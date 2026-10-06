import math

import networkx as nx

from qamr_sim.rng import rng


def generate(config):
    random = rng(config.topology_seed, "topology")
    positions = {i: random.random(2).tolist() for i in range(config.nodes)}
    radius = config.radius or math.sqrt(config.target_mean_degree / ((config.nodes - 1) * math.pi))
    graph = nx.random_geometric_graph(config.nodes, radius, pos=positions)
    # One unconditional draw; no connectivity conditioning or favorable resampling.
    graph.graph.update(
        radius=radius,
        topology_seed=config.topology_seed,
        acceptance="first_draw",
        achieved_mean_degree=2 * graph.number_of_edges() / config.nodes,
        connected=nx.is_connected(graph),
        components=nx.number_connected_components(graph),
        vertex_connectivity=nx.node_connectivity(graph) if nx.is_connected(graph) else 0,
        formal_r_robustness="unknown",
    )
    return graph


def select_sessions(graph, config):
    if config.sessions is not None:
        return config.sessions
    random = rng(config.topology_seed, "topology", "sessions")
    return [
        tuple(map(int, random.choice(sorted(graph), 2, replace=False)))
        for _ in range(config.session_count)
    ]


def lifetimes(config):
    random = rng(config.seed, "hardware")
    center, spread = config.coherence_central_seconds, config.coherence_spread_seconds
    if config.coherence_distribution == "fixed":
        return {i: center for i in range(config.nodes)}
    values = {}
    for i in range(config.nodes):
        v = (
            random.uniform(center - spread, center + spread)
            if config.coherence_distribution == "bounded_uniform"
            else random.normal(center, spread)
        )
        while v <= 0:
            v = random.normal(center, spread)
        values[i] = float(v)
    return values
