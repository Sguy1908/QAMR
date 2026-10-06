"""Equations (1)-(3), (23) and independent finite-buffer reference formulas."""

import math


def aggregate_load(rates, fractions):
    return sum(rate * fraction for rate, fraction in zip(rates, fractions, strict=True))


def hardware_efficiency(pg, ng, pm, nm):
    return pg**ng * pm**nm


def service_rate(ps, xi, tau_p, tau_s):
    return ps * xi / (tau_p + tau_s)


def mm1(lam, mu):
    if lam < 0 or mu <= 0:
        raise ValueError("Require lambda >= 0 and mu > 0")
    rho = lam / mu
    if rho >= 1:
        return dict(rho=rho, number=math.inf, sojourn=math.inf, queue_wait=math.inf)
    return dict(
        rho=rho, number=rho / (1 - rho), sojourn=1 / (mu - lam), queue_wait=rho / (mu - lam)
    )


def mm1k(lam, mu, capacity):
    """K includes the job in service; this is NOT finite quantum memory."""
    if lam < 0 or mu <= 0 or capacity < 1:
        raise ValueError("Invalid finite queue parameters")
    rho = lam / mu
    if rho == 0:
        probs = [1.0] + [0.0] * capacity
    else:
        logs = [i * math.log(rho) for i in range(capacity + 1)]
        weights = [math.exp(v - max(logs)) for v in logs]
        probs = [w / sum(weights) for w in weights]
    number = sum(i * p for i, p in enumerate(probs))
    throughput = lam * (1 - probs[-1])
    return dict(
        blocking=probs[-1],
        number=number,
        throughput=throughput,
        sojourn=number / throughput if throughput else None,
    )
