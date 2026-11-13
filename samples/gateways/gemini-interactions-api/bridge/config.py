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

"""Typed configuration for the A2A bridge.

Settings are loaded from environment variables (see ``Settings``); the
multi-agent registry is loaded from ``AGENTS_CONFIG`` which may be either a
filesystem path to a JSON file or an inline JSON string.
"""

from __future__ import annotations

import pathlib
import string
import types

from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal, Self

import pydantic
import pydantic_settings


if TYPE_CHECKING:
    from collections.abc import Mapping


AGENT_HEADER = 'x-bridge-agent'

_TOOL_ALIASES = types.MappingProxyType({'mcp': 'mcp_server'})
_CONTROL_PLANE_ONLY = frozenset({'filesystem'})


class Tool(pydantic.BaseModel):
    """A Vertex Interactions tool spec.

    Only ``type`` is required; backend-specific keys (e.g. ``name``/``url`` for
    ``mcp_server``) are passed through verbatim.
    """

    model_config = pydantic.ConfigDict(extra='allow')

    type: str
    forward_user_auth: bool = False

    @pydantic.model_validator(mode='after')
    def _normalize(self) -> Self:
        self.type = _TOOL_ALIASES.get(self.type, self.type)
        if self.type in _CONTROL_PLANE_ONLY:
            raise ValueError(
                f'tool type {self.type!r} is control-plane only; declare it on the '
                'Agent resource, not in default_tools'
            )
        if self.forward_user_auth and self.type != 'mcp_server':
            raise ValueError(
                f"forward_user_auth is only supported on 'mcp_server' tools, not {self.type!r}"
            )
        return self


class AgentConfig(pydantic.BaseModel):
    """One routable agent exposed by the bridge."""

    agent: str
    display_name: str
    description: str
    system_instruction: str | None = None
    tags: list[str] = pydantic.Field(default_factory=list)
    default_tools: list[Tool] = pydantic.Field(default_factory=list)
    default_environment: str | dict[str, Any] | None = None
    interaction_agent_config: dict[str, Any] | None = None
    starter_prompts: list[str] = pydantic.Field(default_factory=list)


class AgentsRegistry(pydantic.BaseModel):
    """The parsed ``agents.json`` document."""

    default: str
    agents: dict[str, AgentConfig]

    @pydantic.model_validator(mode='after')
    def _check_default(self) -> Self:
        if self.default not in self.agents:
            raise ValueError(f"default agent {self.default!r} is not defined in 'agents'")
        return self

    @property
    def default_agent(self) -> AgentConfig:
        """The configuration of the registry's default agent."""
        return self.agents[self.default]

    def resolve(self, key: str | None) -> tuple[str, AgentConfig]:
        """Returns (key, config) for *key*, falling back to the default."""
        if key and key in self.agents:
            return key, self.agents[key]
        return self.default, self.default_agent

    @classmethod
    def load(cls, source: str, substitutions: Mapping[str, str] | None = None) -> AgentsRegistry:
        """Loads a registry from a path or an inline JSON string.

        ``${PROJECT_ID}``-style placeholders are expanded from *substitutions*
        (unknown placeholders are left intact via ``safe_substitute``), so one
        config can target multiple projects.
        """
        text = source if source.lstrip().startswith('{') else pathlib.Path(source).read_text()
        if substitutions:
            text = string.Template(text).safe_substitute(substitutions)
        return cls.model_validate_json(text)


class Settings(pydantic_settings.BaseSettings):
    """Process-wide settings, populated from environment variables."""

    model_config = pydantic_settings.SettingsConfigDict(env_file='.env', extra='ignore')

    port: int = 8080
    allow_anonymous: bool = False
    # When false, the executor ignores caller-supplied message.metadata.vertex
    # overrides that pick a different agent/tools/agent_config/environment, so
    # agents.json stays the trust boundary. Enable only for trusted callers.
    allow_request_overrides: bool = False
    # Overrides the ID-token audience; when unset the per-request host URL is
    # used (see bridge.auth).
    id_token_audience: str | None = None
    # When false (default), an ID token is rejected unless an audience can be
    # determined (id_token_audience or the request host); never verify with no
    # aud.
    allow_unverified_id_token_audience: bool = False
    project_id: str
    location: str = 'global'
    vertex_endpoint: str = 'https://aiplatform.googleapis.com'
    api_revision: str = '2026-05-20'
    # Idle read timeout for the interaction SSE stream. A stalled stream raises
    # httpx.ReadTimeout (handled as a turn failure) instead of hanging forever;
    # keep it well above the largest expected gap between stream events.
    stream_read_timeout_s: int = 600
    env_scope: Literal['context', 'user'] = 'context'
    idle_ttl_s: int = 3600
    firestore_database: str | None = None
    upload_bucket: str | None = None
    agents_config: str

    @cached_property
    def registry(self) -> AgentsRegistry:
        """The parsed agent registry, lazily loaded and cached.

        Loaded from ``agents_config`` on first access, with ``${PLACEHOLDER}``
        substitution applied (see :meth:`AgentsRegistry.load`).
        """
        return AgentsRegistry.load(
            self.agents_config,
            {
                'PROJECT_ID': self.project_id,
                'LOCATION': self.location,
                'BUCKET': self.upload_bucket or '',
            },
        )
