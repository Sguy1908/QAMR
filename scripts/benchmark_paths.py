"""Actual bounded path-discovery timings; no equation (22) runtime claim."""

import json
import time

from qamr_sim.config import Config
from qamr_sim.topology.generation import generate
from qamr_sim.topology.paths import candidates

rows = []
for count in (20, 60, 120):
    config = Config(nodes=count)
    graph = generate(config)
    for kind in ("vertex_disjoint", "shortest_overlapping"):
        started = time.perf_counter()
        paths = [candidates(graph, 0, i, 2, kind) for i in range(1, min(count, 20))]
        rows.append(
            dict(
                nodes=count,
                edges=graph.number_of_edges(),
                kind=kind,
                queries=len(paths),
                candidate_cap=2,
                seconds=time.perf_counter() - started,
            )
        )
print(json.dumps(rows, indent=2))
