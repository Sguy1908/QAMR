"""Eqs. (8)-(18): literal sums, no hidden normalization or exact optimizer."""

from .analytical import throughput_proxy


def selected_metrics(activation, delays, mus, rhos, fidelities):
    if any(x not in (0, 1) for x in activation):
        raise ValueError("Eq. (9)/(18) requires binary activation")
    if len({len(v) for v in (activation, delays, mus, rhos, fidelities)}) != 1:
        raise ValueError("Mismatched path vectors")
    count = sum(activation)
    return dict(
        delay=sum(x * d for x, d in zip(activation, delays)),
        throughput=throughput_proxy([x * m for x, m in zip(activation, mus)], rhos),
        fidelity=sum(x * f for x, f in zip(activation, fidelities)) / count if count else None,
    )


def objective(session_delays, session_fidelities, throughput, weights=(1, 1, 1)):
    if any(w < 0 for w in weights):
        raise ValueError("Objective weights must be nonnegative")
    a, b, c = weights
    return a * sum(session_delays) - b * sum(session_fidelities) - c * throughput


def constraints(loads, mus, numbers, memories, fidelities, threshold, activation, max_paths):
    return dict(
        stability=all(load < mu for load, mu in zip(loads, mus, strict=True)),
        memory=all(q <= m for q, m in zip(numbers, memories, strict=True)),
        fidelity=all(f >= threshold for f in fidelities),
        max_paths=sum(activation) <= max_paths,
        binary=all(x in (0, 1) for x in activation),
    )
