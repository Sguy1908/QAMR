from dataclasses import dataclass


@dataclass
class Candidate:
    path: tuple[int, ...]
    paper_fidelity: float
    fidelity: float
    rounds: int
    delay: float
    mu_path: float
    rho_path: float
    aggregate_ok: bool
    node_ok: bool
    memory_mean_ok: bool
    fidelity_ok: bool
    eligible: bool
    score: float
    probability: float = 0.0
