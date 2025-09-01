import types
import uuid

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from a2a.types import AgentExtension


_CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/traceability/v1'
TRACEABILITY_EXTENSION_URI = f'https://{_CORE_PATH}'


class CallTypeEnum(str, Enum):
    """An enumeration of call types for tracking interactions in the A2A multiagent system.

    Values:
        AGENT: Represents calls made to or from agents
        TOOL: Represents calls made to or from tools
        HOST: Represents calls made to or from the host application
    """

    AGENT = 'AGENT'
    TOOL = 'TOOL'
    HOST = 'HOST'


class TraceRecord:
    """A class for tracking and recording steps in a trace.

    TraceRecord represents a single step in a trace, capturing information such as
    the call type, timing, parameters, and results. It provides methods for finalizing
    a step and converting the record to a dictionary format.

    Attributes:
        step_id (str): Unique identifier for this trace step
        trace_id (str): Optional identifier of the parent trace this step belongs to
        parent_step_id (str): Optional identifier of the parent step
        call_type (CallTypeEnum): The type of call being traced
        name (str): Optional name for the step
        parameters (dict): Optional parameters associated with the step
        requests (dict): Optional request details associated with the step
        step_type (str): Optional type classification for the step
        cost (float): Optional cost associated with the step
        total_tokens (int): Optional count of tokens used in the step
        additional_attributes (dict): Dictionary for any extra attributes to track
        latency (int): Execution time in milliseconds (calculated when step ends)
        start_time (datetime): Timestamp when the step was created
        end_time (datetime): Timestamp when the step was completed
        error (Any): Optional error information if the step failed
    """

    # Disable the "too many arguments" lint warning for this method
    # as all parameters are necessary for the trace record initialization
    def __init__(
        self,
        call_type: CallTypeEnum,
        name: str | None = None,
        parameters: dict[str, Any] | None = None,
        requests: dict[str, Any] | None = None,
        parent_step_id: str | None = None,
        step_type: str | None = None,
    ):
        """Initializes a TraceRecord with the given parameters.

        This is the constructor for the TraceRecord class, which initializes
        a new trace step with a unique ID, start time, and optional parameters.
        """
        self.step_id = f'step-{uuid.uuid4()}'
        self.trace_id = None
        self.parent_step_id = parent_step_id
        self.call_type = call_type
        self.name = name
        self.parameters = parameters
        self.requests = requests
        self.step_type = step_type
        self.cost = None
        self.total_tokens = None
        self.additional_attributes = {}
        self.latency = None
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        self.error = None

    def end_step(
        self,
        cost: float | None = None,
        total_tokens: int | None = None,
        additional_attributes: dict[str, Any] | None = None,
        error: Any = None,
    ) -> None:
        """Finalizes the trace step with timing and usage information.

        This method records the end time of the step, calculates latency,
        and updates attributes such as cost, token count, and any errors that occurred.

        Args:
            cost (float | None, optional): The cost associated with this step. Defaults to None.
            total_tokens (int | None, optional): Total number of tokens used. Defaults to None.
            additional_attributes (dict[str, Any] | None, optional): Additional information to record. Defaults to None.
            error (Any, optional): Error information if the step failed. Defaults to None.
        """
        self.end_time = datetime.now(timezone.utc)
        self.latency = int(
            (self.end_time - self.start_time).total_seconds() * 1000
        )
        if cost:
            self.cost = cost
        if total_tokens:
            self.total_tokens = total_tokens
            print(
                f'### TraceRecord: end_step called with cost={cost}, total_tokens={total_tokens}'
            )
        if additional_attributes:
            self.additional_attributes.update(additional_attributes)
        if error:
            self.error = error

    def attach_to_trace(self, trace_id: str) -> None:
        """Associates this trace record with a parent trace.

        Args:
            trace_id (str): The identifier of the trace to attach this record to.
        """
        self.trace_id = trace_id

    def as_dict(self) -> dict[str, Any]:
        """Converts the trace record to a dictionary representation.

        Returns:
            dict[str, Any]: A dictionary containing all attributes of the trace record.
        """
        return {
            'step_id': self.step_id,
            'trace_id': self.trace_id,
            'parent_step_id': self.parent_step_id,
            'call_type': self.call_type,
            'name': self.name,
            'parameters': self.parameters,
            'requests': self.requests,
            'step_type': self.step_type,
            'cost': self.cost,
            'total_tokens': self.total_tokens,
            'additional_attributes': self.additional_attributes,
            'latency': self.latency,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error': self.error,
        }


class ResponseTrace:
    """A class for managing and recording trace steps in a response.

    ResponseTrace organizes multiple trace records under a single trace ID,
    providing methods to add steps and convert the entire trace to a dictionary format.

    Attributes:
        trace_id (str): Unique identifier for this trace
        steps (list[TraceRecord]): List of trace records belonging to this trace
    """

    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or f'trace-{uuid.uuid4()}'
        self.steps: list[TraceRecord] = []

    def add_step(self, step: TraceRecord) -> None:
        """Adds a trace step to this response trace.

        This method attaches the step to this trace and adds it to the steps collection.

        Args:
            step (TraceRecord): The trace record to add to this trace.
        """
        step.attach_to_trace(self.trace_id)
        self.steps.append(step)

    def as_dict(self) -> dict[str, Any]:
        """Converts the response trace to a dictionary representation.

        Returns:
            dict[str, Any]: A dictionary containing the trace ID and all steps in the trace.
        """
        return {
            'trace_id': self.trace_id,
            'steps': [s.as_dict() for s in self.steps],
        }


class TraceStep:
    """Context manager for tracing agent/tool steps.

    Usage:
        with TraceStep(trace, call_type, ...) as step:
            ...agent or tool logic...
            step.end_step(cost=x, additional_attributes={...})
    """

    def __init__(
        self,
        response_trace: ResponseTrace | None,
        call_type: CallTypeEnum,
        name: str | None = None,
        parameters: dict[str, Any] | None = None,
        requests: dict[str, Any] | None = None,
        parent_step_id: str | None = None,
        step_type: str | None = None,
    ):
        """Initialize a tracer object for tracking function calls and responses.

        Args:
            response_trace (ResponseTrace | None): The response trace object to record into, or None if tracing is disabled.
            call_type (CallTypeEnum): The type of call being traced (e.g., function, tool).
            name (str | None, optional): The name of the operation being traced. Defaults to None.
            parameters (dict[str, Any] | None, optional): Parameters provided to the call. Defaults to None.
            requests (dict[str, Any] | None, optional): Request data associated with the call. Defaults to None.
            parent_step_id (str | None, optional): ID of the parent step if this is a nested operation. Defaults to None.
            step_type (str | None, optional): Type of step being performed. Defaults to None.
        """
        self.response_trace = response_trace
        self.step = TraceRecord(
            call_type=call_type,
            name=name,
            parameters=parameters,
            requests=requests,
            parent_step_id=parent_step_id,
            step_type=step_type,
        )

    def __enter__(self) -> TraceRecord:
        """Context manager entry point that returns the trace step.

        Returns:
            TraceRecord: The trace record instance to be used in the context.
        """
        return self.step

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_traceback: types.TracebackType | None,
    ) -> bool:
        """Context manager exit point that finalizes the trace step.

        Args:
            exc_type: The exception type if an exception was raised in the context.
            exc_val: The exception value if an exception was raised in the context.
            traceback: The traceback if an exception was raised in the context.

        Returns:
            bool: False to indicate that exceptions should not be suppressed.
        """
        error_msg = None
        if exc_type:
            error_msg = ''.join(
                exc_traceback.format_exception(exc_type, exc_val, exc_traceback)
            )
        self.step.end_step(error=error_msg)
        if self.response_trace:
            self.response_trace.add_step(self.step)
        # Do not suppress exceptions
        return False


class TraceabilityExtension:
    """An implementation of the Traceability extension.

    This extension implementation illustrates a simple way for an extension to
    provide functionality to agent developers.
    """

    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension representing this extension."""
        return AgentExtension(
            uri=TRACEABILITY_EXTENSION_URI,
            description='Adds traceability information to artifacts.',
        )
