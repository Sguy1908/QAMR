# Executed paper reconstruction and discrepancies

This is a paper reconstruction from the six-page PDF, not an exact reproduction.
All original scientific targets remain comparisons, never fitted parameters or test
assertions. No graph was redrawn for favorable performance.

## Executed on 2026-10-06

- One traced smoke run, including Parquet and PNG/SVG/PDF outputs.
- 27 smoke sweep runs (12-node preset, 100 s, three rates and three replications).
- 315 paper-sized runs (60 nodes, 2000 s, three independent topology/traffic seeds
  per scenario), with zero failed runs:

| Saved experiment directory under results/ | Runs | Coverage |
|---|---:|---|
| reduced | 27 | lambda .1/.5/1, QAMR/fixed single/best-score single |
| reduced_memory | 36 | 8/12/16/24 qubits |
| reduced_coherence | 27 | 30/50/70 s central lifetimes |
| reduced_robustness | 36 | rmax 1/2; six policies including ablations |
| reduced_fidelity_models | 36 | both routing and event fidelity laws, including crossed choices |
| reduced_traffic | 18 | total versus per-session offered rates |
| reduced_dispatch | 27 | split, replicated children, round-robin |
| reduced_path_service | 54 | bottleneck/serial capacity proxies; steady/rolling/literal-full load |
| reduced_lifetime | 27 | bounded uniform, positive truncated normal, fixed |
| reduced_failures | 27 | no failures, scheduled node outage, scheduled edge outage |

The failure sweep's fixed edge (0,1) is not guaranteed to exist in each unconditional
random graph, and node 0 need not lie on selected session paths. Such scenarios can
be no-ops. Inspect the saved topology and before/after pair connectivity; do not
interpret unchanged metrics as proven fault tolerance. Deterministic integration
tests separately inject real outages into active held paths and verify cleanup.

Every scenario has independent *within-scenario* seed replications. Seeds are shared
across scenarios/policies for paired comparisons; the 315 runs are not 315 mutually
independent samples of one scientific condition. Study-specific uncertainty is in
confidence_intervals.csv and paired_differences.csv. Raw replication tables retain
scenario, topology_seed, policy and paths to all run artifacts.

## Observed main comparison

Means over three topology/traffic replications, network-total arrival convention:

| Configured lambda | QAMR pairs/s | Single-path pairs/s | QAMR fidelity | Single-path fidelity |
|---|---:|---:|---:|---:|
| 0.1 | 0.08283 | 0.08283 | 0.91013 | 0.92467 |
| 0.5 | 0.41167 | 0.41167 | 0.91162 | 0.92498 |
| 1.0 | 0.82750 | 0.82767 | 0.91140 | 0.92513 |

QAMR does **not** show the reported 40–60% throughput gain under these transparent
defaults. Mu=13.571/s (xi=1) leaves these loads far from aggregate saturation.
Memory 8/12/16/24 gives identical measured throughput here. At lambda=.5, changing
central coherence 30 -> 50 -> 70 gives QAMR fidelity .90554 -> .91162 -> .91193,
without an observed throughput change. The no-purification ablation reduces mean
throughput to .07917 pairs/s at this load. Replication can select a higher-fidelity
first completion, but duplicate successes never increase unique-parent throughput.

The topology seeds 17/18/19 produced achieved mean degrees 3.967/3.700/3.667 and
5/6/5 connected components, respectively. Seed 18 had an unreachable session:
1,006 offers were rejected as no-path at lambda=1. This explains part of the average
throughput deficit; retaining this outcome is essential for an unconditional graph
experiment. Formal r-robustness is unknown, and global vertex connectivity is zero.

## Published statements and unresolved conflicts

The paper reports peak 1.45 pairs/s at lambda=1, 40–60% gain, moderate-load fidelity
0.913–0.918, and mean delay about .37 s. The PDF does not specify number of sessions,
per-session versus network-wide lambda, or yield. With one unique pair per offered
request and network-total lambda=1, sustained 1.45 pairs/s cannot follow from that
traffic convention. A finite-window realized rate can differ from its expectation;
our conservation checks use actual arrivals rather than comparing to nominal lambda.
Per-session profiles explicitly change total offered traffic, without target fitting.

Figure 3 visually shows baseline fidelity above QAMR across all plotted loads,
contrary to VII-C's claim that this happens only at negligible load. The .37 s mean
is not clearly linked to Figure 4's multi-second CDF. Queue-only and sojourn quantities
must remain separate. Finite sampled waits do not establish bounded M/M/1 support.

The two published decoherence laws remain alternatives. Actual modeled fidelity
uses conservative reserved-chain aging, while literal Eq. (5)'s serial-residence
proxy is logged separately. Idealized auxiliary purification supply, xi, radius,
sessions, memory reservations and load estimation are consequential assumptions.
No mismatch here is conclusive evidence about the original undisclosed simulator.

## Unexecuted full research suite

`qamr-sim reproduce --preset research` plans **2,520 runs**: 600 arrival-rate,
240 memory, 180 coherence, 240 rmax/ablation, 240 fidelity-model, 120 traffic,
180 dispatch, 360 path-service/load-estimator, 180 lifetime, and 180 failure runs.
It uses all ten rates .1–1 in the main sweep and 20 replications for every scenario.
That full suite has **not been executed**. The reduced suite covers every listed
sensitivity value with three replications, but only three main arrival-rate values.

The 343 initial saved runs consumed about 168 seconds of measured engine/runtime
work, excluding export/plotting overhead. Scaling roughly to the full suite gives
about 20–40 minutes end-to-end on this host; different graph/traffic/hardware choices
and storage can change this materially. Use the run manifests to refine the estimate.
This is an estimate, not a benchmark guarantee. Resume only reuses exact config/code/
paper/environment identities; edits deliberately cause new run identities.

```bash
.venv/bin/qamr-sim reproduce --preset research
# Repeat the representative main sweep:
.venv/bin/qamr-sim sweep --config configs/sweeps/reduced.yaml
# Any reduced sensitivity, e.g.:
.venv/bin/qamr-sim sweep --config configs/sweeps/reduced_coherence.yaml
# Audit every exported run independently:
.venv/bin/python scripts/audit_results.py
```

Figure outputs are generated solely from saved observations. No paper curve points
were digitized or inserted as observations. All raw run data remain in ignored
results/; the local paper is also ignored, and neither is silently redistributed.
