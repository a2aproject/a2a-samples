import logging
import subprocess
import sys

from agents.python.v03.pyproto import instruction_pb2
from test_suite.go_v03 import AGENT_DEF as GO_V03_AGENT_DEF
from test_suite.python_v03 import AGENT_DEF as PYTHON_V03_AGENT_DEF


_AGENT_DEFS = {
    'go_v03': GO_V03_AGENT_DEF,
    'python_v03': PYTHON_V03_AGENT_DEF,
}

_TRAVERSAL_FUNCTIONS = {}


def register_traversal(name: str):
    """Decorator to register a traversal function."""

    def decorator(func):
        _TRAVERSAL_FUNCTIONS[name] = func
        return func

    return decorator


_SUPPORTED_TRANSPORTS_PER_SDK = {
    'go_v03': {'jsonrpc', 'grpc'},
    'python_v03': {'jsonrpc', 'grpc', 'http_json'},
}

_HOST = '127.0.0.1'

_ALL_TRANSPORTS = {'jsonrpc', 'grpc', 'http_json'}

_END_OF_TRAVERSAL_TOKEN = 'traversal-completed'  # noqa: S105

_MIN_SDKS_PER_TRANSPORT = 2


def create_test_suite(
    sdks: list[str],
    logger: logging.Logger,
    traversal_name: str = 'euler',
) -> tuple[
    instruction_pb2.Instruction,
    list[str],
    list[subprocess.Popen],
    list[str],
    list[str],
]:

    testing_instruction = instruction_pb2.Instruction()
    testing_instruction.steps.response_generator = (
        instruction_pb2.SeriesOfSteps.RESPONSE_GENERATOR_CONCAT
    )
    traversal_function = _TRAVERSAL_FUNCTIONS.get(traversal_name)
    if not traversal_function:
        raise ValueError(f'Unknown traversal: {traversal_name}')
    expected_end_tokens = []
    for transport in _ALL_TRANSPORTS:
        sdks_for_transport = [
            sdk
            for sdk in sdks
            if transport in _SUPPORTED_TRANSPORTS_PER_SDK[sdk]
        ]
        if len(sdks_for_transport) < _MIN_SDKS_PER_TRANSPORT:
            logger.info(
                'Skipping transport %s because only %d of specified SDKs support it - A2A tests require at least 2 SDKs for cross-SDK testing',
                transport,
                len(sdks_for_transport),
            )
            continue
        instruction_for_transport, trace_tokens = traversal_function(
            sdks_for_transport[0], sdks_for_transport, transport
        )
        expected_end_tokens.extend(
            [*trace_tokens, f'{_END_OF_TRAVERSAL_TOKEN}:{transport}']
        )
        testing_instruction.steps.instructions.add().CopyFrom(
            instruction_for_transport
        )

    ports = []
    agent_launchers = []
    agent_card_uris = []
    for sdk in sdks:
        agent_def_for_sdk = _AGENT_DEFS.get(sdk)
        if not agent_def_for_sdk:
            raise ValueError(f'Unknown SDK: {sdk}')
        ports.append(agent_def_for_sdk['httpPort'])
        ports.append(agent_def_for_sdk['grpcPort'])
        agent_launchers.append(agent_def_for_sdk['launcher'])
        agent_card_uris.append(
            f'http://{_HOST}:{agent_def_for_sdk["httpPort"]}'
        )
    return (
        testing_instruction,
        ports,
        agent_launchers,
        agent_card_uris,
        expected_end_tokens,
    )


@register_traversal('euler')
def _euler_traversal_with_hierholzer(
    current_sdk: str,
    all_sdks: list[str],
    transport: str,
) -> tuple[instruction_pb2.Instruction, list[str]]:
    """
    This function utilizes Hierholzer's Algorithm to find an Eulerian Circuit
    covering all directed edges exactly once.

    Why this is guaranteed to exist for a Complete Digraph (Complete
    Directed Graph with no self-loops):
    1. **Connectedness**: Direct edges exist between every node pair, making it
       strongly connected.
    2. **Balance (In-degree = Out-degree)**: In a graph of N vertices, every
       node has exactly (N-1) outgoing edges and (N-1) incoming edges.
    A strongly connected graph where In(X) = Out(X) for all nodes is guaranteed
    to possess an Eulerian Circuit, traversing all segments linearly without
    duplicate activation overlaps.

    Args:
        current_sdk: The starting agent/SDK node.
        all_sdks: The list of ALL agents/SDKs in the graph.
        transport: The transport protocol to use for hops.
    Returns:
        instruction_pb2.Instruction: The assembled full-graph traversal instruction.
    """

    # 1. Generate All Edges for Complete Digraph
    edges = [(u, v) for u in all_sdks for v in all_sdks if u != v]

    # 2. Build Adjacency List for Eulerian Path
    adj = {u: [] for u in all_sdks}
    for u, v in edges:
        adj[u].append(v)

    # 3. Hierholzer's Algorithm to find Eulerian Circuit
    stack = [current_sdk]
    circuit = []

    while stack:
        u = stack[-1]
        if adj[u]:
            v = adj[u].pop()
            stack.append(v)
        else:
            circuit.append(stack.pop())

    circuit.reverse()

    # 4. Assemble Instruction backward from back edge to start
    current_inst = instruction_pb2.Instruction()
    current_inst.return_response.response = (
        f'{_END_OF_TRAVERSAL_TOKEN}:{transport}'
    )
    trace_tokens = []

    for i in range(len(circuit) - 2, -1, -1):
        u = circuit[i]
        v = circuit[i + 1]

        hop = instruction_pb2.Instruction()
        hop.steps.response_generator = (
            instruction_pb2.SeriesOfSteps.RESPONSE_GENERATOR_CONCAT
        )

        trace_token = f'[{u} -> {v} ({transport})]'
        trace_tokens.append(trace_token)
        trace = hop.steps.instructions.add()
        trace.return_response.response = trace_token

        call_step = hop.steps.instructions.add()

        agent_def = _AGENT_DEFS.get(v)
        if not agent_def:
            raise ValueError(f'Unknown SDK: {v}')

        port = agent_def.get('httpPort')
        agent_card_uri = f'http://{_HOST}:{port}'

        call_step.call_agent.agent_card_uri = agent_card_uri
        call_step.call_agent.transport = transport
        call_step.call_agent.instruction.CopyFrom(current_inst)

        current_inst = hop

    return current_inst, trace_tokens
