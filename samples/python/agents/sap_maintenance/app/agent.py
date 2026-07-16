"""PEOS Agent — Planner → Executor → Observer → Synthesiser.

A multi-step LangGraph state machine for SAP Maintenance Order analysis.
Demonstrates production-grade patterns:
- Dynamic tool binding (60-80% token savings)
- Staged prompts (separate system prompt per node)
- Human-in-the-Loop for write operations
- History windowing (bounded conversation context)
- Result truncation (50KB cap)
- E2E timeout guard
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict

import litellm

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_litellm import ChatLiteLLM
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agent_config import (
    AGENT_CAPABILITIES,
    E2E_TIMEOUT_SECONDS,
    LLM_MODEL_NAME,
    MAX_EXECUTOR_ITERATIONS,
    MAX_HISTORY_MESSAGES,
    MAX_QUERY_LENGTH,
)
from app.prompts import (
    OBSERVER_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_TEMPLATE,
    SYNTHESISER_PROMPT,
)
from app.tool_policy import ToolPolicyEngine
from app.tools import TOOLS


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langgraph.graph.state import CompiledStateGraph


# Prevent litellm from crashing on unknown model params
litellm.drop_params = True

logger = logging.getLogger(__name__)


# ── State Schema ────────────────────────────────────────────────────────────


class AgentState(TypedDict):
    """State schema for the PEOS agent graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    plan: dict | None
    tool_results: dict[str, Any]
    executor_iterations: int
    observer_signals: list[str]
    final_answer: str | None
    context_id: str
    human_input_required: bool


@dataclass
class AgentResponse:
    """Structured response from the PEOS agent."""

    status: Literal['input_required', 'completed', 'error']
    message: str


# ── Temporal Context ────────────────────────────────────────────────────────


def _get_temporal_context() -> str:
    """Generate date/time context so the LLM can resolve 'today', 'this week', etc."""
    now = datetime.now(tz=UTC)
    return (
        f'Current date: {now.strftime("%Y-%m-%d")} ({now.strftime("%A")})\n'
        f'Current time: {now.strftime("%H:%M")}'
    )


# ── Agent ───────────────────────────────────────────────────────────────────


class SAPMaintenanceAgent:
    """PEOS agent for SAP Maintenance Order analysis.

    Architecture:
        Planner  → Classifies intent, selects tools, builds execution plan (1 LLM call)
        Executor → Calls SAP OData tools based on plan (1 LLM call per iteration)
        Observer → Evaluates result quality, detects anomalies (1 LLM call)
        Synthesiser → Formats final response with quick replies (1 LLM call)

    Token Optimization:
        - Dynamic tool binding: executor only sees tools in the plan (~60-80% savings)
        - Staged prompts: each node has its own focused system prompt (~40% savings)
        - 3-turn planner window: planner sees last 3 conversation turns (~70% savings)
        - Result truncation: tool results capped at 50KB
        - History windowing: conversation history capped at 40 messages
    """

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self) -> None:
        logger.info(
            'Initializing SAPMaintenanceAgent model=%s tools=%d',
            LLM_MODEL_NAME,
            len(TOOLS),
        )
        self.llm = ChatLiteLLM(model=LLM_MODEL_NAME, timeout=25)
        self.llm_with_tools = self.llm.bind_tools(TOOLS)
        self.tool_map = {t.name: t for t in TOOLS}
        self.tools_by_name = {t.name: t for t in TOOLS}
        self.tool_policy = ToolPolicyEngine()
        self._history: dict[str, list[BaseMessage]] = defaultdict(list)
        self.graph = self._build_graph()

    # ── Dynamic Tool Binding ────────────────────────────────────────────────
    # KEY OPTIMIZATION: Instead of sending all 11 tool schemas to the LLM on every
    # executor call (costing ~2-3K tokens), we only bind the tools referenced in
    # the planner's output. For typical 2-3 tool plans, this saves 60-80% tokens.

    def _select_tools_from_plan(self, plan: dict | None) -> list:
        """Select only tools referenced in the plan — massive token savings."""
        if not plan:
            return TOOLS

        selected: list[str] = []
        # From relevant_tools list
        for name in plan.get('relevant_tools', []):
            if (
                isinstance(name, str)
                and name in self.tools_by_name
                and name not in selected
            ):
                selected.append(name)
        # From step definitions
        for step in plan.get('steps', []) or []:
            name = step.get('tool') if isinstance(step, dict) else None
            if (
                isinstance(name, str)
                and name in self.tools_by_name
                and name not in selected
            ):
                selected.append(name)

        if not selected:
            return TOOLS
        return [self.tools_by_name[name] for name in selected]

    # ── HITL Detection ──────────────────────────────────────────────────────

    @staticmethod
    def _has_write_confirmation(text: str) -> bool:
        """Check if user message contains write confirmation keywords."""
        if not text:
            return False
        return bool(
            re.search(
                r'\b(confirm|confirmed|approval|approved|yes proceed|go ahead)\b',
                text.lower(),
            )
        )

    @staticmethod
    def _extract_order_ids(plan: dict) -> list[str]:
        """Extract order IDs from plan step args."""
        ids: list[str] = []
        for step in plan.get('steps', []) or []:
            if not isinstance(step, dict):
                continue
            for oid in (step.get('args', {}) or {}).get('order_ids', []):
                if isinstance(oid, str) and oid not in ids:
                    ids.append(oid)
        return ids

    # ── Graph Construction ──────────────────────────────────────────────────

    def _build_graph(self) -> CompiledStateGraph:  # noqa: PLR0915
        """Construct the LangGraph state machine (planner/executor/observer/synthesiser)."""
        agent = self  # Closure reference

        # ── PLANNER NODE ────────────────────────────────────────────────────
        async def planner_node(state: AgentState) -> dict:
            """Classify intent and build execution plan. Cost: 1 LLM call."""
            context_id = state['context_id']
            logger.info('[PLANNER] context_id=%s', context_id)

            user_msg = next(
                (
                    m.content
                    for m in reversed(state['messages'])
                    if isinstance(m, HumanMessage)
                ),
                '',
            )

            # 3-turn history window — planner doesn't need full conversation
            history_msgs = [
                m for m in state['messages'] if not isinstance(m, SystemMessage)
            ][-6:]
            history_text = (
                '\n'.join(
                    f'{type(m).__name__}: {(m.content[:200] if isinstance(m.content, str) else "(structured)")}'
                    for m in history_msgs
                )
                or '(no history)'
            )

            plan_prompt = PLANNER_USER_TEMPLATE.format(
                temporal_context=_get_temporal_context(),
                session_context='(new session)',
                history=history_text,
                user_message=user_msg,
            )

            try:
                plan_raw = await agent.llm.ainvoke(
                    [
                        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                        HumanMessage(content=plan_prompt),
                    ]
                )
                content = (
                    plan_raw.content.strip()
                    if isinstance(plan_raw.content, str)
                    else '{}'
                )
                if content.startswith('```'):
                    content = (
                        content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
                    )
                plan_dict = json.loads(content)
                if not isinstance(plan_dict.get('relevant_tools'), list):
                    plan_dict['relevant_tools'] = []
            except Exception as e:  # noqa: BLE001
                logger.warning('[PLANNER] fallback: %s', e)
                plan_dict = {
                    'goal_type': 'conversational',
                    'goal_summary': 'direct response',
                    'relevant_tools': [],
                    'steps': [],
                    'requires_synthesis': True,
                }

            return {
                'plan': plan_dict,
                'tool_results': {},
                'executor_iterations': 0,
                'observer_signals': [],
                'final_answer': None,
                'human_input_required': False,
            }

        # ── EXECUTOR NODE ───────────────────────────────────────────────────
        async def executor_node(state: AgentState) -> dict:
            """Execute tools from the plan. Uses dynamic tool binding."""
            iterations = state.get('executor_iterations', 0)
            tool_results = dict(state.get('tool_results', {}))
            messages = list(state['messages'])
            plan = state.get('plan') or {}

            # ── HITL Gate: require confirmation for write operations ─────────
            latest_user = next(
                (
                    m.content
                    for m in reversed(messages)
                    if isinstance(m, HumanMessage)
                    and isinstance(m.content, str)
                ),
                '',
            )
            goal_type = plan.get('goal_type', '')
            if goal_type in {
                'action_teco',
                'action_unteco',
            } and not agent._has_write_confirmation(latest_user):
                order_ids = agent._extract_order_ids(plan)
                action = (
                    'set TECO' if goal_type == 'action_teco' else 'reset TECO'
                )
                order_text = (
                    ', '.join(order_ids)
                    if order_ids
                    else 'the requested order(s)'
                )
                return {
                    'messages': [
                        AIMessage(
                            content=f"⚠️ **Confirmation required**: I'm about to {action} for {order_text}. Reply 'confirm' to proceed."
                        )
                    ],
                    'tool_results': tool_results,
                    'executor_iterations': iterations + 1,
                    'human_input_required': True,
                }

            # Inject plan summary on first iteration
            if iterations == 0:
                steps = plan.get('steps', [])
                if steps:
                    summary = '\n'.join(
                        f'Step {i + 1}: {s.get("tool")} — {s.get("reason", "")}'
                        for i, s in enumerate(steps)
                    )
                    messages.append(
                        SystemMessage(
                            content=f'Execution plan:\n{summary}\nExecute now.'
                        )
                    )

            # ── Dynamic tool binding: only bind plan-relevant tools ──────────
            active_tools = agent._select_tools_from_plan(plan)
            llm_bound = agent.llm.bind_tools(active_tools)
            response = await llm_bound.ainvoke(messages)
            new_messages: list[BaseMessage] = [response]

            # Execute tool calls concurrently
            if hasattr(response, 'tool_calls') and response.tool_calls:

                async def _run_tool(
                    tc: dict,
                ) -> tuple[ToolMessage, dict | None]:
                    tool_name = tc['name']
                    tool_args = tc['args']
                    try:
                        # Check policy (write protection)
                        decision = agent.tool_policy.evaluate(tool_name)
                        if not decision.allowed:
                            msg = f'Policy blocked: {decision.reason}'
                            return ToolMessage(
                                content=msg, tool_call_id=tc['id']
                            ), None

                        result = await agent.tool_map[tool_name].ainvoke(
                            tool_args
                        )
                        result_str = str(result)
                        # Result truncation: 50KB cap
                        max_result_size = 50_000
                        if len(result_str) > max_result_size:
                            result_str = (
                                result_str[:max_result_size] + '... [TRUNCATED]'
                            )
                        return (
                            ToolMessage(
                                content=result_str, tool_call_id=tc['id']
                            ),
                            {
                                'tool': tool_name,
                                'args': tool_args,
                                'result': result_str,
                            },
                        )
                    except Exception:
                        logger.exception(
                            '[EXECUTOR] Tool failed: %s', tool_name
                        )
                        return (
                            ToolMessage(
                                content=f'Tool {tool_name} failed. Service may be unavailable.',
                                tool_call_id=tc['id'],
                            ),
                            None,
                        )

                results = await asyncio.gather(
                    *[_run_tool(tc) for tc in response.tool_calls]
                )
                for msg, entry in results:
                    new_messages.append(msg)
                    if entry:
                        tool_results[f'{entry["tool"]}_{msg.tool_call_id}'] = (
                            entry
                        )

            return {
                'messages': new_messages,
                'tool_results': tool_results,
                'executor_iterations': iterations + 1,
                'human_input_required': False,
            }

        # ── OBSERVER NODE ───────────────────────────────────────────────────
        async def observer_node(state: AgentState) -> dict:
            """Evaluate tool results for completeness and anomalies."""
            tool_results = state.get('tool_results', {})
            if not tool_results:
                return {'observer_signals': []}

            # Truncate each result to 400 chars for observer (token savings)
            summary = json.dumps(
                {k: v.get('result', '')[:400] for k, v in tool_results.items()},
                indent=2,
            )

            try:
                obs_resp = await agent.llm.ainvoke(
                    [
                        SystemMessage(content=OBSERVER_PROMPT),
                        HumanMessage(content=f'Tool results:\n{summary}'),
                    ]
                )
                content = (
                    obs_resp.content.strip()
                    if isinstance(obs_resp.content, str)
                    else '{}'
                )
                if content.startswith('```'):
                    content = (
                        content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
                    )
                parsed = json.loads(content)
            except Exception as e:  # noqa: BLE001
                logger.warning('[OBSERVER] fallback: %s', e)
                parsed = {'signals': [], 'patterns': []}

            signals = list(parsed.get('signals', [])) + [
                f'Pattern: {p}' for p in parsed.get('patterns', [])
            ]
            return {'observer_signals': signals, 'tool_results': tool_results}

        # ── SYNTHESISER NODE ────────────────────────────────────────────────
        async def synthesiser_node(state: AgentState) -> dict:
            """Format final response. Handles fast paths (zero LLM cost) and full synthesis."""
            plan = state.get('plan') or {}
            goal_type = plan.get('goal_type', '')

            # Fast path: capability inquiry — zero LLM calls
            if goal_type == 'capability_inquiry':
                answer = json.dumps(
                    {
                        'answer': AGENT_CAPABILITIES,
                        'chartData': [],
                        'quickReplies': [
                            'Orders for plant 1010',
                            'Details order 4000045',
                            'Stock for 100-100',
                        ],
                    }
                )
                return {
                    'final_answer': answer,
                    'messages': [AIMessage(content=answer)],
                }

            # Fast path: HITL confirmation prompt
            if state.get('human_input_required'):
                approval = next(
                    (
                        m.content
                        for m in reversed(state['messages'])
                        if isinstance(m, AIMessage)
                        and 'confirmation required' in (m.content or '').lower()
                    ),
                    None,
                )
                if approval:
                    answer = json.dumps(
                        {
                            'answer': approval,
                            'chartData': [],
                            'quickReplies': ['Confirm', 'Cancel'],
                        }
                    )
                    return {
                        'final_answer': answer,
                        'messages': [AIMessage(content=answer)],
                        'human_input_required': True,
                    }

            # Fast path: out of scope
            if goal_type == 'out_of_scope':
                answer = json.dumps(
                    {
                        'answer': 'That\'s outside my area of expertise. I specialize in SAP plant maintenance insights.\n\nTry: "Show orders for plant 1010" or "What can you do?"',
                        'chartData': [],
                        'quickReplies': [
                            'What can you do?',
                            'Orders for plant 1010',
                            'Search orders',
                        ],
                    }
                )
                return {
                    'final_answer': answer,
                    'messages': [AIMessage(content=answer)],
                }

            # Full synthesis: filter ToolMessages to prevent orphan tool_call_id errors
            valid_tc_ids: set[str] = set()
            for m in state['messages']:
                if (
                    isinstance(m, AIMessage)
                    and hasattr(m, 'tool_calls')
                    and m.tool_calls
                ):
                    for tc in m.tool_calls:
                        valid_tc_ids.add(tc['id'])

            synthesis_msgs: list[BaseMessage] = []
            for m in state['messages']:
                if isinstance(m, SystemMessage):
                    continue
                if (
                    isinstance(m, ToolMessage)
                    and getattr(m, 'tool_call_id', '') not in valid_tc_ids
                ):
                    continue
                synthesis_msgs.append(m)

            signals = state.get('observer_signals', [])
            if signals:
                synthesis_msgs.append(
                    SystemMessage(
                        content='Observer signals:\n'
                        + '\n'.join(f'- {s}' for s in signals)
                    )
                )

            try:
                system = f'{_get_temporal_context()}\n\n{SYNTHESISER_PROMPT}'
                response = await agent.llm.ainvoke(
                    [SystemMessage(content=system), *synthesis_msgs]
                )
                answer = (
                    response.content
                    if isinstance(response.content, str)
                    else str(response.content)
                )
            except Exception:
                answer = json.dumps(
                    {
                        'answer': 'Unable to generate a response. Please try again.',
                        'chartData': [],
                        'quickReplies': [
                            'Try again',
                            'What can you do?',
                            'Show orders',
                        ],
                    }
                )
                logger.exception('[SYNTHESISER] Error')

            return {
                'final_answer': answer,
                'messages': [AIMessage(content=answer)],
            }

        # ── Routing ─────────────────────────────────────────────────────────

        def route_after_planner(state: AgentState) -> str:
            plan = state.get('plan') or {}
            goal = plan.get('goal_type', '')
            if not plan.get('steps') or goal in (
                'conversational',
                'capability_inquiry',
                'out_of_scope',
            ):
                return 'synthesiser'
            return 'executor'

        def route_after_executor(state: AgentState) -> str:
            if state.get('human_input_required'):
                return 'synthesiser'
            if state.get('executor_iterations', 0) >= MAX_EXECUTOR_ITERATIONS:
                return 'observer'
            last = state['messages'][-1]
            if hasattr(last, 'tool_calls') and last.tool_calls:
                return 'executor'
            return 'observer'

        # ── Build Graph ─────────────────────────────────────────────────────

        builder = StateGraph(AgentState)
        builder.add_node('planner', planner_node)
        builder.add_node('executor', executor_node)
        builder.add_node('observer', observer_node)
        builder.add_node('synthesiser', synthesiser_node)

        builder.add_edge(START, 'planner')
        builder.add_conditional_edges(
            'planner',
            route_after_planner,
            {'executor': 'executor', 'synthesiser': 'synthesiser'},
        )
        builder.add_conditional_edges(
            'executor',
            route_after_executor,
            {
                'executor': 'executor',
                'observer': 'observer',
                'synthesiser': 'synthesiser',
            },
        )
        builder.add_edge('observer', 'synthesiser')
        builder.add_edge('synthesiser', END)

        return builder.compile()

    # ── Message Management ──────────────────────────────────────────────────

    def _build_messages(self, query: str, context_id: str) -> list[BaseMessage]:
        return self._history[context_id] + [HumanMessage(content=query)]

    def _update_history(
        self, context_id: str, messages: list[BaseMessage]
    ) -> None:
        """Keep only Human + AI messages. Strip ToolMessages to prevent orphan IDs."""
        clean: list[BaseMessage] = []
        for m in messages:
            if isinstance(m, (SystemMessage, ToolMessage)):
                continue
            if isinstance(m, AIMessage):
                content = (
                    m.content if isinstance(m.content, str) else str(m.content)
                )
                if content and content.strip():
                    clean.append(AIMessage(content=content))
                continue
            clean.append(m)
        self._history[context_id] = clean[-MAX_HISTORY_MESSAGES:]

    # ── Public Interface ────────────────────────────────────────────────────

    async def stream(
        self, query: str, context_id: str
    ) -> AsyncGenerator[dict, None]:
        """Stream agent response. Entry point for A2A integration."""
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]

        yield {
            'is_task_complete': False,
            'require_user_input': False,
            'content': 'Analyzing request...',
        }

        try:
            state: AgentState = {
                'messages': self._build_messages(query, context_id),
                'plan': None,
                'tool_results': {},
                'executor_iterations': 0,
                'observer_signals': [],
                'final_answer': None,
                'context_id': context_id,
                'human_input_required': False,
            }

            try:
                result = await asyncio.wait_for(
                    self.graph.ainvoke(state), timeout=E2E_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                logger.exception(
                    'E2E timeout (%ss) for context=%s',
                    E2E_TIMEOUT_SECONDS,
                    context_id,
                )
                yield {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': json.dumps(
                        {
                            'answer': 'Request took too long. Please try a simpler query.',
                            'chartData': [],
                            'quickReplies': [
                                'Try again',
                                'What can you do?',
                                'Show orders',
                            ],
                        }
                    ),
                }
                return

            response = result.get('final_answer') or json.dumps(
                {
                    'answer': 'Unable to generate a response. Please try again.',
                    'chartData': [],
                    'quickReplies': [
                        'Try again',
                        'What can you do?',
                        'Show orders',
                    ],
                }
            )

            self._update_history(context_id, result['messages'])

            requires_input = result.get('human_input_required', False)
            yield {
                'is_task_complete': not requires_input,
                'require_user_input': requires_input,
                'content': response,
            }

        except Exception:
            logger.exception('stream error')
            yield {
                'is_task_complete': True,
                'require_user_input': False,
                'content': json.dumps(
                    {
                        'answer': 'I encountered an internal error. Please try again.',
                        'chartData': [],
                        'quickReplies': ['Try again', 'What can you do?'],
                    }
                ),
            }
