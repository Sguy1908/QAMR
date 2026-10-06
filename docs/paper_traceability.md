# Paper-to-implementation traceability

Source: Goenka et al., *Queue-Aware Multi-Path Entanglement Distribution in r-Robust
Hybrid Quantum-Classical Networks under NISQ Constraints*, IEEE ICICI 2026,
DOI 10.1109/ICICI68867.2026.11565029. Pages below are local PDF pages 1–6.
`models.*` references mean modules under `src/qamr_sim/models/`. P = published;
A = implementation assumption; E = optional extension. Analytical functions are
not evidence that the corresponding microscopic event process was specified.

## Equations

| Equation / PDF location | Implementation symbol | Configuration / assumptions | Verification / outputs | Kind |
|---|---|---|---|---|
| (1), p2 III-A | `queueing.aggregate_load`; `Router.loads` | arrival_rate, sessions, traffic_convention, load_estimator; A15–16 | test_queue_meanings_and_units; configured total, path constraints | P function, A dynamic split |
| (2), p2 III-B | `queueing.service_rate`, `hardware_efficiency`; `Config.mu` | ps, xi, tau_p, tau_s; A02/A11 | test_queue_meanings_and_units; node_metrics.mu | P rate, A efficiency |
| (3), p2 III-B | `queueing.mm1` | lambda/mu, A01 | test_queue_meanings_and_units; test_independent_queue_limit; analytical vs observed node metrics | P analytical, real queue dynamics |
| (4), p2 III-C | `fidelity.decay(...paper_exponential)` | initial_fidelity, coherence; A03/A09 | test_fidelity_domains_and_inversion; attempt and delivery fidelity | P law, A path aging |
| (5), p2 III-C | `fidelity.path_fidelity` | proxy_swap_factor, routing_fidelity_model; A04/05/09 | test_fidelity_proxy_and_purification; path_metrics.paper_fidelity | P exponential proxy, named half-floor A |
| (6), p2 III-C | `purification.gain`, `delayed_round`, `plan`; `Simulation.attempt` | kappa, tau_p, cap; A10–11 | test_fidelity_proxy_and_purification; real purification start/end events | P gain, A resources/time placement |
| (7), p2 III-D | `analytical.throughput_proxy` | path_service, A13 | test_literal_equations_and_constraints; path mus/rhos | P analytical only, not delivery rate |
| (8), p2 III-E | `objective.constraints`, `Router.evaluate`, `Memory.reserve` | M, F_th; A07/A09 | model constraints tests + atomic memory test | P mean constraint, A hard slots |
| (9), p3 IV-A | `objective.selected_metrics` activation vector | binary selections | test_literal_equations_and_constraints | P evaluator; heuristic selections |
| (10), p3 IV-B | `objective.selected_metrics['delay']` | unnormalized sum, Wij maps to origin node | test_literal_equations_and_constraints; candidate delay | P analytical sum |
| (11), p3 IV-B | `objective.selected_metrics['throughput']` summed by caller over sessions | A13, no independent-capacity claim | model tests; delivered throughput separate | P analytical only |
| (12), p3 IV-B | `objective.selected_metrics['fidelity']` over supplied selected-path vector | undefined for no selection | model tests; delivered means separate | P selected-path mean |
| (13), p3 IV-C | `objective.objective` | explicit weights, no normalization; A26 | model tests | P evaluation, no exact optimization |
| (14), p3 IV-D | `objective.constraints['stability']`; candidate.node_ok | admission interpretation | aggregate-vs-node counterexample test | P |
| (15), p3 IV-D | `objective.constraints['memory']`; candidate.memory_mean_ok | analytical M versus hard qubits separate | model tests, shared-bottleneck test | P + A slots |
| (16), p3 IV-D | `objective.constraints['fidelity']`; candidate.fidelity_ok | finite paid purification | delayed-gain test; fidelity drop accounting | P constraint |
| (17), p3 IV-D | `objective.constraints['max_paths']`; Router.paths cap | max_paths | path tests, policy tests | P |
| (18), p3 IV-D | `objective.constraints['binary']`, selected_metrics validation | binary integer activation | model tests | P |
| (19), p3 V-B | `analytical.score`; Router.evaluate | literal +rho; score_weights; A06 | positive-rho test; candidate.score | P, congestion ablation E |
| (20), p3 V-B | `analytical.probabilities`; Router.choose | eligible set, uniform zero-score fallback; A14 | normalization test, replication test; probability column | P ratio, A fallback/dispatch |
| (21), p3 V-C/p4 | `analytical.aggregate_admission` | theta=.9, A07 | aggregate-vs-node counterexample; aggregate_ok column | P |
| (22), p4 V-E | `analytical.published_complexity_term` | actual algorithm details in development.md | mathematical operation-count helper; separate runtime manifest | P analytical claim only |
| (23), p4 VI | `queueing.mm1` stability and sojourn | isolated validation config | statistical queue tests / validate-queue JSON | P stationary relation, no hard bounded delay |
| (24), p4 VI | `fidelity.decay(...paper_half_floor)` | explicit selected model | inversion/limits tests | P node law |
| (25), p4 VI | `fidelity.delay_bound` | half-floor default; domains checked | inversion/limits and scaling tests | P analytical bound |
| (26), p4 VI | `analytical.redundancy_throughput`; report illustration | p_link, independent redundant paths, P_full semantics; A23 | redundancy limits test; report value distinct from measured throughput | P analytical independence approximation |

## Algorithm 1 and Figure 1 (p4)

| Step(s) | Implementation / actual behavior | Verification / output |
|---|---|---|
| Algorithm 1 inputs 1; initialize 2 | Config, Simulation.sessions, Router | validated typed inputs; config tests |
| Compute paths 3 | topology.paths.candidates, Router.paths | real flow-disjoint or bounded shortest paths; graph tests |
| Loop 4, collect 5 | Router.evaluate/loads; Control | configured steady fractions or actual rolling-entry telemetry; candidate rows |
| Fidelity 6 | path_fidelity for literal proxy plus conservative endpoint-aging estimate | both logged; fidelity tests |
| Purification branch 7–8 | plan; actual delayed_round in Simulation.attempt | bounded paid rounds, feasibility recheck; purification test |
| Score 9, end loop 10 | analytical.score | literal +rho test |
| Probabilities 11 | probabilities over eligible candidates | zero-score/domain tests |
| Repeated draws 12–13 | choose: split default; replicate/round_robin named alternatives | policy/unique-delivery tests; A14 |
| Admission 14–16 | aggregate + per-node + mean memory + final fidelity, then atomic slots | separate booleans; hard-memory test |
| End loop 17 | finite candidate bound | max_paths/candidate_cap |
| Dispatch 18 | Simulation.request spawns child processes | real queue/service/memory events; end-to-end tests |
| Figure 1 Start / incoming | Poisson offered_traffic; Simulation.traffic | schedule reproducibility; offer event |
| Discover / collect / compute | above paths, loads, two fidelity estimates | path_metrics |
| Fidelity yes/no / purification / updated-fidelity / discard | bounded plan and actual final fidelity threshold | rejected/expired reasons |
| Score / aggregate admission / add path | above scoring and guardrails | routing decision rows |
| More paths / feedback | bounded candidate set, remembered probabilities; per-request reevaluation | A14/16; no unbounded zero-time loop |
| Dispatch / request routed / end | real child processes and terminal event accounting | requests/attempts tables, conservation tests |

## Table II (p5)

| Published parameter | Configuration field and default | Validation / experiment |
|---|---|---|
| N=60 | nodes=60 | topology counts; paper/reduced configs |
| mean degree=4 | target_mean_degree=4 | achieved degree recorded; finite-domain radius A19 |
| Mi={8,12,16,24} | memory_capacity=8 default scenario | memory sweep and slot invariant |
| tau_c=50 ±10 s | coherence_central_seconds=50, coherence_spread_seconds=10 | lifetime/coherence sensitivity; A18 distribution |
| tau_s=.05 s | swap_time_seconds=.05 | mu and queue tests |
| tau_p=.02 s | purification_time_seconds=.02 | paid rounds and rate test |
| ps=.95 | swap_success_probability=.95 | rate and proxy tests |
| F0=.98 | initial_fidelity=.98 | decay tests |
| kappa=.6 | purification_efficiency=.6 | gain tests |
| Fth=.85 | fidelity_threshold=.85 | bound/admission/delivery tests |
| lambda=.1–1 req/s | arrival_rate per sweep .1,.2,...,1 | grid is implementation choice, scope A15 |
| Tsim=2000 s | simulation_duration_seconds=2000 | research + reduced full-duration runs |
| rmax=2 | max_paths=2 | robustness/ablation suite |

No other defaults are labeled Table II values. `configs/paper.yaml` and every
resolved run retain this distinction. Hard-slot limits and analytical mean L<=M
are different tests despite sharing the scenario capacity number.

## Figures and Section VII

| Source | Runnable reconstruction | Output and limits |
|---|---|---|
| VII-A p5 setup | paper config + seeded unconditional RGG + sweep runner | graph/config/manifest; first-draw disconnections retained |
| Figure 2 / VII-B p5 | arrival_rate.yaml, policies qamr/single_path/queue_aware_single | independent replication throughput, t CI, paired differences; 1.45 and 40–60% text targets only |
| Figure 3 / VII-C p5 | same sweep | delivered fidelity means/n, undefined no-delivery metrics; text/plot discrepancy A30 |
| Figure 4 / VII-D p5 | each saved run waiting_cdf; explicit queue vs path-sojourn | CDF cohort/censoring disclosed; no assertion that sampled max proves bounded support |
| VII-E p5–6 | coherence.yaml centers 30/50/70; lifetime.yaml distributions | physical-delay effects, no fitted parameters |
| VII-F p6 discussion | reports + all sensitivity/ablation suites | discrepancies are valid outcomes, internal consistency not independent validation |
| Additional requested memory | memory.yaml 8/12/16/24 | time-integrated queues, hard qubits, blocking |
| Interpretation sensitivities | fidelity_models/traffic/dispatch/path_service/lifetime.yaml | all identities and assumptions retained |
| rmax and ablations | robustness.yaml | rmax 1/2; no_queue, no_purification, congestion_penalty |
| Failure extension | failures.yaml | scheduled node/edge loss, recovery, pairwise connectivity; no formal r certificate |
| Analytical/event validation | validation_mm1/mm1k + validate-queue, per-run report | standalone queue stationary checks; Eq. (26) applicability explicitly limited |

Unsupported claims: exact reproduction, globally optimal routing, universal
bounded M/M/1 delay, automatic r-robust certification, microscopic purification
resource accounting, and independent empirical validation from this simulator.
