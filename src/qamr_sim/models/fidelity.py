"""Published laws remain explicitly distinct; path half-floor is assumption A04."""

import math


def decay(f0, exposure, model="paper_exponential"):
    if not 0 <= f0 <= 1 or exposure < 0:
        raise ValueError("Fidelity in [0,1], exposure >= 0")
    floor = 0 if model == "paper_exponential" else 0.5
    if model not in ("paper_exponential", "paper_half_floor"):
        raise ValueError(model)
    return floor + (f0 - floor) * math.exp(-exposure)


def path_fidelity(f0, hops, waits, coherences, ps, model="paper_exponential", swap_factor=True):
    """Eq. (5) literally for exponential; named extension for half-floor."""
    if hops < 1:
        raise ValueError("Paths require at least one link")
    exposure = sum(w / t for w, t in zip(waits, coherences, strict=True))
    base = f0**hops * (ps ** (hops - 1) if swap_factor else 1)
    return decay(base, exposure, model)


def delay_bound(f0, threshold, tau, model="paper_half_floor"):
    """Eq. (25) with explicit no-feasible and unbounded cases."""
    if tau <= 0 or not 0 <= f0 <= 1 or not 0 <= threshold <= 1:
        raise ValueError("Invalid domain")
    floor = 0 if model == "paper_exponential" else 0.5
    if f0 <= floor:
        raise ValueError("Decay-bound inversion requires F0 above asymptotic floor")
    if threshold > f0:
        return None
    if threshold <= floor:
        return math.inf
    return -tau * math.log((threshold - floor) / (f0 - floor))
