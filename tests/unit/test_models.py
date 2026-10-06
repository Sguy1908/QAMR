import math

import networkx as nx
import pytest
from pydantic import ValidationError

from qamr_sim.config import Config
from qamr_sim.models.analytical import (
    aggregate_admission,
    probabilities,
    redundancy_throughput,
    score,
)
from qamr_sim.models.fidelity import decay, delay_bound, path_fidelity
from qamr_sim.models.objective import constraints, objective, selected_metrics
from qamr_sim.models.purification import gain, plan
from qamr_sim.models.queueing import aggregate_load, hardware_efficiency, mm1, mm1k, service_rate
from qamr_sim.topology.paths import candidates, pair_properties
from qamr_sim.topology.robustness import exact_r_robust


def test_queue_meanings_and_units():
    q = mm1(0.5, 1)
    assert q["number"] == 1
    assert q["sojourn"] == 2
    assert q["queue_wait"] == 1
    assert q["number"] == 0.5 * q["sojourn"]
    assert mm1(1, 1)["sojourn"] == math.inf
    assert aggregate_load([1, 1], [0.5, 0.5]) == 1
    assert service_rate(0.95, 1, 0.02, 0.05) == pytest.approx(0.95 / 0.07)
    assert hardware_efficiency(0.9, 2, 0.8, 1) == pytest.approx(0.648)
    assert mm1(0, 1)["queue_wait"] == 0
    assert mm1k(1, 1, 4)["blocking"] == pytest.approx(0.2)
    assert mm1k(0, 1, 4)["sojourn"] is None
    assert mm1k(1e6, 1, 4)["number"] <= 4


@pytest.mark.parametrize("model,floor", [("paper_exponential", 0), ("paper_half_floor", 0.5)])
def test_fidelity_domains_and_inversion(model, floor):
    assert decay(0.98, 0, model) == 0.98
    assert decay(0.98, 1e6, model) == floor
    bound = delay_bound(0.98, 0.85, 50, model)
    assert decay(0.98, bound / 50, model) == pytest.approx(0.85)
    assert decay(0.98, (bound + 0.1) / 50, model) < 0.85
    assert delay_bound(0.9, 0.95, 50, model) is None
    assert delay_bound(0.98, floor, 50, model) == math.inf
    assert delay_bound(0.98, 0.85, 100, model) == pytest.approx(2 * bound)


def test_fidelity_proxy_and_purification():
    assert path_fidelity(0.98, 2, [0, 0], [50, 50], 0.95) == pytest.approx(0.98**2 * 0.95)
    assert gain(0.8, 0.6, 0) == 0.8
    assert gain(0.8, 0.6, 100) == 1
    n, f = plan(0.5, 0.85, 2, 0.01, 100, 10, "paper_exponential")
    assert n == 2 and f < 0.85  # time cost can overwhelm every gain round


def test_literal_equations_and_constraints():
    assert score(1, 0.9, 0.8, (0.4, 0.4, 0.2)) > score(1, 0.9, 0.1, (0.4, 0.4, 0.2))
    assert probabilities([0, 0]) == [0.5, 0.5]
    assert probabilities([]) == []
    assert sum(probabilities([1, 2, 3])) == pytest.approx(1)
    with pytest.raises(ValueError):
        probabilities([math.inf])
    assert aggregate_admission([11, 0], [10, 10], 0.9)
    assert not constraints([11, 0], [10, 10], [1, 1], [8, 8], [0.9], 0.85, [1], 2)["stability"]
    v = selected_metrics([1, 0], [2, 9], [3, 4], [0.5, 0.5], [0.9, 0.7])
    assert v == {"delay": 2, "throughput": 1.5, "fidelity": 0.9}
    assert selected_metrics([0], [1], [1], [0], [0.9])["fidelity"] is None
    assert objective([2], [0.9], 1.5) == pytest.approx(-0.4)
    assert redundancy_throughput(2, [1, 1], 0.5, 1, 0) == 1.5
    assert redundancy_throughput(2, [], 0.5, 1, 0) == 0
    assert redundancy_throughput(2, [1], 1, 1, 1) == 0


def test_graph_definitions():
    cycle = nx.cycle_graph(4)
    assert pair_properties(cycle, 0, 2)["vertex_disjoint"] == 2
    assert len(candidates(cycle, 0, 2, 2)) == 2
    assert nx.node_connectivity(cycle) == 2
    assert not exact_r_robust(cycle, 2)  # connectivity is NOT r-robustness
    assert exact_r_robust(nx.complete_graph(3), 2)
    assert not candidates(nx.empty_graph(3), 0, 2)
    with pytest.raises(ValueError):
        exact_r_robust(nx.path_graph(11), 1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"warmup_seconds": 2000},
        {"theta": 1},
        {"score_weights": (-1, 1, 1)},
        {"coherence_central_seconds": 5},
        {"sessions": [(0, 60)]},
        {"arrival_rate": -1},
        {"unknown": 2},
    ],
)
def test_invalid_config(kwargs):
    with pytest.raises(ValidationError):
        Config(**kwargs)
