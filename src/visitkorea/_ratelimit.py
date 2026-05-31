"""Optional client-side request throttling for TourAPI quota protection."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class RateLimiter(Protocol):
    """Anything that can gate one request and report how long to wait first."""

    def acquire(self) -> float:
        """Reserve one request and return the seconds the caller should sleep first."""
        ...


class TokenBucketRateLimiter:
    """A monotonic token-bucket limiter shared by sync and async HTTP clients.

    `acquire()` returns the number of seconds the caller should wait before issuing
    the request. The HTTP layer performs the actual (sync or async) sleep, so the
    same limiter works for both client styles. The clock is injectable for tests.
    """

    def __init__(
        self,
        rate: float,
        per: float = 1.0,
        *,
        burst: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be > 0")
        if per <= 0:
            raise ValueError("per must be > 0")
        self.rate = rate
        self.per = per
        self.capacity = float(burst if burst is not None else rate)
        self._fill_rate = rate / per
        self._clock = clock
        self._tokens = self.capacity
        self._last = clock()

    def acquire(self) -> float:
        now = self._clock()
        elapsed = max(0.0, now - self._last)
        self._tokens = min(self.capacity, self._tokens + elapsed * self._fill_rate)
        self._last = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return 0.0
        wait = (1.0 - self._tokens) / self._fill_rate
        self._tokens = 0.0
        self._last = now + wait
        return wait
