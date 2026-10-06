"""Algorithm 1, with bounded purification and explicit interpretation choices."""

import math

import networkx as nx

from qamr_sim.models.analytical import aggregate_admission, probabilities, score
from qamr_sim.models.fidelity import path_fidelity
from qamr_sim.models.purification import plan
from qamr_sim.models.queueing import mm1
from qamr_sim.rng import rng
from qamr_sim.topology.paths import candidates

from .base import Candidate


class Router:
    def __init__(self, config, graph, sessions, coherences, control):
        self.c, self.graph, self.sessions = config, graph, sessions
        self.coherences, self.control = coherences, control
        self.cache = {}
        self.fractions = {}
        self.round_robin = {}

    def paths(self, session):
        s, d = self.sessions[session]
        key = (session, tuple(sorted(self.graph.nodes)), tuple(sorted(self.graph.edges)))
        if key not in self.cache:
            if self.c.policy == "single_path":
                try:
                    paths = [tuple(nx.shortest_path(self.graph, s, d))]
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    paths = []
            else:
                cap = min(self.c.candidate_cap, self.c.max_paths)
                paths = candidates(self.graph, s, d, cap, self.c.path_kind)
            self.cache[key] = paths
        return self.cache[key]

    def loads(self):
        c = self.c
        if c.load_estimator == "rolling":
            return self.control.published.copy()
        loads = {n: 0.0 for n in range(c.nodes)}
        rate = c.arrival_rate / (len(self.sessions) if c.traffic_convention == "total" else 1)
        for s in range(len(self.sessions)):
            paths = self.paths(s)
            for path in paths:
                fraction = self.fractions.get((s, path), 1 / len(paths))
                if c.dispatch == "replicate" or c.load_estimator == "literal_full":
                    fraction = 1
                for n in path[:-1]:
                    loads[n] += rate * fraction
        return loads

    def evaluate(self, session):
        c = self.c
        loads = self.loads()
        rows = []
        for path in self.paths(session):
            stats = [mm1(loads[n], c.mu) for n in path[:-1]]
            waits = [v["sojourn"] for v in stats]
            # No-queue ablation uses unloaded service estimates, not instantaneous queue length.
            estimate_waits = [1 / c.mu] * len(waits) if c.policy == "no_queue" else waits
            delay = sum(estimate_waits)
            mus = [c.mu] * len(waits)
            rhos = [v["rho"] for v in stats]
            mu_path = min(mus) if c.path_service == "bottleneck" else 1 / sum(1 / m for m in mus)
            rho_path = (
                max(rhos)
                if c.path_service == "bottleneck"
                else sum(loads[n] for n in path[:-1]) / len(mus) / mu_path
            )
            paper_f = path_fidelity(
                c.initial_fidelity,
                len(path) - 1,
                estimate_waits,
                [self.coherences[n] for n in path[:-1]],
                c.swap_success_probability,
                c.routing_fidelity_model,
                c.proxy_swap_factor,
            )
            # Slot endpoints exist together: each node on the reserved chain decoheres during
            # the entire traversal. This explicit resource abstraction is A09, not Eq. (5).
            exposure_rate = sum(1 / self.coherences[n] for n in path)
            resource_f = path_fidelity(
                c.initial_fidelity,
                len(path) - 1,
                [delay],
                [1 / exposure_rate],
                c.swap_success_probability,
                c.routing_fidelity_model,
                c.proxy_swap_factor,
            )
            cap = 0 if c.policy == "no_purification" else c.purification_round_cap
            rounds, fidelity = plan(
                resource_f,
                c.fidelity_threshold,
                cap,
                c.purification_efficiency,
                c.purification_time_seconds,
                exposure_rate,
                c.routing_fidelity_model,
            )
            aggregate_ok = aggregate_admission([loads[n] for n in path[:-1]], mus, c.theta)
            node_ok = all(v["rho"] < 1 for v in stats)
            memory_ok = all(v["number"] <= c.memory_capacity for v in stats)
            fidelity_ok = fidelity >= c.fidelity_threshold and math.isfinite(delay)
            eligible = (
                aggregate_ok
                and fidelity_ok
                and (c.admission == "aggregate_only" or (node_ok and memory_ok))
            )
            rho_score = 0 if c.policy == "no_queue" else rho_path
            value = (
                score(delay, fidelity, rho_score, c.score_weights, c.policy == "congestion_penalty")
                if eligible
                else 0
            )
            rows.append(
                Candidate(
                    path,
                    paper_f,
                    fidelity,
                    rounds,
                    delay,
                    mu_path,
                    rho_path,
                    aggregate_ok,
                    node_ok,
                    memory_ok,
                    fidelity_ok,
                    eligible,
                    max(0, value),
                )
            )
        eligible = [r for r in rows if r.eligible]
        if c.policy == "queue_aware_single" and eligible:
            best = max(eligible, key=lambda r: (r.score, tuple(-n for n in r.path)))
            eligible = [best]
        for r, p in zip(eligible, probabilities([r.score for r in eligible])):
            r.probability = p
        # Prospective split offered-load estimates; no full-demand duplication on split paths.
        for r in rows:
            self.fractions[(session, r.path)] = r.probability
        return rows

    def choose(self, rows, request_id, retry, session):
        eligible = [r for r in rows if r.probability > 0]
        if not eligible:
            return []
        if self.c.dispatch == "replicate":
            return eligible
        if self.c.dispatch == "round_robin":
            index = self.round_robin.get(session, 0)
            self.round_robin[session] = index + 1
            return [eligible[index % len(eligible)]]
        random = rng(self.c.seed, "policy", request_id, retry)
        return [eligible[int(random.choice(len(eligible), p=[r.probability for r in eligible]))]]
