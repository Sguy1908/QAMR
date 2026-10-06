import itertools
import json
from pathlib import Path

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field

from qamr_sim.config import Config, load_config
from qamr_sim.io.export import write_json
from qamr_sim.plotting.paper_figures import comparison_cdf, comparison_figures

from .manifest import identity
from .runner import run_one
from .statistics import interval


class Sweep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: str = "configs/paper.yaml"
    name: str
    repetitions: int = Field(default=20, ge=1)
    independent_topologies: bool = True
    policies: list[str] = ["qamr", "single_path", "queue_aware_single"]
    grid: dict[str, list] = {}
    overrides: dict = {}


def summarize(frame, directory):
    records = []
    if not len(frame):
        return
    # Retain scenario identity so no sensitivity settings are silently pooled.
    for (scenario, policy), group in frame.groupby(["scenario", "policy"]):
        for metric in ("throughput", "mean_fidelity", "mean_queue_wait", "mean_latency"):
            records.append(
                dict(
                    scenario=scenario,
                    policy=policy,
                    metric=metric,
                    **interval(group[metric].tolist()),
                )
            )
    pd.DataFrame(records).to_csv(Path(directory) / "confidence_intervals.csv", index=False)
    paired = []
    for scenario, group in frame.groupby("scenario"):
        for metric in ("throughput", "mean_fidelity", "mean_latency"):
            pivot = group.pivot(index="replication", columns="policy", values=metric)
            if "qamr" in pivot and "single_path" in pivot:
                paired.append(
                    dict(
                        scenario=scenario,
                        metric=metric,
                        **interval((pivot.qamr - pivot.single_path).tolist()),
                    )
                )
    pd.DataFrame(paired).to_csv(Path(directory) / "paired_differences.csv", index=False)
    # One plot family per non-arrival scenario; never pool memory/coherence/profile axes.
    groupcols = [c for c in frame.columns if c.startswith("axis_") and c != "axis_arrival_rate"]
    groups = frame.groupby(groupcols, dropna=False) if groupcols else [("all", frame)]
    for index, (_, group) in enumerate(groups):
        comparison_figures(group, Path(directory) / "figures" / str(index))
        comparison_cdf(group, Path(directory) / "figures" / str(index))
    failures = frame.attrs.get("failures", [])
    (Path(directory) / "report.md").write_text(
        "# Experiment report\n\n"
        f"{len(frame)} completed replications. {len(failures)} failed runs. "
        "Raw runs: replications.parquet. 95% Student-t intervals use independent run-level "
        "observations, with undefined metrics omitted and n reported. Paired differences align "
        "the same seed/topology and scenario; offered schedules are identical across policies. "
        "Common keyed service draws align only for matching request/path/node keys. "
        "Inspect topology_seed for per-topology variation. Targets are comparisons, not tests.\n\n"
        "Each run report details censoring, traffic convention, analytical applicability, "
        "and published discrepancies. Formal graph robustness remains unknown.\n"
    )


def sweep(path, output="results", progress=None, cancelled=None):
    spec = Sweep.model_validate(yaml.safe_load(Path(path).read_text()))
    base_config = load_config(spec.base)
    base = base_config.model_dump()
    expected_identity = identity(base_config)
    directory = Path(output) / spec.name
    directory.mkdir(parents=True, exist_ok=True)
    keys = list(spec.grid)
    combinations = list(itertools.product(*(spec.grid[k] for k in keys)))
    rows, failures = [], []
    total = len(combinations) * spec.repetitions * len(spec.policies)
    done = 0
    for values in combinations:
        if cancelled and cancelled():
            break
        overrides = dict(zip(keys, values))
        scenario = json.dumps(overrides, sort_keys=True)
        for rep in range(spec.repetitions):
            if cancelled and cancelled():
                break
            for policy in spec.policies:
                if cancelled and cancelled():
                    break
                resolved = {
                    **base,
                    **spec.overrides,
                    **overrides,
                    "policy": policy,
                    "seed": base["seed"] + rep,
                    "topology_seed": base["topology_seed"]
                    + (rep if spec.independent_topologies else 0),
                }
                config = Config.model_validate(resolved)
                current = identity(base_config)
                if current != expected_identity:
                    raise RuntimeError(
                        "Code, paper, or environment changed during sweep; "
                        "resume with a stable workspace"
                    )
                try:
                    run = run_one(config, directory, figures=True, cancelled=cancelled)
                    summary = json.loads((run / "summary.json").read_text())
                    if summary["cancelled"]:
                        break
                    rows.append(
                        dict(
                            scenario=scenario,
                            replication=rep,
                            policy=policy,
                            seed=config.seed,
                            topology_seed=config.topology_seed,
                            run=str(run),
                            arrival_rate=config.arrival_rate,
                            profile=config.profile,
                            **{
                                "axis_" + k: json.dumps(v) if isinstance(v, (list, dict)) else v
                                for k, v in overrides.items()
                            },
                            **{
                                m: summary[m]
                                for m in (
                                    "throughput",
                                    "mean_fidelity",
                                    "mean_queue_wait",
                                    "mean_latency",
                                    "offered",
                                    "delivered_measurement",
                                )
                            },
                        )
                    )
                except Exception as exc:
                    failures.append(
                        dict(scenario=scenario, replication=rep, policy=policy, error=str(exc))
                    )
                done += 1
                if progress:
                    progress(done, total)
                pd.DataFrame(rows).to_parquet(directory / "replications.parquet", index=False)
                write_json(directory / "failures.json", failures)
    frame = pd.DataFrame(rows)
    frame.attrs["failures"] = failures
    if len(frame):
        summarize(frame, directory)
    write_json(
        directory / "sweep_manifest.json",
        dict(
            schema_version=1,
            spec=spec.model_dump(),
            planned_runs=total,
            completed_runs=len(rows),
            failed_runs=len(failures),
            interrupted=bool(cancelled and cancelled()),
            identity=expected_identity,
        ),
    )
    return directory
