from qamr_sim.rng import rng


def offered_traffic(config, sessions):
    """Precomputed per-session Poisson schedules independent of routing consumption."""
    rate = config.arrival_rate / (len(sessions) if config.traffic_convention == "total" else 1)
    arrivals = []
    if not rate:
        return arrivals
    for session in range(len(sessions)):
        random = rng(config.seed, "traffic", session)
        time, index = 0.0, 0
        while True:
            time += float(random.exponential(1 / rate))
            if time >= config.simulation_duration_seconds:
                break
            arrivals.append((time, session, f"{session}:{index}"))
            index += 1
    return sorted(arrivals)
