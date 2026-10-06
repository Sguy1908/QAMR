import networkx as nx
import pytest
import simpy

from qamr_sim.config import Config, Failure
from qamr_sim.engine.memory import Memory
from qamr_sim.engine.simulation import Simulation
from qamr_sim.engine.traffic import offered_traffic


def small(**kwargs):
    return Config(
        **dict(
            nodes=4,
            simulation_duration_seconds=20,
            arrival_rate=2,
            sessions=[(0, 3)],
            coherence_distribution="fixed",
            **kwargs,
        )
    )


def run(config, graph=None):
    return Simulation(config, nx.path_graph(config.nodes) if graph is None else graph).run()


def assert_accounting(result):
    s = result.summary
    assert s["request_conservation"]
    assert sum(s["terminal_counts"].values()) == s["offered"]
    assert s["delivered_measurement"] <= s["offered"]
    assert s["resources_after_cleanup"] == 0
    assert all(n["peak_qubits"] <= result.config["memory_capacity"] for n in result.node_metrics)
    assert all(a["status"] not in ("created", "active") for a in result.attempts)


def test_reproducible_trace_independent():
    c = small()
    a, b = run(c), run(c)
    assert a == b
    silent = run(Config.model_validate({**c.model_dump(), "trace": False}))
    assert a.summary == silent.summary and a.requests == silent.requests
    assert not silent.events
    assert_accounting(a)
    assert a.summary["delivered_measurement"] > 0


@pytest.mark.parametrize(
    "policy",
    [
        "qamr",
        "single_path",
        "queue_aware_single",
        "no_queue",
        "no_purification",
        "congestion_penalty",
    ],
)
def test_matched_policies(policy):
    c = small(policy=policy)
    r = run(c, nx.cycle_graph(4))
    assert_accounting(r)
    baseline = small()
    assert offered_traffic(c, [(0, 3)]) == offered_traffic(baseline, [(0, 3)])


def test_atomic_memory():
    env = simpy.Environment()
    m = Memory(env, range(3), 2, 0)
    assert m.reserve("a", (0, 1, 2))
    assert m.used == {0: 1, 1: 2, 2: 1}
    assert not m.reserve("b", (0, 1, 2))
    assert m.used == {0: 1, 1: 2, 2: 1}
    m.release("a")
    m.release("a")
    assert not any(m.used.values())


def test_no_traffic_no_path_and_overload():
    base = small().model_dump()
    empty = run(Config.model_validate({**base, "arrival_rate": 0}))
    assert empty.summary["throughput"] == 0
    assert empty.summary["mean_fidelity"] is None
    missing = run(small(), nx.empty_graph(4))
    assert missing.summary["terminal_counts"].get("rejected") == missing.summary["offered"]
    loaded = run(
        Config.model_validate(
            {**base, "arrival_rate": 200, "memory_capacity": 2, "max_deferrals": 1}
        )
    )
    assert_accounting(loaded)
    assert loaded.summary["terminal_counts"].get("rejected", 0) > 0


def test_replication_unique_delivery():
    r = run(small(dispatch="replicate"), nx.cycle_graph(4))
    assert_accounting(r)
    assert r.summary["duplicates"] > 0
    assert r.summary["attempted_deliveries"] > r.summary["delivered_measurement"]
    assert all(a["parent_id"] in {q["request_id"] for q in r.requests} for a in r.attempts)


@pytest.mark.parametrize(
    "failure", [Failure(node=1, time=2, duration=5), Failure(edge=(1, 2), time=2, duration=5)]
)
def test_failure_during_reservations_and_recovery(failure):
    c = small(
        failures=[failure],
        hardware_efficiency=0.02,
        load_estimator="rolling",
        telemetry_interval_seconds=100,
        purification_round_cap=10,
    )
    r = run(c)
    assert_accounting(r)
    assert any(a["reason"] in ("node_failure", "edge_failure") for a in r.attempts)
    assert len(r.summary["failure_connectivity"]) == 2


def test_expiration_and_unfinished():
    c = small(
        hardware_efficiency=0.01,
        load_estimator="rolling",
        telemetry_interval_seconds=100,
        purification_round_cap=10,
        request_deadline_seconds=0.2,
    )
    r = run(c)
    assert_accounting(r)
    assert r.summary["terminal_counts"].get("expired", 0) > 0
    c = Config.model_validate(
        {**c.model_dump(), "request_deadline_seconds": 100, "simulation_duration_seconds": 2}
    )
    r = run(c)
    assert_accounting(r)
    assert r.summary["terminal_counts"].get("unfinished", 0) > 0


def test_cancellation_and_warmup():
    sim = Simulation(small(warmup_seconds=2), nx.cycle_graph(4))
    r = sim.run(cancelled=lambda: sim.env.now >= 10)
    assert_accounting(r)
    assert r.summary["cancelled"]
    assert r.summary["measurement_seconds"] == 8
    assert r.summary["latency_cohort_n"] <= r.summary["delivered_measurement"]


def test_shared_bottleneck_and_slot_integrals():
    graph = nx.Graph([(0, 1), (1, 2), (2, 4), (1, 3), (3, 4)])
    c = Config(
        nodes=5,
        sessions=[(0, 4)],
        arrival_rate=5,
        simulation_duration_seconds=30,
        path_kind="shortest_overlapping",
        memory_capacity=2,
    )
    r = run(c, graph)
    assert_accounting(r)
    assert r.summary["memory_blocked_attempts"] > 0
    assert r.node_metrics[1]["peak_qubits"] == 2
    assert r.node_metrics[1]["mean_qubits"] <= 2
