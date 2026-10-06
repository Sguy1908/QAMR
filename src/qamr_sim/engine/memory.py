from collections import Counter

from qamr_sim.metrics.collector import Integral


class Memory:
    """One slot per elementary-link endpoint, two at an internal repeater."""

    def __init__(self, env, nodes, capacity, warmup):
        self.env, self.capacity = env, capacity
        self.used = {n: 0 for n in nodes}
        self.owners = {}
        self.occupancy = {n: Integral(warmup) for n in nodes}
        self.full = {n: Integral(warmup) for n in nodes}

    @staticmethod
    def demand(path):
        return Counter(n for edge in zip(path, path[1:]) for n in edge)

    def reserve(self, owner, path):
        demand = self.demand(path)
        if any(self.used[n] + v > self.capacity for n, v in demand.items()):
            return False
        if owner in self.owners:
            raise RuntimeError("Duplicate reservation")
        self.owners[owner] = demand
        for n, v in demand.items():
            self.used[n] += v
            self._update(n)
        return True

    def release(self, owner):
        for n, v in self.owners.pop(owner, {}).items():
            self.used[n] -= v
            self._update(n)

    def _update(self, n):
        assert 0 <= self.used[n] <= self.capacity
        self.occupancy[n].set(self.env.now, self.used[n])
        self.full[n].set(self.env.now, int(self.used[n] == self.capacity))
