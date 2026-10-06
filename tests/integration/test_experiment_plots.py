import pandas as pd
import yaml

from qamr_sim.config import Config
from qamr_sim.experiments.runner import run_one
from qamr_sim.experiments.sweeps import sweep


def test_experiment_generates_run_and_comparison_plots(tmp_path):
    base = tmp_path / "base.yaml"
    base.write_text(
        yaml.safe_dump(
            Config(nodes=5, radius=1, simulation_duration_seconds=5, arrival_rate=2).model_dump(
                mode="json"
            )
        )
    )
    spec = tmp_path / "sweep.yaml"
    spec.write_text(
        yaml.safe_dump(dict(base=str(base), name="plot_check", repetitions=1, policies=["qamr"]))
    )
    directory = sweep(spec, output=tmp_path / "results")
    frame = pd.read_parquet(directory / "replications.parquet")
    assert len(frame) == 1
    from pathlib import Path

    run = Path(frame.iloc[0]["run"])
    for extension in ("png", "svg", "pdf"):
        for name in ("waiting_cdf", "queue_memory"):
            assert (run / "figures" / f"{name}.{extension}").stat().st_size > 0
        for name in ("throughput", "mean_fidelity", "comparison_waiting_cdf"):
            assert (directory / "figures" / "0" / f"{name}.{extension}").stat().st_size > 0

    # A partially deleted plot set must be repaired without changing measured data.
    requests = (run / "requests.parquet").read_bytes()
    missing = run / "figures" / "queue_memory.pdf"
    missing.unlink()
    config = Config.model_validate(yaml.safe_load(base.read_text()))
    assert run_one(config, directory) == run
    assert missing.stat().st_size > 0
    assert (run / "requests.parquet").read_bytes() == requests
