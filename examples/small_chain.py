"""No filesystem or UI needed to inspect a custom graph."""

import networkx as nx

from qamr_sim.config import Config
from qamr_sim.engine.simulation import Simulation

config = Config(
    nodes=4,
    sessions=[(0, 3)],
    simulation_duration_seconds=100,
    arrival_rate=1,
    coherence_distribution="fixed",
)
result = Simulation(config, nx.path_graph(4)).run()
print(result.summary)
