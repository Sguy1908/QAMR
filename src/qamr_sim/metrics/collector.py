"""Piecewise-constant event integrals, clipped to measurement window."""


class Integral:
    def __init__(self, warmup):
        self.warmup = warmup
        self.last = 0.0
        self.value = 0
        self.area = 0.0
        self.maximum = 0

    def set(self, now, value):
        self.area += self.value * max(0.0, now - max(self.last, self.warmup))
        self.last = now
        self.value = value
        self.maximum = max(self.maximum, value)

    def mean(self, now):
        self.set(now, self.value)
        return self.area / (now - self.warmup) if now > self.warmup else None
