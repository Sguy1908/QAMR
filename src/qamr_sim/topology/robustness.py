"""Formal r-reachability of disjoint nonempty vertex subsets, exponential checker."""

from itertools import product


def exact_r_robust(graph, r):
    if len(graph) > 10:
        raise ValueError("Exact O(3^n) certification restricted to <=10 vertices")
    if r < 1:
        raise ValueError("r >= 1 required")
    nodes = sorted(graph)
    for labels in product(range(3), repeat=len(nodes)):
        a = {n for n, label in zip(nodes, labels) if label == 1}
        b = {n for n, label in zip(nodes, labels) if label == 2}
        if (
            a
            and b
            and not any(len(set(graph[v]) - a) >= r for v in a)
            and not any(len(set(graph[v]) - b) >= r for v in b)
        ):
            return False
    return True
