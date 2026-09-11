import math
from collections import deque
from typing import NamedTuple, Optional

from app.config import settings

_STDDEV_EPSILON = 1e-6

_windows: dict[str, deque] = {}


class Baseline(NamedTuple):
    mean: Optional[float]
    stddev: Optional[float]
    z_score: Optional[float]
    count: int


def _window_for(node_id: str) -> deque:
    window = _windows.get(node_id)
    if window is None:
        window = deque(maxlen=settings.baseline_window_size)
        _windows[node_id] = window
    return window


def _stats(window: deque) -> tuple[Optional[float], Optional[float]]:
    n = len(window)
    if n < settings.baseline_min_points:
        return None, None
    mean = sum(window) / n
    variance = sum((v - mean) ** 2 for v in window) / n
    stddev = math.sqrt(variance)
    return mean, stddev


def current_baseline(node_id: str) -> Baseline:
    """Read-only snapshot of the current window's stats (does not mutate)."""
    window = _window_for(node_id)
    mean, stddev = _stats(window)
    return Baseline(mean=mean, stddev=stddev, z_score=None, count=len(window))


def record_and_score(node_id: str, value: float) -> Baseline:
    """Score `value` against the window as it stood *before* this reading,
    then append the reading to the window. Returns None mean/stddev/z_score
    until enough points have accumulated, and None z_score if the sensor is
    too stable (near-zero stddev) to make a z-score meaningful."""
    window = _window_for(node_id)
    mean, stddev = _stats(window)

    z_score = None
    if mean is not None and stddev is not None and stddev > _STDDEV_EPSILON:
        z_score = (value - mean) / stddev

    count = len(window)
    window.append(value)

    return Baseline(mean=mean, stddev=stddev, z_score=z_score, count=count)
