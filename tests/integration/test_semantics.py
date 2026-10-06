import networkx as nx
import pytest

from qamr_sim.config import Config, Failure
from qamr_sim.engine.simulation import Simulation
from qamr_sim.engine.traffic import offered_traffic
from qamr_sim.topology.generation import generate, lifetimes, select_sessions


def test_real_paid_purification_and_delivery_threshold():
    c = Config(
        nodes=5,
        sessions=[(0, 4)],
        simulation_duration_seconds=10,
        arrival_rate=3,
        trace=True,
        coherence_distribution="fixed",
    )
    result = Simulation(c, nx.path_graph(5)).run()
    assert any(a["purification_rounds"] for a in result.attempts)
    for attempt in result.attempts:
        events = [e for e in result.events if e["attempt_id"] == attempt["attempt_id"]]
        starts = [e for e in events if e["kind"] == "purification_start"]
        ends = [e for e in events if e["kind"] == "purification_end"]
        for start, end in zip(starts, ends):
            assert end["time"] - start["time"] == pytest.approx(c.purification_time_seconds)
        if attempt["status"] == "completed":
            assert attempt["fidelity"] >= c.fidelity_threshold
    assert result.summary["resources_after_cleanup"] == 0


def test_impossible_physical_memory_cannot_leak():
    c = Config(
        nodes=3,
        sessions=[(0, 2)],
        memory_capacity=1,
        arrival_rate=2,
        simulation_duration_seconds=10,
    )
    result = Simulation(c, nx.path_graph(3)).run()
    assert not result.attempts  # internal repeater needs two slots atomically
    assert result.summary["memory_blocking"] == 1
    assert result.summary["throughput"] == 0
    assert result.summary["resources_after_cleanup"] == 0


def test_overlapping_failures_recover_only_after_both():
    c = Config(
        nodes=3,
        sessions=[(0, 2)],
        simulation_duration_seconds=10,
        arrival_rate=3,
        failures=[Failure(node=1, time=2, duration=4), Failure(node=1, time=3, duration=5)],
    )
    result = Simulation(c, nx.path_graph(3)).run()
    checkpoints = result.summary["failure_connectivity"]
    assert [(x["time"], x["pairs"][0]["vertex_disjoint"]) for x in checkpoints] == [
        (2, 0),
        (3, 0),
        (6, 0),
        (8, 1),
    ]
    assert result.summary["resources_after_cleanup"] == 0


def test_hardware_distributions_and_unconditioned_topology():
    c = Config()
    g = generate(c)
    assert len(g) == 60
    assert g.graph["acceptance"] == "first_draw"
    assert g.graph["formal_r_robustness"] == "unknown"
    assert list(g.edges) == list(generate(c).edges)
    assert select_sessions(g, c) == select_sessions(g, c)
    values = lifetimes(c)
    assert min(values.values()) >= 40 and max(values.values()) <= 60
    normal = Config(coherence_distribution="positive_truncated_normal")
    assert min(lifetimes(normal).values()) > 0
    fixed = Config(coherence_distribution="fixed")
    assert set(lifetimes(fixed).values()) == {50}


def test_traffic_scope_explicit_and_logged():
    total = Config(nodes=4, arrival_rate=1, simulation_duration_seconds=100)
    sessions = [(0, 1), (2, 3)]
    per_session = Config.model_validate({**total.model_dump(), "traffic_convention": "per_session"})
    assert len(offered_traffic(per_session, sessions)) > len(offered_traffic(total, sessions))
    r = Simulation(per_session, nx.complete_graph(4)).run()
    assert r.summary["total_configured_arrival_rate"] == 2
