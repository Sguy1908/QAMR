"""Equation (6) as a gain approximation, not a physical two-pair protocol."""

from math import exp

from .fidelity import decay


def gain(fidelity, kappa, rounds):
    if not 0 <= fidelity <= 1 or kappa < 0 or rounds < 0:
        raise ValueError("Invalid purification domain")
    return fidelity + (1 - fidelity) * (1 - exp(-kappa * rounds))


def delayed_round(fidelity, kappa, seconds, exposure_rate, model):
    return gain(decay(fidelity, seconds * exposure_rate, model), kappa, 1)


def plan(fidelity, threshold, cap, kappa, seconds, exposure_rate, model):
    for n in range(cap + 1):
        if fidelity >= threshold:
            return n, fidelity
        if n < cap:
            fidelity = delayed_round(fidelity, kappa, seconds, exposure_rate, model)
    return cap, fidelity
