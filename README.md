# QAMR paper reconstruction

An auditable Python/SimPy discrete-event simulator for Goenka et al.,
*Queue-Aware Multi-Path Entanglement Distribution in r-Robust Hybrid
Quantum-Classical Networks under NISQ Constraints*, DOI
10.1109/ICICI68867.2026.11565029.

This is a **paper reconstruction**, not exact reproduction. It preserves all 26
published analytical equations while making incomplete event semantics explicit.
It includes real queues, finite endpoint memories, paid purification, expiry,
matched routing baselines, sweeps, statistics, plots, and a Streamlit dashboard.
No original code/raw data is available. No proprietary service or login is needed.

## Install and run

The checked environment is CPython 3.14 on Linux; source requires Python >=3.11.
`requirements.lock` pins the tested full dependency set (older Python versions may
need a separately resolved compatible environment). From this repository:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/qamr-sim validate-config configs/paper.yaml
.venv/bin/qamr-sim run --config configs/smoke.yaml
.venv/bin/qamr-sim reproduce --preset smoke
.venv/bin/streamlit run dashboard/app.py
.venv/bin/pytest -q
.venv/bin/ruff check .
```

Equivalent with uv (when installed): `uv venv --python 3.14`,
`uv pip sync requirements.lock`, `uv pip install --no-deps --no-build-isolation -e .`,
then `uv run --no-sync qamr-sim run --config configs/smoke.yaml`.
The pip lock is the reproducible-environment equivalent of uv.lock; plain `uv sync`
would resolve a different environment and is not the pinned installation command.

Keep your authorized reference at `docs/paper/qamr.pdf` (ignored by Git).
The repository does not distribute the paper or assign a legal license on the
owner's behalf. Runs without the PDF are allowed for CI/offline engine tests but
have a null paper checksum and cannot identify an audited source copy.

## Research workflow

```bash
.venv/bin/qamr-sim sweep --config configs/sweeps/arrival_rate.yaml
.venv/bin/qamr-sim sweep --config configs/sweeps/reduced.yaml
.venv/bin/qamr-sim reproduce --preset research
.venv/bin/qamr-sim validate-queue --config configs/validation_mm1.yaml
.venv/bin/qamr-sim validate-queue --config configs/validation_mm1k.yaml
.venv/bin/pytest -q -m statistical
.venv/bin/qamr-sim report --results results/arrival_rate
```

Research uses 20 independent replications and paired policies, saving raw Parquet,
resolved YAML, seeds, topology, code/paper hashes, environment versions, reports,
and PDF/SVG/PNG figures. Reduced runs retain 60 nodes and 2000 s with three rates
and three replications. All failures and unfavorable outcomes remain visible.
See [reproduction](docs/reproduction.md) for actual executed coverage and cost.

Plots are generated automatically after each run, including runs within `sweep`
and `reproduce`. Each run's `figures/` directory contains waiting-time CDFs and
queue/memory plots in PNG, SVG, and PDF. At the end of a sweep, comparison plots
(throughput, fidelity, and waiting-time CDF) are saved under the experiment's
`figures/` directory, grouped by scenario. The CLI prints these locations.
Resuming a completed run restores missing plot files without rerunning the simulation.
For individual `run` commands, `--no-figures` explicitly disables plotting.

The default geometric graph is sampled once, without connectivity conditioning.
Some sessions may have no path. This is a meaningful recorded outcome, not an
excuse to regenerate until QAMR looks favorable. `formal_r_robustness=unknown` is
separate from vertex connectivity and internally disjoint paths.

## Scientific boundaries

The default has one unique delivered pair per request, network-total lambda,
xi=1, and exponential aggregate successful service. These are transparent choices,
not recovered original code. Slot occupancy differs from M/M/1 mean number;
queue waiting differs from sojourn. Both published fidelity laws are named options.
Endpoint aging and purification supply assumptions can dominate results; no
microscopic quantum protocol is claimed. A stable M/M/1 queue has unbounded delay
support. Published targets are comparison statements, never test assertions.

Read [traceability](docs/paper_traceability.md), [assumptions](docs/assumptions.md),
[model](docs/model.md), [metrics](docs/metrics/definitions.md),
[validation](docs/validation.md), and [development](docs/development.md).

For offline installation on the same platform, prepare a wheelhouse on a connected
machine with `pip download -r requirements.lock -d wheelhouse`, then install using
`pip install --no-index --find-links wheelhouse -r requirements.lock`. Runtime is
entirely local. Paper/large run data and the virtual environment remain untracked.
