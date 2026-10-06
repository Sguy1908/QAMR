"""Filesystem-independent SimPy aggregate-service reconstruction."""

from collections import Counter
from dataclasses import asdict

import networkx as nx
import numpy as np
import simpy

from qamr_sim.config import Config
from qamr_sim.models.fidelity import decay
from qamr_sim.models.purification import delayed_round
from qamr_sim.rng import rng
from qamr_sim.routing.qamr import Router
from qamr_sim.topology.generation import generate, lifetimes, select_sessions
from qamr_sim.topology.paths import pair_properties
from qamr_sim.types import TERMINAL, Attempt, Request, Result

from .control import Control
from .memory import Memory
from .node import Node
from .traffic import offered_traffic


class Simulation:
    def __init__(self, config: Config, graph=None):
        self.c = config
        self.env = simpy.Environment()
        self.original = generate(config) if graph is None else graph.copy()
        if set(self.original) != set(range(config.nodes)):
            raise ValueError("Graph nodes must match configured consecutive integer IDs")
        self.graph = self.original.copy()
        self.sessions = select_sessions(self.graph, config)
        self.coherences = lifetimes(config)
        self.nodes = {n: Node(self.env, config.warmup_seconds) for n in self.graph}
        self.memory = Memory(self.env, self.graph, config.memory_capacity, config.warmup_seconds)
        self.control = Control(self.env, config, self.nodes)
        self.router = Router(config, self.graph, self.sessions, self.coherences, self.control)
        self.requests, self.attempts, self.processes = {}, {}, {}
        self.events, self.path_metrics = [], []
        self.blocked_reservations = self.reservation_attempts = 0
        self.down_nodes, self.down_edges = Counter(), Counter()
        self.failure_connectivity = []
        self.stopped = False
        self.env.process(self.traffic())
        for index, f in enumerate(config.failures):
            self.env.process(self.failure(index, f))

    def log(self, kind, request_id="", attempt_id="", node=None, value=None, detail=""):
        if self.c.trace:
            self.events.append(
                dict(
                    schema_version=1,
                    time=self.env.now,
                    kind=kind,
                    request_id=request_id,
                    attempt_id=attempt_id,
                    node=node,
                    value=value,
                    detail=detail,
                )
            )

    def finish(self, req, status, reason):
        if req.status in TERMINAL:
            return
        req.status, req.reason, req.end = status, reason, self.env.now
        self.log(status, req.request_id, detail=reason)

    def traffic(self):
        for time, session, rid in offered_traffic(self.c, self.sessions):
            yield self.env.timeout(time - self.env.now)
            req = Request(rid, session, time)
            self.requests[rid] = req
            self.log("offered", rid)
            pending = sum(r.status == "pending" for r in self.requests.values())
            if pending > self.c.pending_capacity:
                self.finish(req, "rejected", "classical_pending_full")
            else:
                self.env.process(self.request(req))

    def request(self, req):
        c = self.c
        for retry in range(c.max_deferrals + 1):
            if req.status in TERMINAL:
                return
            if self.env.now - req.arrival >= c.request_deadline_seconds:
                self.finish(req, "expired", "request_deadline")
                return
            rows = self.router.evaluate(req.session)
            for row in rows:
                self.path_metrics.append(
                    dict(
                        schema_version=1,
                        time=self.env.now,
                        request_id=req.request_id,
                        retry=retry,
                        **asdict(row),
                    )
                )
            chosen = self.router.choose(rows, req.request_id, retry, req.session)
            jobs = []
            for index, row in enumerate(chosen):
                aid = f"{req.request_id}/{retry}/{index}"
                self.reservation_attempts += 1
                if not self.memory.reserve(aid, row.path):
                    self.blocked_reservations += 1
                    self.log("memory_blocked", req.request_id, aid)
                    continue
                attempt = Attempt(aid, req.request_id, row.path)
                self.attempts[aid] = attempt
                process = self.env.process(self.attempt(req, attempt, row))
                self.processes[aid] = process
                jobs.append(process)
            if jobs:
                req.admitted = True
                req.status = "active"
                self.log("admitted", req.request_id)
                yield simpy.events.AllOf(self.env, jobs)
                if req.status not in TERMINAL:
                    statuses = [
                        a.status for a in self.attempts.values() if a.parent_id == req.request_id
                    ]
                    status = "expired" if "expired" in statuses else "failed"
                    reasons = sorted(
                        {a.reason for a in self.attempts.values() if a.parent_id == req.request_id}
                    )
                    self.finish(req, status, ",".join(reasons))
                return
            if not rows:
                self.finish(req, "rejected", "no_path")
                return
            if retry < c.max_deferrals:
                req.deferrals += 1
                self.log("deferred", req.request_id)
                yield self.env.timeout(
                    min(
                        c.retry_seconds,
                        max(0, c.request_deadline_seconds - (self.env.now - req.arrival)),
                    )
                )
        self.finish(req, "rejected", "admission_or_memory_exhausted")

    def attempt(self, req, attempt, candidate):
        c, env = self.c, self.env
        aid, path = attempt.attempt_id, attempt.path
        attempt.start, attempt.status = env.now, "active"
        exposure_rate = sum(1 / self.coherences[n] for n in path)
        fidelity = c.initial_fidelity ** (len(path) - 1)
        if c.proxy_swap_factor:
            fidelity *= c.swap_success_probability ** (len(path) - 2)
        last = env.now
        token = None
        node = None
        cap = 0 if c.policy == "no_purification" else c.purification_round_cap
        deadline = req.arrival + c.request_deadline_seconds
        self.log(
            "reserved",
            req.request_id,
            aid,
            value=sum(self.memory.demand(path).values()),
            detail=str(path),
        )
        try:
            # Aggregate service already includes successful swapping. Link success is a separate
            # explicitly declared heralding assumption; default 1 avoids an invented loss rate.
            for hop, (u, v) in enumerate(zip(path, path[1:])):
                self.log("link_attempt", req.request_id, aid, node=u)
                if (
                    rng(c.seed, "hardware", req.request_id, path, hop, "link").random()
                    >= c.link_success_probability
                ):
                    attempt.status, attempt.reason = "failed", "link_failure"
                    return
            # Conservative expiry: terminate only when even all remaining gain rounds with ZERO
            # extra time cannot rescue the fidelity, or the independent request deadline hits.
            watcher = env.process(self.expiration(aid, deadline, fidelity, exposure_rate, cap))
            for hop, n in enumerate(path[:-1]):
                node = self.nodes[n]
                entered = env.now
                self.control.observe(n)
                token = node.resource.request()
                node.sample(env.now)
                self.log("queue_enter", req.request_id, aid, n, len(node.resource.queue))
                yield token
                node.sample(env.now)
                waited = env.now - entered
                attempt.queue_wait += waited
                self.log("service_start", req.request_id, aid, n, waited)
                duration = float(
                    rng(c.seed, "service", req.request_id, path, n, hop).exponential(1 / c.mu)
                )
                yield env.timeout(duration)
                attempt.service_time += duration
                fidelity = decay(fidelity, (env.now - last) * exposure_rate, c.event_fidelity_model)
                last = env.now
                node.completed += 1
                if env.now >= c.warmup_seconds:
                    node.waits.append(waited)
                    node.sojourns.append(env.now - entered)
                node.resource.release(token)
                token = None
                node.sample(env.now)
                self.log("service_end", req.request_id, aid, n, duration)
            if watcher.is_alive:
                watcher.interrupt("service_complete")
            # Actual delay can require a different number of rounds than the admission estimate.
            while fidelity < c.fidelity_threshold and attempt.purification_rounds < cap:
                if env.now + c.purification_time_seconds >= deadline:
                    attempt.status, attempt.reason = "expired", "deadline_during_purification"
                    return
                self.log("purification_start", req.request_id, aid, value=fidelity)
                yield env.timeout(c.purification_time_seconds)
                fidelity = delayed_round(
                    fidelity,
                    c.purification_efficiency,
                    c.purification_time_seconds,
                    exposure_rate,
                    c.event_fidelity_model,
                )
                attempt.purification_rounds += 1
                self.log("purification_end", req.request_id, aid, value=fidelity)
            req.attempted_deliveries += 1
            attempt.fidelity = fidelity
            if fidelity < c.fidelity_threshold:
                req.below_threshold += 1
                attempt.status, attempt.reason = "expired", "below_threshold"
            elif req.status == "completed":
                req.duplicates += 1
                attempt.status, attempt.reason = "duplicate", "already_delivered"
                self.log("duplicate", req.request_id, aid, value=fidelity)
            elif env.now >= deadline:
                attempt.status, attempt.reason = "expired", "request_deadline"
            else:
                attempt.status, attempt.reason = "completed", "qualifying_delivery"
                req.fidelity, req.path = fidelity, list(path)
                req.queue_wait, req.service_time = attempt.queue_wait, attempt.service_time
                req.sojourn = env.now - attempt.start
                self.finish(req, "completed", "qualifying_delivery")
        except simpy.Interrupt as exc:
            attempt.status = (
                "unfinished"
                if exc.cause == "termination"
                else ("expired" if exc.cause == "expiration" else "failed")
            )
            attempt.reason = str(exc.cause)
            self.log("interrupted", req.request_id, aid, detail=str(exc.cause))
        finally:
            if token is not None:
                if token in node.resource.users:
                    node.resource.release(token)
                else:
                    token.cancel()
                node.sample(env.now)
            self.memory.release(aid)
            attempt.end = env.now
            req.purification_rounds += attempt.purification_rounds
            self.log("released", req.request_id, aid, detail=attempt.status)

    def expiration(self, aid, deadline, fidelity, exposure_rate, cap):
        # Invert gain(f(t), cap) >= threshold. No resource-free improvement is delivered;
        # this bound only avoids premature cancellation of salvageable attempts.
        import math

        min_f = 1 - (1 - self.c.fidelity_threshold) * math.exp(self.c.purification_efficiency * cap)
        floor = 0 if self.c.event_fidelity_model == "paper_exponential" else 0.5
        limit = max(0, deadline - self.env.now)
        if min_f > floor and fidelity > floor:
            limit = min(
                limit, max(0, -math.log((min_f - floor) / (fidelity - floor)) / exposure_rate)
            )
        try:
            yield self.env.timeout(limit)
            process = self.processes[aid]
            if process.is_alive:
                process.interrupt("expiration")
        except simpy.Interrupt:
            return

    def rebuild_graph(self):
        self.graph.clear()
        self.graph.add_nodes_from(
            (n, a) for n, a in self.original.nodes(data=True) if not self.down_nodes[n]
        )
        self.graph.add_edges_from(
            (u, v, a)
            for u, v, a in self.original.edges(data=True)
            if u in self.graph and v in self.graph and not self.down_edges[tuple(sorted((u, v)))]
        )

    def failure(self, index, f):
        yield self.env.timeout(f.time)
        key = f.node if f.node is not None else tuple(sorted(f.edge))
        counts = self.down_nodes if f.node is not None else self.down_edges
        counts[key] += 1
        self.rebuild_graph()
        self.log("failure", detail=str(f.model_dump()))
        self.failure_connectivity.append(
            dict(
                time=self.env.now,
                event="failure",
                pairs=[pair_properties(self.graph, s, d) for s, d in self.sessions],
            )
        )
        for aid, process in list(self.processes.items()):
            path = self.attempts[aid].path
            affected = (
                key in path
                if f.node is not None
                else key in {tuple(sorted(e)) for e in zip(path, path[1:])}
            )
            if affected and process.is_alive:
                process.interrupt("node_failure" if f.node is not None else "edge_failure")
        yield self.env.timeout(f.duration)
        counts[key] -= 1
        self.rebuild_graph()
        self.log("recovery", detail=str(index))
        self.failure_connectivity.append(
            dict(
                time=self.env.now,
                event="recovery",
                pairs=[pair_properties(self.graph, s, d) for s, d in self.sessions],
            )
        )

    def run(self, progress=None, cancelled=None):
        if self.stopped:
            raise RuntimeError("A finalized Simulation cannot be resumed; create a fresh instance")
        end = self.c.simulation_duration_seconds
        step = min(10, end / 20)
        was_cancelled = False
        while self.env.now < end:
            if cancelled is not None and cancelled():
                was_cancelled = True
                break
            self.env.run(until=min(end, self.env.now + step))
            if progress:
                progress(self.env.now / end)
        now = self.env.now
        # Classify work in flight before cancellation cleanup changes individual attempts.
        for req in self.requests.values():
            if req.status not in TERMINAL:
                self.finish(req, "unfinished", "cancelled" if was_cancelled else "horizon")
        for process in list(self.processes.values()):
            if process.is_alive:
                process.interrupt("termination")
        # Interrupts have priority 0; process only cleanup events at the boundary.
        while self.env._queue and self.env._queue[0][0] == now and self.env._queue[0][1] <= 0:
            self.env.step()
        assert not self.memory.owners and not any(self.memory.used.values())
        assert all(not n.resource.queue and not n.resource.users for n in self.nodes.values())
        self.stopped = True
        return self.result(now, was_cancelled)

    def result(self, now, cancelled):
        c = self.c
        measurement = max(0, now - c.warmup_seconds)
        delivered = [
            r
            for r in self.requests.values()
            if r.status == "completed" and r.end >= c.warmup_seconds
        ]
        cohort = [r for r in delivered if r.arrival >= c.warmup_seconds]
        fidelity = [r.fidelity for r in delivered]
        latencies = [r.end - r.arrival for r in cohort]
        counts = dict(Counter(r.status for r in self.requests.values()))
        offered_measurement = sum(r.arrival >= c.warmup_seconds for r in self.requests.values())
        summary = dict(
            schema_version=1,
            profile=c.profile,
            policy=c.policy,
            cancelled=cancelled,
            elapsed_simulation_seconds=now,
            measurement_seconds=measurement,
            offered=len(self.requests),
            offered_measurement=offered_measurement,
            admitted=sum(r.admitted for r in self.requests.values()),
            terminal_counts=counts,
            deferred_requests=sum(r.deferrals > 0 for r in self.requests.values()),
            deferral_events=sum(r.deferrals for r in self.requests.values()),
            delivered_measurement=len(delivered),
            latency_cohort_n=len(cohort),
            throughput=len(delivered) / measurement if measurement else None,
            offered_rate=offered_measurement / measurement if measurement else None,
            total_configured_arrival_rate=c.arrival_rate
            * (len(self.sessions) if c.traffic_convention == "per_session" else 1),
            mean_fidelity=float(np.mean(fidelity)) if fidelity else None,
            mean_queue_wait=float(np.mean([r.queue_wait for r in cohort])) if cohort else None,
            mean_sojourn=float(np.mean([r.sojourn for r in cohort])) if cohort else None,
            mean_latency=float(np.mean(latencies)) if latencies else None,
            latency_quantiles={
                str(q): float(np.quantile(latencies, q)) if latencies else None
                for q in (0.5, 0.95, 0.99)
            },
            attempted_deliveries=sum(r.attempted_deliveries for r in self.requests.values()),
            duplicates=sum(r.duplicates for r in self.requests.values()),
            below_threshold=sum(r.below_threshold for r in self.requests.values()),
            pair_yield=sum(r.status == "completed" for r in self.requests.values())
            / len(self.requests)
            if self.requests
            else None,
            memory_blocking=self.blocked_reservations / self.reservation_attempts
            if self.reservation_attempts
            else None,
            reservation_attempts=self.reservation_attempts,
            memory_blocked_attempts=self.blocked_reservations,
            drops_by_cause=dict(
                Counter(
                    r.reason
                    for r in self.requests.values()
                    if r.status in ("rejected", "expired", "failed")
                )
            ),
            resources_after_cleanup=sum(self.memory.used.values()),
            failure_connectivity=self.failure_connectivity,
            request_conservation=sum(counts.values()) == len(self.requests),
        )
        nodes = []
        for n, node in self.nodes.items():
            nodes.append(
                dict(
                    schema_version=1,
                    node=n,
                    mu=c.mu,
                    coherence=self.coherences[n],
                    mean_queue=node.queue.mean(now),
                    mean_system=node.system.mean(now),
                    utilization=node.busy.mean(now),
                    mean_qubits=self.memory.occupancy[n].mean(now),
                    peak_qubits=self.memory.occupancy[n].maximum,
                    time_full_fraction=self.memory.full[n].mean(now),
                    completed_jobs=node.completed,
                    mean_queue_wait=float(np.mean(node.waits)) if node.waits else None,
                    mean_sojourn=float(np.mean(node.sojourns)) if node.sojourns else None,
                )
            )
        topology = nx.node_link_data(self.original)
        topology.update(
            sessions=self.sessions,
            coherences=self.coherences,
            pair_properties=[pair_properties(self.original, s, d) for s, d in self.sessions],
        )
        return Result(
            1,
            c.model_dump(mode="json"),
            topology,
            [asdict(r) for r in self.requests.values()],
            [asdict(a) for a in self.attempts.values()],
            self.events,
            nodes,
            self.path_metrics,
            summary,
        )
