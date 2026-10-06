"""Isolated queue experiments: no routing, expiry, memory, or purification."""

import numpy as np
import simpy

from qamr_sim.metrics.collector import Integral
from qamr_sim.rng import rng


def isolated_queue(lam=0.6, mu=1.0, capacity=None, duration=20000.0, warmup=2000.0, seed=0):
    env = simpy.Environment()
    resource = simpy.Resource(env, capacity=1)
    number, queue = Integral(warmup), Integral(warmup)
    traffic, service = rng(seed, "traffic"), rng(seed, "service")
    waits, sojourns = [], []
    admitted = blocked = completed = 0

    def update():
        number.set(env.now, len(resource.users) + len(resource.queue))
        queue.set(env.now, len(resource.queue))

    def job():
        nonlocal completed
        start = env.now
        token = resource.request()
        update()
        yield token
        update()
        wait = env.now - start
        yield env.timeout(float(service.exponential(1 / mu)))
        if env.now >= warmup:
            completed += 1
        if start >= warmup:
            waits.append(wait)
            sojourns.append(env.now - start)
        resource.release(token)
        update()

    def arrivals():
        nonlocal admitted, blocked
        while lam:
            yield env.timeout(float(traffic.exponential(1 / lam)))
            if capacity is not None and len(resource.users) + len(resource.queue) >= capacity:
                blocked += int(env.now >= warmup)
            else:
                admitted += int(env.now >= warmup)
                env.process(job())

    env.process(arrivals())
    env.run(until=duration)
    return dict(
        number=number.mean(duration),
        queue_number=queue.mean(duration),
        queue_wait=float(np.mean(waits)) if waits else None,
        sojourn=float(np.mean(sojourns)) if sojourns else None,
        throughput=completed / (duration - warmup),
        blocking=blocked / (admitted + blocked) if admitted + blocked else None,
        completed=completed,
    )
