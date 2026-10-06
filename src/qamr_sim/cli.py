"""CLI entry points. No network services required."""

import json
from pathlib import Path

import pandas as pd
import typer

from qamr_sim.config import load_config
from qamr_sim.engine.queue_validation import isolated_queue
from qamr_sim.experiments.runner import report_run, run_one
from qamr_sim.experiments.sweeps import summarize
from qamr_sim.experiments.sweeps import sweep as execute_sweep

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


@app.command("validate-config")
def validate_config(path: Path):
    config = load_config(path)
    typer.echo(config.model_dump_json(indent=2))


@app.command()
def run(
    config: Path = typer.Option(Path("configs/smoke.yaml")),
    output: Path = typer.Option(Path("results/manual")),
    resume: bool = True,
    figures: bool = True,
):
    directory = run_one(load_config(config), output, resume, figures)
    typer.echo(str(directory))
    if figures:
        typer.echo(f"Plots saved to {directory / 'figures'} (PNG, SVG, PDF)")


@app.command()
def sweep(config: Path = typer.Option(...), output: Path = Path("results")):
    directory = execute_sweep(
        config, output, lambda done, total: typer.echo(f"{done}/{total} runs")
    )
    show_experiment_outputs(directory)


def show_experiment_outputs(directory):
    typer.echo(str(directory))
    typer.echo(f"Comparison plots: {directory / 'figures'} (PNG, SVG, PDF)")
    typer.echo(f"Per-run plots: {directory}/<run_id>/figures/")


@app.command()
def reproduce(preset: str = typer.Option("smoke")):
    if preset == "smoke":
        show_experiment_outputs(execute_sweep("configs/sweeps/smoke.yaml"))
    elif preset == "research":
        for name in (
            "arrival_rate",
            "memory",
            "coherence",
            "robustness",
            "fidelity_models",
            "traffic",
            "dispatch",
            "path_service",
            "lifetime",
            "failures",
        ):
            show_experiment_outputs(
                execute_sweep(
                    f"configs/sweeps/{name}.yaml",
                    progress=lambda done, total: typer.echo(f"{done}/{total} runs"),
                )
            )
    else:
        raise typer.BadParameter("preset must be smoke or research")


@app.command()
def report(results: Path = typer.Option(...)):
    if (results / "summary.json").exists():
        typer.echo(report_run(results))
    else:
        summarize(pd.read_parquet(results / "replications.parquet"), results)
        typer.echo(str(results / "report.md"))


@app.command("validate-queue")
def validate_queue(config: Path = typer.Option(Path("configs/validation_mm1.yaml"))):
    import yaml

    from qamr_sim.experiments.statistics import interval
    from qamr_sim.models.queueing import mm1, mm1k

    spec = yaml.safe_load(config.read_text())
    reps = spec.pop("repetitions", 10)
    rows = [isolated_queue(**spec, seed=i) for i in range(reps)]
    ref = (
        mm1k(spec["lam"], spec["mu"], spec["capacity"])
        if spec.get("capacity")
        else mm1(spec["lam"], spec["mu"])
    )
    typer.echo(
        json.dumps(
            dict(reference=ref, observed={k: interval([r[k] for r in rows]) for k in rows[0]}),
            indent=2,
        )
    )


if __name__ == "__main__":
    app()
