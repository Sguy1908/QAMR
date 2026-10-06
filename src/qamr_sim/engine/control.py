from collections import deque


class Control:
    """Interval telemetry plus delivery latency; shared by all policies."""

    def __init__(self, env, config, nodes):
        self.env, self.config, self.nodes = env, config, nodes
        self.published = {n: 0.0 for n in nodes}
        self.history = {n: deque() for n in nodes}
        env.process(self.run())

    def observe(self, n):
        self.history[n].append(self.env.now)

    def publish(self, values):
        yield self.env.timeout(self.config.control_latency_seconds)
        self.published = values

    def run(self):
        c = self.config
        while True:
            yield self.env.timeout(c.telemetry_interval_seconds)
            values = {}
            for n, history in self.history.items():
                while history and history[0] < self.env.now - c.rolling_window_seconds:
                    history.popleft()
                values[n] = len(history) / min(self.env.now, c.rolling_window_seconds)
            self.env.process(self.publish(values))
