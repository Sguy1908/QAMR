# Scientific contract

Read docs/paper/qamr.pdf before changing scientific semantics. The reference is
Goenka et al., DOI 10.1109/ICICI68867.2026.11565029. Keep the PDF untracked.
This is a paper reconstruction, never an exact reproduction without original
code/data. Do not invent a license for the repository or redistribute the paper.

Every model behavior must be classified as published, an implementation assumption,
or a disabled-by-default extension. Keep docs/paper_traceability.md and
docs/assumptions.md synchronized. Preserve literal equations (1)-(26), including
both fidelity laws, positive utilization scoring, and analytical throughput proxies.
Never conflate queue-only waiting, sojourn, physical qubits, or analytical means.
Never fit hidden parameters or hardcode experimental targets. Export unfavorable
and failed runs. Validate conservation, finite resources, reproducibility, and
statistical queue limits; target agreement is not a test of correctness.

Core engine cannot depend on dashboard, plotting, or filesystem output. Keep
typed/versioned schemas and independent keyed random streams. Log assumptions,
configuration, paper/code hashes, seeds, and runtime. Shared-resource multipath
capacities are not independent. Path counts do not certify formal r-robustness.
Baselines share all non-policy semantics. No microscopic protocol is claimed by
the aggregate service abstraction. Run pytest, ruff, and a real smoke experiment
after meaningful changes. Statistical tests run separately. Keep unexecuted
research experiments explicitly identified.
