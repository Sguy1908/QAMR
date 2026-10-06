import pytest

from qamr_sim.metrics.collector import Integral
from qamr_sim.models.analytical import published_complexity_term


def test_event_integral_warmup_and_simultaneous_changes():
    value = Integral(warmup=5)
    value.set(0, 10)
    value.set(4, 2)
    value.set(7, 4)
    value.set(7, 6)
    # [5,7):2, [7,10):6, not an unweighted mean of event samples.
    assert value.mean(10) == pytest.approx(22 / 5)
    assert value.mean(10) == pytest.approx(22 / 5)
    assert value.maximum == 10


def test_complexity_claim_is_separate_analytical_expression():
    assert published_complexity_term(2, 60, 60) == 2 * published_complexity_term(1, 60, 60)
