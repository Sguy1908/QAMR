import numpy as np
import pytest

from qamr_sim.engine.queue_validation import isolated_queue
from qamr_sim.models.queueing import mm1, mm1k

pytestmark = pytest.mark.statistical


@pytest.mark.parametrize("capacity,lam", [(None, 0.6), (4, 1.2)])
def test_independent_queue_limit(capacity, lam):
    rows = [isolated_queue(lam=lam, capacity=capacity, seed=i) for i in range(12)]
    reference = mm1(lam, 1) if capacity is None else mm1k(lam, 1, capacity)
    for key in ("number", "sojourn"):
        values = np.array([r[key] for r in rows])
        # Six standard errors protects family-wise stochastic false failures; 2% floor
        # permits finite-horizon/cohort effects. Report normal 95% CIs separately.
        tolerance = max(0.02 * reference[key], 6 * values.std(ddof=1) / np.sqrt(len(rows)))
        assert abs(values.mean() - reference[key]) < tolerance
    if capacity is None:
        assert np.mean([r["queue_wait"] for r in rows]) == pytest.approx(
            reference["queue_wait"], rel=0.05
        )
    else:
        assert np.mean([r["blocking"] for r in rows]) == pytest.approx(
            reference["blocking"], abs=0.01
        )
    for r in rows:
        assert r["number"] == pytest.approx(r["throughput"] * r["sojourn"], rel=0.03)
