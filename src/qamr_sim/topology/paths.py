from itertools import islice

import networkx as nx


def candidates(graph, source, destination, cap=2, kind="vertex_disjoint"):
    if (
        source not in graph
        or destination not in graph
        or not nx.has_path(graph, source, destination)
    ):
        return []
    if kind == "vertex_disjoint":
        paths = list(nx.node_disjoint_paths(graph, source, destination, cutoff=cap))
    else:
        paths = list(islice(nx.shortest_simple_paths(graph, source, destination), cap))
    return sorted([tuple(p) for p in paths], key=lambda p: (len(p), p))


def pair_properties(graph, source, destination):
    if (
        source not in graph
        or destination not in graph
        or not nx.has_path(graph, source, destination)
    ):
        return dict(vertex_disjoint=0, edge_disjoint=0, pair_vertex_connectivity=0)
    return dict(
        vertex_disjoint=len(list(nx.node_disjoint_paths(graph, source, destination))),
        edge_disjoint=len(list(nx.edge_disjoint_paths(graph, source, destination))),
        pair_vertex_connectivity=nx.node_connectivity(graph, source, destination),
    )
