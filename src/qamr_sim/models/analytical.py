"""Equations (7), (19)-(22), (26), never measured delivery rates."""

import math


def throughput_proxy(mus, rhos):
    return sum(mu * (1 - rho) for mu, rho in zip(mus, rhos, strict=True))


def score(delay, fidelity, rho, weights, congestion_penalty=False):
    w1, w2, w3 = weights
    return w1 / (1 + delay) + w2 * fidelity + w3 * ((1 - rho) if congestion_penalty else rho)


def probabilities(scores):
    if not scores:
        return []
    if any(s < 0 or not math.isfinite(s) for s in scores):
        raise ValueError("Scores must be finite and nonnegative")
    total = sum(scores)
    return [s / total for s in scores] if total else [1 / len(scores)] * len(scores)


def aggregate_admission(loads, mus, theta):
    return sum(loads) < theta * sum(mus)


def published_complexity_term(rmax, edges, nodes):
    """Magnitude of expression inside published big-O, not a benchmark."""
    return rmax * (edges + nodes * math.log(nodes))


def redundancy_throughput(lam_total, lengths, p_link, p_swap, p_full):
    if (
        lam_total < 0
        or any(length < 1 for length in lengths)
        or any(not 0 <= p <= 1 for p in (p_link, p_swap, p_full))
    ):
        raise ValueError("Invalid redundancy parameters")
    return (
        lam_total
        * (1 - math.prod(1 - p_link**length * p_swap ** (length - 1) for length in lengths))
        * (1 - p_full)
    )
