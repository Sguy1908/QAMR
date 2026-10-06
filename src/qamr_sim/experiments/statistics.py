import numpy as np
from scipy.stats import t


def interval(values, confidence=0.95):
    """Student-t CI across independent run observations, not individual events."""
    values = np.array([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    n = len(values)
    mean = float(values.mean()) if n else None
    half = (
        float(t.ppf((1 + confidence) / 2, n - 1) * values.std(ddof=1) / np.sqrt(n))
        if n > 1
        else None
    )
    return dict(
        n=n,
        mean=mean,
        low=mean - half if half is not None else None,
        high=mean + half if half is not None else None,
    )


def paired_interval(left, right):
    return interval(
        [a - b for a, b in zip(left, right, strict=True) if a is not None and b is not None]
    )
