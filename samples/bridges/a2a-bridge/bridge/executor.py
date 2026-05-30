# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A2A AgentExecutor bridging requests to the Vertex Interactions API."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from a2a import types as a2a_types
from a2a.server import agent_execution
from a2a.server import events as a2a_events
from a2a.server import tasks as a2a_tasks
from google.protobuf import json_format

from bridge import auth, config, content, interactions, render, sessions, storage, stream
from bridge import runtime as runtime_mod


logger = logging.getLogger(__name__)


def _text_parts(text: str) -> list[a2a_types.Part]:
    return [a2a_types.Part(text=text)]


def _vertex_overrides(
    context: agent_execution.RequestContext,
) -> Mapping[str, Any]:
    """Extracts the optional ``vertex`` override block from message metadata."""
    message = context.message
    if message is None or not message.metadata:
        return {}
    metadata: Any = message.metadata
    # message.metadata is a protobuf Struct, which registers as a Mapping but has
    # no .get; convert any protobuf message to a plain dict before reading it.
    if hasattr(metadata, 'DESCRIPTOR'):
        metadata = json_format.MessageToDict(metadata)
    if not isinstance(metadata, Mapping):
        return {}
    vertex_overrides = metadata.get('vertex')
    return vertex_overrides if isinstance(vertex_overrides, Mapping) else {}


def _ids(context: agent_execution.RequestContext) -> tuple[str, str]:
    assert context.task_id is not None  # noqa: S101
    assert context.context_id is not None  # noqa: S101
    return context.task_id, context.context_id


class InteractionsAgentExecutor(agent_execution.AgentExecutor):
    """Bridges A2A ``execute``/``cancel`` to Vertex Interactions SSE.

    One turn per ``execute`` call. Serialises concurrent turns on the
    same session via :class:`Session.lock`. ``cancel`` closes the active
    ``httpx`` response so the consumer task exits; the Vertex interaction
    itself continues server-side (``POST .../cancel`` returns 501 on Vertex).
    """

    def __init__(self, settings: config.Settings, runtime: runtime_mod.Runtime) -> None:
        """Constructs the executor.

        Builds its Interactions client, session store, and content builder from
        *settings* and *runtime*.
        """
        self._settings = settings
        self._registry = settings.registry
        self._client = interactions.InteractionsClient(settings)
        self._sessions = sessions.build(
            firestore_database=settings.firestore_database,
            project_id=settings.project_id,
        )
        signer = (
            storage.SignedUrlProvider(settings.upload_bucket) if settings.upload_bucket else None
        )
        self._content = content.ContentBuilder(runtime, signer)
        self._active: dict[str, httpx.Response] = {}
        self._cancelled: set[str] = set()

    @property
    def session_store(self) -> sessions.SessionStore:
        """The session store backing this executor."""
        return self._sessions

    async def aclose(self) -> None:
        """Closes the Interactions API client."""
        await self._client.aclose()

    def _headers(self, context: agent_execution.RequestContext) -> Mapping[str, str]:
        if context.call_context is None:
            return {}
        return context.call_context.state.get('headers', {})

    def _select_agent(
        self,
        context: agent_execution.RequestContext,
        overrides: Mapping[str, Any],
    ) -> tuple[str, config.AgentConfig]:
        requested = overrides.get('agent') or self._headers(context).get(config.AGENT_HEADER)
        return self._registry.resolve(requested)

    def _user(self, context: agent_execution.RequestContext) -> auth.GoogleUser | None:
        call_context = context.call_context
        if call_context and isinstance(call_context.user, auth.GoogleUser):
            return call_context.user
        return None

    def _session_key(
        self,
        user: auth.GoogleUser | None,
        context_id: str,
        agent_key: str,
    ) -> str:
        # context_id is client-supplied; always scope to the authenticated caller
        # so one user's sandbox/history cannot be reattached by another.
        identity = user.identity if user else 'anon'
        if self._settings.env_scope == 'user' and user:
            return f'{identity}:{agent_key}'
        return f'{identity}:{context_id}:{agent_key}'

    def _resolve_environment(
        self,
        *,
        session: sessions.Session,
        overrides: Mapping[str, Any],
        agent_config: config.AgentConfig,
        session_key: str,
    ) -> str | dict[str, Any] | None:
        override = overrides.get('environment')
        if session.env_id:
            if override and override != session.env_id:
                logger.warning(
                    'environment override %r rejected for session %s (bound to %s)',
                    override,
                    session_key,
                    session.env_id,
                )
            return session.env_id
        return override or agent_config.default_environment

    def _open_stream(  # noqa: PLR0913
        self,
        *,
        agent_config: config.AgentConfig,
        overrides: Mapping[str, Any],
        session: sessions.Session,
        session_key: str,
        content_items: list[dict[str, Any]],
        user: auth.GoogleUser | None,
        on_open: interactions.OnOpen,
    ) -> AsyncIterator[dict[str, Any]]:
        allow_overrides = self._settings.allow_request_overrides
        tools = [tool.model_dump() for tool in agent_config.default_tools]
        if allow_overrides:
            # Validate caller-supplied tools through the same model as agents.json
            # so _CONTROL_PLANE_ONLY / forward_user_auth guards still apply.
            for raw in overrides.get('tools') or []:
                tools.append(config.Tool.model_validate(raw).model_dump())  # noqa: PERF401
        bearer = f'Bearer {user.token}' if user and user.token_kind == 'access' else None  # noqa: S105
        for tool in tools:
            forward = tool.pop('forward_user_auth', False)
            if forward and bearer and tool.get('type') == 'mcp_server':
                tool.setdefault('headers', {})['Authorization'] = bearer
        agent_ref = (overrides.get('agent_ref') if allow_overrides else None) or agent_config.agent
        extra_agent_config = (
            overrides.get('agent_config') if allow_overrides else None
        ) or agent_config.interaction_agent_config
        return self._client.create(
            agent=agent_ref,
            content=content_items,
            environment=self._resolve_environment(
                session=session,
                overrides=overrides,
                agent_config=agent_config,
                session_key=session_key,
            ),
            previous_interaction_id=session.interaction_id,
            tools=tools or None,
            agent_config=extra_agent_config,
            on_open=on_open,
        )

    async def execute(  # noqa: PLR0912, PLR0915
        self,
        context: agent_execution.RequestContext,
        event_queue: a2a_events.EventQueue,
    ) -> None:
        """Runs one A2A turn: streams the interaction and emits task updates."""
        task_id, context_id = _ids(context)
        updater = a2a_tasks.TaskUpdater(event_queue, task_id, context_id)
        if context.current_task is None:
            await event_queue.enqueue_event(
                a2a_types.Task(
                    id=task_id,
                    context_id=context_id,
                    status=a2a_types.TaskStatus(state=a2a_types.TaskState.TASK_STATE_SUBMITTED),
                )
            )
        await updater.start_work(
            message=updater.new_agent_message(_text_parts('connecting to sandbox…'))
        )

        overrides = _vertex_overrides(context)
        agent_key, agent_config = self._select_agent(context, overrides)
        user = self._user(context)
        session_key = self._session_key(user, context_id, agent_key)
        session = await self._sessions.get_or_create(session_key)
        owner = user.identity if user else None
        if session.owner and session.owner != owner:
            # Persisted under a different caller (e.g. pre-identity-keyed Firestore
            # doc); refuse to reattach to someone else's sandbox/conversation.
            logger.warning('session owner mismatch for %s; starting a fresh chain', session_key)
            session.env_id = None
            session.interaction_id = None
        session.owner = owner
        session.agent_key = agent_key
        session.context_id = context_id

        async with session.lock:
            content_items, preamble = await asyncio.gather(
                self._content.from_message(context.message),
                self._content.export_preamble(context_id),
            )
            if preamble:
                content_items.insert(0, preamble)

            consumer = stream.StreamConsumer(session, updater)

            def track_response(resp: httpx.Response) -> None:
                # A cancel may land while the stream is opening; don't let the new
                # response escape cancellation (cancel() only sees what's in _active).
                if task_id in self._cancelled:
                    asyncio.ensure_future(resp.aclose())  # noqa: RUF006
                    return
                self._active[task_id] = resp

            try:
                await consumer.run(
                    self._open_stream(
                        agent_config=agent_config,
                        overrides=overrides,
                        session=session,
                        session_key=session_key,
                        content_items=content_items,
                        user=user,
                        on_open=track_response,
                    )
                )
                if (
                    consumer.terminal is None
                    and session.interaction_id
                    and task_id not in self._cancelled
                ):
                    logger.info('stream ended early; reattaching to %s', session.interaction_id)
                    await consumer.run(
                        self._client.reattach(
                            session.interaction_id,
                            last_event_id=consumer.last_event_id,
                            on_open=track_response,
                        )
                    )
            except httpx.RemoteProtocolError:
                if task_id in self._cancelled:
                    # The drop is our own cancel closing the response; do not reattach
                    # to the interaction the client just cancelled.
                    pass
                elif session.interaction_id:
                    logger.info('stream dropped; reattaching to %s', session.interaction_id)
                    try:
                        await consumer.run(
                            self._client.reattach(
                                session.interaction_id,
                                last_event_id=consumer.last_event_id,
                                on_open=track_response,
                            )
                        )
                    except httpx.HTTPError as err:
                        consumer.error = f'reattach failed: {err}'
                else:
                    consumer.error = 'stream disconnected before interaction started'
            except httpx.HTTPError as err:
                logger.exception('interaction stream error')
                consumer.error = str(err)
            except Exception as err:
                # Last resort: SSE parse / TaskUpdater / proto errors must still fail
                # the task cleanly rather than leave it stuck in WORKING.
                logger.exception('unexpected error consuming interaction stream')
                consumer.error = str(err)
            finally:
                self._active.pop(task_id, None)
                was_cancelled = task_id in self._cancelled
                self._cancelled.discard(task_id)

            if session.env_id or session.interaction_id:
                try:
                    await self._sessions.persist(session_key, session)
                except Exception:
                    logger.exception('session persist failed for %s', session_key)
            if was_cancelled:
                return
            if consumer.error:
                await self._fail(session, updater, consumer.error)
            elif consumer.terminal is None:
                await self._fail(session, updater, 'stream ended without completion')

    async def cancel(
        self,
        context: agent_execution.RequestContext,
        event_queue: a2a_events.EventQueue,
    ) -> None:
        """Cancels the in-flight interaction for this task."""
        task_id, context_id = _ids(context)
        if (resp := self._active.pop(task_id, None)) is not None:
            # Only record while an execute is in flight; that execute's finally
            # discards the entry, so the set stays bounded.
            self._cancelled.add(task_id)
            with contextlib.suppress(Exception):
                await resp.aclose()
        updater = a2a_tasks.TaskUpdater(event_queue, task_id, context_id)
        await updater.cancel(message=updater.new_agent_message(_text_parts('cancelled by client')))

    async def _fail(
        self,
        session: sessions.Session,
        updater: a2a_tasks.TaskUpdater,
        message: str,
    ) -> None:
        # Salvage the environment id so the next turn can reattach to the sandbox.
        if session.interaction_id:
            try:
                interaction = await self._client.get(session.interaction_id)
                if env_id := interaction.get('environment_id'):
                    session.env_id = env_id
            except httpx.HTTPError:
                logger.debug('env_id salvage failed', exc_info=True)
        logger.error('interaction failed: %s', message)
        await updater.failed(
            message=updater.new_agent_message(
                _text_parts('sandbox backend error — please retry: ' + render.short_error(message))
            )
        )
