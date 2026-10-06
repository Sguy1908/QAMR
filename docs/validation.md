# Validation evidence

Executed locally on 2026-10-06, CPython 3.14.4, exact versions in requirements.lock.
These checks establish internal mathematical consistency and engineering properties,
not independent reproduction of the paper's unpublished experiments.

## Actual checks

| Command / check | Observed outcome |
|---|---|
| Install all pinned dependencies from requirements.lock | Successful |
| `pip install --no-deps --no-build-isolation -e .` | Successful editable package / CLI |
| `pip check` | No broken requirements |
| `pytest -q` | 38 passed; 2 statistical tests deselected |
| `pytest -q -m statistical` | 2 passed; fast tests deselected |
| `ruff check .` and `ruff format --check .` | Passed |
| `qamr-sim run --config configs/smoke.yaml` | Real request/event/node/path Parquet, report and PNG/SVG/PDF figures |
| `qamr-sim reproduce --preset smoke` | 27 completed policy/replication runs |
| Reduced 60-node, 2000-s suites | 315 runs, zero failed runs; see reproduction.md |
| `python scripts/audit_results.py` | Independently checks exported request/attempt/slot invariants across saved runs |
| Streamlit AppTest initial page and saved-run load | No exceptions; configuration and eight data tables/four metrics render |
| Rendered waiting CDF and comparison chart inspection | Readable axes, sample counts and distinct quantities |

Fast tests cover queue metric semantics, rate/units, fidelity limits and inverted
bounds, delayed purification gain, literal utilization scoring, admission-vs-node
counterexample, binary selection constraints/objective, Eq. (26) limits, formal
r-robustness versus connectivity, disjoint paths, invalid configs, seeded equality,
trace independence, matched baselines, atomic reservation rollback, no traffic/path,
overload, unique parent throughput with duplicate attempts, failure while resources
are held, overlapping failures/recovery, expiry, horizon/cancellation, warmup integrals,
shared bottlenecks, paid purification events, impossible slot demand, lifetime
interpretations, traffic scope, complete artifacts/empty schemas/resume, cancelled
overwrite markers, and failure provenance retention.

The horizon test exposed a cleanup bug during development: a higher-priority boundary
event prevented urgent interrupts from draining. Cleanup now processes all urgent
boundary events and asserts both memory and server-token release. The artifact tests
also protect against stale complete markers after cancelling an overwrite.

## Independent stationary queue experiments

20 independent runs per validation command, each 20,000 s with 2,000 s warmup.
95% Student-t intervals use the 20 run means, not correlated service completions.
Raw summaries: [M/M/1](evidence/mm1.json), [M/M/1/K](evidence/mm1k.json).

| Quantity | Analytical | Simulated mean | 95% CI |
|---|---:|---:|---:|
| M/M/1 L, lambda=.6, mu=1 | 1.5 | 1.50495 | [1.47318, 1.53671] |
| M/M/1 W (sojourn), seconds | 2.5 | 2.50464 | [2.45786, 2.55141] |
| M/M/1 Wq, seconds | 1.5 | 1.50681 | [1.46350, 1.55013] |
| M/M/1/K L, lambda=1.2, mu=1, K=4 | 2.35949 | 2.35631 | [2.34519, 2.36742] |
| M/M/1/K blocking | 0.27865 | 0.27667 | [0.27397, 0.27936] |
| M/M/1/K W, seconds | 2.72578 | 2.71752 | [2.70151, 2.73352] |

K includes service. This is a standalone finite classical buffer; it does not
validate treating reserved quantum memory/expiry/admission as M/M/1/K. Statistical
pytest uses 12 independent seeds, six-standard-error tolerances with a 2% finite-run
floor for L/W and explicit tolerances for Wq/blocking/Little's law. Wider test gates
limit stochastic false failures; the separately reported confidence intervals stay
95%. No test checks proximity to 1.45 pairs/s or the paper's fidelity targets.

## Limits

Three topology replications per reduced scientific scenario are exploratory, not
precise Monte Carlo evidence. Means can hide disconnected-session variability.
The supported engine is aggregate successful service with abstract purification
supply. It cannot validate a physical microscopic protocol. No global optimization,
independent raw-data comparison, or formal 60-node r-robustness certificate exists.
