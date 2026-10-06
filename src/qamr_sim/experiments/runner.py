import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from qamr_sim.engine.simulation import Simulation
from qamr_sim.io.export import export, load_run, write_json
from qamr_sim.models.analytical import redundancy_throughput

from .manifest import digest, manifest


def report_run(directory):
    run = load_run(directory)
    s, c = run["summary"], run["config"]
    paths = run["path_metrics"]
    proxy = None
    if len(paths):
        first = paths[paths.request_id == paths.request_id.iloc[0]]
        proxy = redundancy_throughput(
            s["total_configured_arrival_rate"],
            [len(p) - 1 for p in first.path],
            c["link_success_probability"],
            c["swap_success_probability"],
            s["memory_blocking"] or 0,
        )
    content = f"""# Paper reconstruction run

Profile: {c["profile"]}; policy: {c["policy"]}; fidelity: {c["event_fidelity_model"]}.
Traffic convention: {c["traffic_convention"]}; configured total: {s["total_configured_arrival_rate"]} req/s.
Measurement: {s["measurement_seconds"]} s; warm-up: {c["warmup_seconds"]} s.

- Offered: {s["offered"]}; terminal outcomes: {s["terminal_counts"]}.
- Unique measured throughput: {s["throughput"]} pairs/s.
- Delivered mean fidelity: {s["mean_fidelity"]}; sample size: {s["delivered_measurement"]}.
- Queue-only mean: {s["mean_queue_wait"]} s; path sojourn: {s["mean_sojourn"]} s.
- End-to-end mean: {s["mean_latency"]} s; quantiles: {s["latency_quantiles"]}.
- Request conservation: {s["request_conservation"]}; released resources: {s["resources_after_cleanup"]} remain.
- Eq. (26) illustration on first evaluated session candidates: {proxy} pairs/s.
  This assumes independent redundant attempts; observed reservation blocking is used as an
  explicitly approximate P_full. It is not a split-traffic prediction or a fit.

## Discrepancies and applicability

Published comparisons: peak 1.45 pairs/s; relative gain 40–60%; moderate-load
fidelity 0.913–0.918; reported mean delay about 0.37 s (quantity unspecified).
These are reference statements, not pass criteria. Figure 3 visually shows the
baseline above QAMR at all plotted loads, inconsistent with the surrounding prose.
The paper's 0.37 s and its multi-second Figure 4 cannot be assigned a common
cohort from the available text. Sampled maxima do not prove bounded M/M/1 delay.

This run uses one unique pair per parent. With total traffic 1 req/s, sustained
1.45 unique pairs/s is incompatible with that offered rate/yield (finite-window
throughput can differ from its expectation). Per-session interpretation changes
network traffic explicitly. No target-fitting or graph acceptance conditioning occurs.

The reserved-chain aggregate service model is an implementation assumption;
Eq. (5) is logged separately from its resource-aging estimate. The endpoint chain
ages during queueing, service, and purification. This is not a microscopic protocol.
M/M/1 formulas apply to isolated stationary queues, not automatically to admission,
finite-memory, interrupted, or tandem path processes. Capacity sums double-count
shared resources; Eq. (26) assumes independent path success.

Latency/CDFs include requests arriving after warm-up and successfully delivered
before the horizon. Rejected/expired/unfinished requests remain in accounting;
this completed cohort has selection and right-censoring bias. Throughput counts
all post-warm-up delivery events, including requests offered before warm-up.
Single runs have no independent-replication confidence interval.

Topology formal r-robustness is unknown. Inspect topology.json for separate
vertex connectivity and pairwise vertex-/edge-disjoint path counts.
"""
    (Path(directory) / "report.md").write_text(content)
    return content


def run_one(
    config, output="results/manual", resume=True, figures=True, progress=None, cancelled=None
):
    meta = manifest(config)
    run_id = digest(
        json.dumps(
            {
                k: meta[k]
                for k in ("config_hash", "code_hash", "paper_checksum", "versions", "python")
            },
            sort_keys=True,
        ).encode()
    )[:20]
    directory = Path(output) / run_id
    if resume and (directory / "complete.json").exists():
        if figures and any(
            not (directory / "figures" / f"{name}.{extension}").exists()
            for name in ("waiting_cdf", "queue_memory")
            for extension in ("png", "svg", "pdf")
        ):
            from qamr_sim.plotting.paper_figures import run_figures

            run_figures(load_run(directory))
        return directory
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "complete.json").unlink(missing_ok=True)
    (directory / "failure.json").unlink(missing_ok=True)
    (directory / "resolved_config.yaml").write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=True)
    )
    meta["started_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(directory / "manifest.json", meta)
    started = time.perf_counter()
    try:
        result = Simulation(config).run(progress, cancelled)
        meta["runtime_seconds"] = time.perf_counter() - started
        meta["topology_hash"] = digest(json.dumps(result.topology, sort_keys=True).encode())
        export(result, directory, meta)
        report_run(directory)
        if figures:
            from qamr_sim.plotting.paper_figures import run_figures

            run_figures(load_run(directory))
        if not result.summary["cancelled"]:
            write_json(directory / "complete.json", dict(run_id=run_id, schema_version=1))
        return directory
    except Exception as exc:
        meta["runtime_seconds"] = time.perf_counter() - started
        write_json(directory / "manifest.json", meta)
        write_json(directory / "failure.json", dict(type=type(exc).__name__, message=str(exc)))
        raise
