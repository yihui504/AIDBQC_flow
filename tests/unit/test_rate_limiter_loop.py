import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.rate_limiter import RateLimiter


class _FakeConfigLoader:
    def load(self):
        return True

    def get(self, key, default=None):
        mapping = {
            "rate_limiting.enabled": True,
            "rate_limiting.max_requests_per_minute": 1,
            "rate_limiting.wait_on_limit": True,
        }
        return mapping.get(key, default)


def test_acquire_wait_uses_loop_retry_without_recursion(monkeypatch):
    monkeypatch.setattr("src.rate_limiter.ConfigLoader", _FakeConfigLoader)
    limiter = RateLimiter()
    limiter.requests = deque([100.0])  # already full

    now_values = iter([100.0, 161.0])  # first hit limit, second pass after wait window
    monkeypatch.setattr("src.rate_limiter.time.time", lambda: next(now_values))

    slept = []
    monkeypatch.setattr("src.rate_limiter.time.sleep", lambda seconds: slept.append(seconds))

    assert limiter.acquire(wait=True) is True
    assert len(slept) == 1
    assert slept[0] == 60.0
    assert len(limiter.requests) == 1


def test_acquire_no_wait_returns_false_when_limited(monkeypatch):
    monkeypatch.setattr("src.rate_limiter.ConfigLoader", _FakeConfigLoader)
    limiter = RateLimiter()
    limiter.requests = deque([100.0])  # already full
    monkeypatch.setattr("src.rate_limiter.time.time", lambda: 100.0)

    assert limiter.acquire(wait=False) is False
