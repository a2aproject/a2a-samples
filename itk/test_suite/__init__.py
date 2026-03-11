import logging
import subprocess
import sys

from agents.python.v03.pyproto import instruction_pb2
from test_suite.go_v03 import AGENT_DEF as GO_V03_AGENT_DEF
from test_suite.go_v10_v03_compat import (
    AGENT_DEF as GO_V10_V03_COMPAT_AGENT_DEF,
)
from test_suite.python_v03 import AGENT_DEF as PYTHON_V03_AGENT_DEF


_AGENT_DEFS = {
    'go_v03': GO_V03_AGENT_DEF,
    'python_v03': PYTHON_V03_AGENT_DEF,
    'go_v10_v03_compat': GO_V10_V03_COMPAT_AGENT_DEF,
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
    'go_v10_v03_compat': {'jsonrpc'},
}

_HOST = '127.0.0.1'

_ALL_TRANSPORTS = {'jsonrpc', 'grpc', 'http_json'}

_END_OF_TRAVERSAL_TOKEN = 'traversal-completed'  # noqa: S105

_MIN_SDKS_PER_TRANSPORT = 2


def _parse_edge_strings(
    edges: list[str], ref_sdks: list[str]
) -> list[tuple[str, str]]:
    """Parses a list of edge strings like ["0->1"] into SDK pairs.

    Args:
        edges: List of strings in "u_idx->v_idx" format.
        ref_sdks: The list of SDKs mapping to the indices.

    Returns:
        list[tuple[str, str]]: Parsed SDK pairs.

    Raises:
        ValueError: If edge format or index is invalid.
    """
    parsed = []
    expected_edge_parts = 2
    for edge_str in edges:
        parts = edge_str.split('->')
        if len(parts) != expected_edge_parts:
            raise ValueError(f'Invalid edge format: {edge_str}')
        u_s, v_s = parts[0].strip(), parts[1].strip()
        if not (u_s.isdigit() and v_s.isdigit()):
            raise ValueError(f'Invalid edge format or index: {edge_str}')
        u_idx, v_idx = int(u_s), int(v_s)
        if (
            u_idx < 0
            or u_idx >= len(ref_sdks)
            or v_idx < 0
            or v_idx >= len(ref_sdks)
        ):
            raise ValueError(f'Invalid edge format or index: {edge_str}')
        parsed.append((ref_sdks[u_idx], ref_sdks[v_idx]))
    return parsed


def _verify_eulerian_graph(
    adj: dict[str, list[str]],
    in_degree: dict[str, int],
    out_degree: dict[str, int],
    all_sdks: list[str],
    current_sdk: str,
) -> None:
    """Verifies that the graph defined by degrees and adjacency list is Eulerian.

    Args:
        adj: Adjacency list.
        in_degree: In-degree of each node.
        out_degree: Out-degree of each node.
        all_sdks: List of all SDKs.
        current_sdk: Starting SDK.

    Raises:
        ValueError: If graph is not Eulerian.
    """
    # 1. Verify Balance (In-degree == Out-degree)
    for node in all_sdks:
        if in_degree[node] != out_degree[node]:
            raise ValueError(
                f"Eulerian cycle impossible: Node '{node}' has in-degree={in_degree[node]} "
                f'and out-degree={out_degree[node]}.'
            )

    # 2. Verify Strong Connectedness
    # All nodes with non-zero degree must belong to a single strongly connected component.
    # Since in_degree == out_degree, this is equivalent to verifying all edges are reachable
    # from any node that has edges.
    nodes_with_edges = [n for n in all_sdks if out_degree[n] > 0]
    if nodes_with_edges:
        # Start from current_sdk if it has edges, otherwise any node with edges
        start_node = (
            current_sdk if out_degree[current_sdk] > 0 else nodes_with_edges[0]
        )

        # Verify strong connectedness using a DFS-based reachability check.
        visited = {start_node}
        stack = [start_node]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    stack.append(v)

        for node in nodes_with_edges:
            if node not in visited:
                raise ValueError(
                    f"Graph is not strongly connected. Node '{node}' is unreachable "
                    f"from '{start_node}'."
                )


def _traversal_to_instruction(
    circuit: list[str], transport: str
) -> tuple[instruction_pb2.Instruction, list[str]]:
    """Converts a circuit of SDK names into a nested A2A instruction.

    Args:
        circuit: Ordered list of SDK names representing the traversal path.
        transport: The transport protocol to use for hops.

    Returns:
        tuple[instruction_pb2.Instruction, list[str]]: The nested instruction and trace tokens.
    """
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


def create_test_suite(
    sdks: list[str],
    logger: logging.Logger,
    traversal_name: str = 'euler',
    edges: list[str] | None = None,
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

    parsed_edges = _parse_edge_strings(edges, sdks) if edges else None

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
        try:
            circuit = traversal_function(
                sdks_for_transport[0],
                sdks_for_transport,
                transport,
                edges=parsed_edges,
            )
        except ValueError as e:
            logger.warning(
                'Skipping transport %s because %s',
                transport,
                e,
            )
            continue
        instruction_for_transport, trace_tokens = _traversal_to_instruction(
            circuit, transport
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
    edges: list[tuple[str, str]] | None = None,
) -> list[str]:
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
        edges: Optional list of pre-parsed SDK pairs (u, v).
    Returns:
        list[str]: The node circuit representing the traversal path.
    """

    # 1. Generate Edges (Custom or Complete Digraph)
    if edges:
        valid_nodes = set(all_sdks)
        target_edges = [
            (u, v) for u, v in edges if u in valid_nodes and v in valid_nodes
        ]
    else:
        target_edges = [(u, v) for u in all_sdks for v in all_sdks if u != v]

    # 2. Build Adjacency List and Calculate Degrees
    adj = {u: [] for u in all_sdks}
    in_degree = dict.fromkeys(all_sdks, 0)
    out_degree = dict.fromkeys(all_sdks, 0)
    for u, v in target_edges:
        adj[u].append(v)
        out_degree[u] += 1
        in_degree[v] += 1

    # 3. Verify Eulerian Cycle existence
    _verify_eulerian_graph(adj, in_degree, out_degree, all_sdks, current_sdk)

    # 4. Hierholzer's Algorithm to find Eulerian Circuit
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
    return circuit
