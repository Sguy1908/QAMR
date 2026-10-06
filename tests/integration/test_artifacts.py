from pathlib import Path

from qamr_sim.config import Config
from qamr_sim.experiments.runner import run_one
from qamr_sim.io.export import load_run


def test_real_artifacts_resume_and_empty_tables(tmp_path):
    c = Config(nodes=5, radius=1, simulation_duration_seconds=5, arrival_rate=2)
    directory = run_one(c, tmp_path, figures=False)
    assert directory == run_one(c, tmp_path, figures=False)
    run = load_run(directory)
    assert len(run["requests"]) > 0
    assert run["summary"]["request_conservation"]
    assert "paper_checksum" in run["manifest"]  # Local PDF is intentionally absent in CI
    assert (directory / "report.md").exists()
    empty = run_one(
        Config.model_validate({**c.model_dump(), "arrival_rate": 0}), tmp_path, figures=False
    )
    assert list(load_run(empty)["requests"].columns) == list(run["requests"].columns)
    assert len(list(Path(tmp_path).glob("*/complete.json"))) == 2


def test_cancelled_overwrite_has_no_complete_marker(tmp_path):
    c = Config(nodes=5, radius=1, simulation_duration_seconds=5, arrival_rate=2)
    directory = run_one(c, tmp_path, figures=False)
    assert (directory / "complete.json").exists()
    overwritten = run_one(c, tmp_path, resume=False, figures=False, cancelled=lambda: True)
    assert overwritten == directory
    assert not (directory / "complete.json").exists()
    assert load_run(directory)["summary"]["cancelled"]


def test_failed_run_retains_config_and_error(tmp_path, monkeypatch):
    import pytest

    from qamr_sim.engine.simulation import Simulation

    def fail(*args, **kwargs):
        raise RuntimeError("injected engine failure")

    monkeypatch.setattr(Simulation, "run", fail)
    with pytest.raises(RuntimeError, match="injected"):
        run_one(Config(), tmp_path, figures=False)
    directories = list(tmp_path.iterdir())
    assert len(directories) == 1
    directory = directories[0]
    assert (directory / "failure.json").exists()
    assert (directory / "resolved_config.yaml").exists()
    assert (directory / "manifest.json").exists()
    assert not (directory / "complete.json").exists()
