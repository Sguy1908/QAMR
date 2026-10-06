# Development and architecture

The engine uses a SimPy environment per run, local state and SHA256-derived NumPy
PCG64 streams. Topology is keyed by topology_seed; traffic by seed/session;
service by seed/request/path/node/hop; policy by request/deferral; heralding by
request/path/link. Hardware lifetime samples are independent of these. Scheduled
failure scenarios are deterministic, with a reserved failures namespace for future
stochastic extensions. No runtime RNG is consumed by tracing or plotting.

Tests: `pytest -q` fast properties; `pytest -q -m statistical` independent isolated
queue trials. Ruff format and check are CI gates. CI does not redistribute the
paper: checksums are null when it is absent, which is explicit in the manifest.
Install a local authorized PDF for paper-identified research runs. Unit tests do
not assert the reported throughput/fidelity targets.

Path discovery uses NetworkX node-splitting + max-flow (`node_disjoint_paths`)
with cutoff min(max_paths,candidate_cap), or bounded shortest-simple paths. Default
flow complexity is implementation-dependent and not Eq. (22)'s shortest-path
bound. Edmonds–Karp's generic bound is O(V E²) on the transformed graph; NetworkX
may choose a backend. K shortest simple paths uses a Yen-style algorithm and can
cost O(K V³). Cache keys include the actual graph, so hashing itself costs O(V+E).
Global connectivity and full pairwise path counts are run-level diagnostics, not
per-request routing. Exact formal r checking enumerates O(3^N) assignments and
is refused for N>10. Eq. (22) is preserved as an analytical function and claim,
not a promised runtime bound of this implementation.

Memory allocation checks a path-length Counter and commits all slots at once.
Each job releases its server before acquiring the next; no multi-server deadlock.
Horizon cleanup steps only urgent events at the boundary, never regular completion
at T; tests cover active jobs, queued jobs, and resource leaks. Configuration
validation rejects invalid domains, unknown fields, and nonpositive retry intervals.

Run identities hash full config (including logging), code/docs/config tree, paper
checksum, versions and Python. Graph generation is deterministic given its seed;
the actual exported graph gets a separate checksum. A complete marker is written
only after artifacts/report succeed. Failed and cancelled runs are retained without
a completion marker. Resume requires exact identity; it never combines old-version
runs into a new sweep. Summary tables enumerate only the current planned run IDs.
No cache decision depends on matching scientific targets.

Runner runtime includes simulation and result formation; figure/export time is not
included. Large logs can consume substantial space. `trace=false` drops full event
logs but retains request, attempt, node, and path-decision data. Cancellation is
cooperative at at most 10 simulated seconds (not a guaranteed wall-clock bound).
Do not share mutable Simulation instances across threads. Dashboard owns one
background worker and a thread-safe cancellation Event per active run.
