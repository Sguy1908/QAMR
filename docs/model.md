# Event and analytical model

## Published mathematical layer

`models/` preserves equations (1)–(26). M/M/1 provides L (in-system jobs),
W (node sojourn), Wq (queue-only delay), and rho. Unstable formulas return infinity;
JSON exports encode nonfinite values as null, while Parquet retains infinities for
analysis. Empty means and ratios are null, not fabricated zero. Objective values
have mixed units until a researcher specifies dimensional weights.

## Event layer

A parent request is offered -> pending -> active -> completed/failed/expired;
pending may defer a bounded number of times or be rejected. At the horizon,
nonterminal parents are unfinished. Deferral/admission are intermediate counters,
not terminal statuses. Replicated child attempts have their own parent ID and
active/completed/duplicate/failed/expired/unfinished outcomes. First qualifying
delivery wins; duplicates consume resources but cannot inflate throughput.

At admission, reserve all elementary-link endpoint slots atomically. A path of
h links needs 2h total slots. Internal repeaters hold two; source/destination one.
Classical requests do not occupy qubits before reservation. Each hop queues at
its origin's FCFS SimPy Resource, receives independent Exp(mu) service, and releases
that server. Mu is Eq. (2), already a rate of successful service; no extra swapping
Bernoulli is applied. Link heralding checks are a separate assumed abstraction
(p_link=1 default). Failure interrupts propagate to held resources; no partial
reservation waits or circular acquisition. Repeated cleanup is idempotent.

Initial path fidelity is F0^h ps^(h-1) by default, explicitly the paper proxy.
During the entire held interval its decay exposure is elapsed * sum_path(1/tau_i).
This conservative chain-aging assumption differs from the paper's serial
sum(W_i/tau_i); both admission estimates are saved separately. Swaps are successful
aggregate forwarding jobs, not simulated quantum circuits or concrete Bell-state
measurements. Optional physical-operation mode is not implemented or claimed.

Paid purification follows forwarding. While fidelity is below threshold and rounds
remain, wait tau_p, decay held memory, and apply one Eq. (6) gain. All policies share
this sequence, including the single-path baseline. Per-round apparatus capacity
and sacrificial-pair generation are unspecified and unmodeled (A10). There is no
claim of elementary-pair/yield conservation for an invented microscopic protocol.
The hard resource invariant covers modeled endpoint slots. Admission uses this
same finite-round delayed-gain prediction; observed delay can still cause drops.

An expiration watcher inverts the maximum remaining zero-time gain only to bound
salvageability; it grants no output fidelity. Deadline also bounds each request.
An interrupt cancels queued server tokens or releases active tokens and every
endpoint slot. Horizon uses [0,T), tags work in flight, and interrupts children
without counting deliveries at T. Cancellation does the same at the next checkpoint.
Failure recovery restores graph state but never resumes an interrupted attempt.

## Routing, information and load

Algorithm 1 is interpreted as a traffic split by default: score eligible candidates,
normalize over that set only, draw one path per request. Scores all zero means
uniform selection. Post-purification fidelity and both aggregate/per-node constraints
are checked before selection. Hard qubit capacity is checked separately.
`steady_split` estimates configured demand on each path using previous probabilities;
it is a prospective heuristic, not a fitted arrival estimator or fixed-point solver.
`rolling` uses actual forwarding-entry counts / elapsed window seconds from control
telemetry, never a queue-length substitution for lambda. `literal_full` is a labeled
alternative. Topology changes invalidate path cache keys. No-path requests reject.

## Architecture

`config/types/rng` define interfaces. `models` is purely analytical; `topology`
defines graphs and candidate paths; `routing` produces evaluations/choices;
`engine` schedules work and owns resources; `metrics` integrates state over time.
`experiments` runs independent replications and builds provenance; `io` serializes
versioned tables; `plotting` reads saved data. Dashboard uses the runner and can
load results offline. Engine imports no filesystem, UI or plotting code.
