"""Only these policy controls change; all physical/event settings remain shared."""

POLICIES = {
    "qamr": "Literal positive-utilization scoring and probabilistic split",
    "single_path": "Fixed shortest unweighted path; same admission and purification",
    "queue_aware_single": "Highest-score eligible candidate, one path per request",
    "no_queue": "Unloaded delay and zero-utilization score; actual admission retained",
    "no_purification": "Purification round cap forced to zero",
    "congestion_penalty": "Use omega3*(1-rho) instead of omega3*rho",
}
