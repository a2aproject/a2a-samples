import logging
import socket
import subprocess
import sys

from agents.python.v03.pyproto import instruction_pb2
from test_suite.go_v03 import spawn_agent as spawn_agent_go_v03
from test_suite.go_v10 import spawn_agent as spawn_agent_go_v10
from test_suite.python_v03 import spawn_agent as spawn_agent_python_v03
from test_suite.python_v10 import spawn_agent as spawn_agent_python_v10


_AGENT_DEFS = {
    'go_v03': {'launcher': spawn_agent_go_v03},
    'python_v03': {'launcher': spawn_agent_python_v03},
    'go_v10': {'launcher': spawn_agent_go_v10},
    'python_v10': {'launcher': spawn_agent_python_v10},
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
    'go_v10': {'jsonrpc', 'grpc'},
    'python_v10': {'grpc', 'jsonrpc', 'http_json'},
}

_HOST = '127.0.0.1'

_ALL_TRANSPORTS = {'jsonrpc', 'grpc', 'http_json'}

_END_OF_TRAVERSAL_TOKEN = 'traversal-completed'  # noqa: S105

_MIN_SDKS_PER_TRANSPORT = 2


def _get_free_port() -> int:
    """Finds an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def allocate_agent_ports(sdk_name: str) -> None:
    """Allocates dynamic ports for an agent if not already assigned."""
    agent_def = _AGENT_DEFS.get(sdk_name)
    if not agent_def:
        raise ValueError(f'Unknown SDK: {sdk_name}')
    if 'httpPort' not in agent_def:
        p1 = _get_free_port()
        p2 = _get_free_port()
        max_retries = 10
        for _ in range(max_retries):
            if p2 != p1:
                break
            p2 = _get_free_port()
        else:
            raise RuntimeError(
                f'Failed to allocate distinct ports for {sdk_name} after {max_retries} attempts'
            )
        agent_def['httpPort'] = p1
        agent_def['grpcPort'] = p2


def get_agent_launcher(sdk_name: str):
    """Returns a launcher function with allocated ports bound."""
    agent_def = _AGENT_DEFS.get(sdk_name)
    if not agent_def:
        raise ValueError(f'Unknown SDK: {sdk_name}')
    launcher_func = agent_def['launcher']
    h = agent_def['httpPort']
    g = agent_def['grpcPort']
    return lambda h=h, g=g, f=launcher_func: f(h, g)


def get_agent_card_uri(sdk_name: str) -> str:
    """Returns the well-known agent card URI."""
    agent_def = _AGENT_DEFS.get(sdk_name)
    if not agent_def:
        raise ValueError(f'Unknown SDK: {sdk_name}')
    return f'http://{_HOST}:{agent_def["httpPort"]}/jsonrpc'


def get_agent_def(sdk_name: str) -> dict:
    """Returns the agent definition dictionary for the given SDK."""
    agent_def = _AGENT_DEFS.get(sdk_name)
    if not agent_def:
        raise ValueError(f'Unknown SDK: {sdk_name}')
    return agent_def


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


def _decompose_into_components(
    nodes_with_edges: list[str], adj: dict[str, list[str]]
) -> list[list[str]]:
    """Decomposes nodes with edges into connected components (undirected view)."""
    undirected_adj = {u: set() for u in adj}
    for u, neighbors in adj.items():
        for v in neighbors:
            undirected_adj[u].add(v)
            undirected_adj[v].add(u)

    visited = set()
    components = []
    for node in nodes_with_edges:
        if node not in visited:
            component = []
            stack = [node]
            visited_component = {node}
            while stack:
                u = stack.pop()
                component.append(u)
                for v in undirected_adj[u]:
                    if v not in visited_component:
                        visited_component.add(v)
                        stack.append(v)
            components.append(component)
            visited.update(visited_component)
    return components


def _verify_eulerian_graph(
    in_degree: dict[str, int],
    out_degree: dict[str, int],
    all_sdks: list[str],
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

    # 2. Strong Connectedness verification is deferred to component decomposition
    # in the traversal logic. All components must locally satisfy Eulerian conditions
    # (checked in step 1), making them independently traversable.


def _traversal_to_instruction(
    circuit: list[str], transport: str, streaming: bool = False
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
        agent_card_uri = f'http://{_HOST}:{port}/jsonrpc'

        call_step.call_agent.agent_card_uri = agent_card_uri
        call_step.call_agent.transport = transport
        call_step.call_agent.streaming = streaming
        call_step.call_agent.instruction.CopyFrom(current_inst)

        current_inst = hop

    return current_inst, trace_tokens


def create_test_suite(  # noqa: PLR0913
    sdks: list[str],
    logger: logging.Logger,
    traversal_name: str = 'euler',
    edges: list[str] | None = None,
    protocols: list[str] | None = None,
    streaming: bool = False,
) -> tuple[
    instruction_pb2.Instruction,
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

    transports_to_test = (
        protocols if protocols is not None else list(_ALL_TRANSPORTS)
    )

    expected_end_tokens = []
    for transport in transports_to_test:
        circuits = traversal_function(
            sdks[0],
            sdks,
            transport,
            edges=parsed_edges,
        )
        for circuit in circuits:
            instruction_for_transport, trace_tokens = _traversal_to_instruction(
                circuit, transport, streaming=streaming
            )
            expected_end_tokens.extend(
                [*trace_tokens, f'{_END_OF_TRAVERSAL_TOKEN}:{transport}']
            )
            testing_instruction.steps.instructions.add().CopyFrom(
                instruction_for_transport
            )

    for sdk in sdks:
        allocate_agent_ports(sdk)
    return (
        testing_instruction,
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

    **Note on DFS vs Eulerian traversal**:
    Standard Depth-First Search (DFS) is vertex-focused (it visits vertices and
    marks them as visited to avoid cycles). In a graph with multiple edges or
    cycles, a standard DFS will skip edges that lead to already-visited nodes
    (such as back-edges or cross-edges). Consequently, DFS may skip edges and
    fail to produce an Eulerian traversal. Hierholzer's algorithm, in contrast,
    consumes *edges* to ensure that every directed edge is visited exactly once.

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

    # 3. Verify Eulerian Balance existence
    _verify_eulerian_graph(in_degree, out_degree, all_sdks)

    # 4. Decompose into components and run Hierholzer for each
    nodes_with_edges = [n for n in all_sdks if out_degree[n] > 0]
    components = _decompose_into_components(nodes_with_edges, adj)
    circuits = []

    if not components:
        return [[current_sdk]]

    # Sort to prioritize component containing current_sdk (execute first)
    components.sort(key=lambda c: current_sdk not in c)

    for comp in components:
        start_node = current_sdk if current_sdk in comp else comp[0]
        stack = [start_node]
        comp_circuit = []
        while stack:
            u = stack[-1]
            if adj[u]:
                v = adj[u].pop()
                stack.append(v)
            else:
                comp_circuit.append(stack.pop())
        comp_circuit.reverse()
        circuits.append(comp_circuit)

    return circuits
