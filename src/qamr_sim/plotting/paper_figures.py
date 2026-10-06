"""Only saved observations; published targets are text comparisons, never data."""

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/qamr-matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save(fig, directory, name):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ("png", "svg", "pdf"):
        fig.savefig(directory / f"{name}.{ext}", dpi=150)
    plt.close(fig)


def run_figures(run):
    out = run["directory"] / "figures"
    requests = run["requests"]
    cohort = requests[
        (requests.status == "completed") & (requests.arrival >= run["config"]["warmup_seconds"])
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    for column, label in [("queue_wait", "Queue-only wait"), ("sojourn", "Reserved-path sojourn")]:
        data = np.sort(cohort[column].to_numpy())
        if len(data):
            ax.step(
                data,
                np.arange(1, len(data) + 1) / len(data),
                where="post",
                label=f"{label} (n={len(data)})",
            )
    ax.set(
        xlabel="Seconds",
        ylabel="Empirical CDF",
        title=f"{run['config']['policy']} · {run['config']['profile']}",
    )
    if len(cohort):
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No qualifying delivery cohort", ha="center", transform=ax.transAxes)
    save(fig, out, "waiting_cdf")
    fig, ax = plt.subplots(figsize=(8, 4))
    nodes = run["node_metrics"]
    ax.bar(nodes.node - 0.2, nodes.mean_queue, width=0.4, label="Classical waiting jobs")
    ax.bar(nodes.node + 0.2, nodes.mean_qubits, width=0.4, label="Reserved qubits")
    ax.set(
        xlabel="Node",
        ylabel="Time-average count",
        title="Queue state and physical memory are distinct",
    )
    ax.legend()
    save(fig, out, "queue_memory")


def comparison_figures(frame, directory):
    from qamr_sim.experiments.statistics import interval

    for metric, label in [
        ("throughput", "Unique qualifying pairs/s"),
        ("mean_fidelity", "Delivered mean fidelity"),
    ]:
        fig, ax = plt.subplots(figsize=(7, 4))
        for policy, group in frame.groupby("policy"):
            points = []
            for rate, g in group.groupby("arrival_rate"):
                ci = interval(g[metric].tolist())
                if ci["mean"] is not None:
                    points.append((rate, ci))
            if points:
                ax.errorbar(
                    [p[0] for p in points],
                    [p[1]["mean"] for p in points],
                    yerr=[0 if p[1]["low"] is None else p[1]["mean"] - p[1]["low"] for p in points],
                    marker="o",
                    label=policy,
                )
        ax.set(
            xlabel="Configured arrival rate (requests/s)",
            ylabel=label,
            title=f"Independent-run means and 95% t intervals · {len(frame)} runs",
        )
        if len(frame):
            ax.legend()
        save(fig, directory, metric)


def comparison_cdf(frame, directory):
    """Saved completed-cohort CDFs at largest configured load, pooled descriptively.

    Event samples are correlated; only run-level means get confidence intervals.
    """
    import pandas as pd
    import yaml

    load = frame.arrival_rate.max()
    selected = frame[frame.arrival_rate == load]
    fig, ax = plt.subplots(figsize=(7, 4))
    for policy, group in selected.groupby("policy"):
        data = []
        for run_path in group.run:
            path = Path(run_path)
            config = yaml.safe_load((path / "resolved_config.yaml").read_text())
            requests = pd.read_parquet(path / "requests.parquet")
            cohort = requests[
                (requests.status == "completed") & (requests.arrival >= config["warmup_seconds"])
            ]
            data.extend(cohort.queue_wait.tolist())
        if data:
            values = np.sort(data)
            ax.step(
                values,
                np.arange(1, len(values) + 1) / len(values),
                where="post",
                label=f"{policy}: n={len(values)}, runs={len(group)}",
            )
    ax.set(
        xlabel="Queue-only waiting time (s)",
        ylabel="Empirical CDF",
        title=f"Completed post-warmup arrivals · configured load {load} req/s",
    )
    if ax.lines:
        ax.legend(fontsize=8)
    save(fig, directory, "comparison_waiting_cdf")
