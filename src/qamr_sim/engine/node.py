import simpy

from qamr_sim.metrics.collector import Integral


class Node:
    def __init__(self, env, warmup):
        self.resource = simpy.Resource(env, capacity=1)
        self.queue = Integral(warmup)
        self.busy = Integral(warmup)
        self.system = Integral(warmup)
        self.arrivals = []
        self.completed = 0
        self.waits = []
        self.sojourns = []

    def sample(self, now):
        self.queue.set(now, len(self.resource.queue))
        self.busy.set(now, len(self.resource.users))
        self.system.set(now, len(self.resource.queue) + len(self.resource.users))
