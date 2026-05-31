from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from visitkorea._http import AsyncTourApiHttp, TourApiHttp, _parse_retry_after, _retry_delay
from visitkorea._ratelimit import TokenBucketRateLimiter
from visitkorea.client import KrTourApiClient
from visitkorea.exceptions import TourApiServerError

from .conftest import FakeResponse, FakeSession, tour_payload


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class AsyncSleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class HeaderResponse:
    def __init__(
        self,
        status_code: int,
        *,
        headers: Mapping[str, str] | None = None,
        payload: Any = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self.headers = dict(headers or {})
        self._payload = payload
        self.text = text or json.dumps(payload)

    def json(self) -> Any:
        return self._payload


class RaisingSession:
    """A session that raises a transport error N times, then returns responses."""

    def __init__(self, errors: int, responses: list[Any]) -> None:
        self.errors = errors
        self.responses = responses
        self.calls = 0

    def get(self, url: str, *, params: Mapping[str, Any], timeout: Any) -> Any:
        self.calls += 1
        if self.errors > 0:
            self.errors -= 1
            raise httpx.ConnectError("boom")
        return self.responses.pop(0)


def _http(session: Any, **kwargs: Any) -> TourApiHttp:
    return TourApiHttp(
        "KEY",
        base_url="http://example.com",
        service_name="KorService2",
        mobile_os="ETC",
        mobile_app="test",
        session=session,
        **kwargs,
    )


def test_retry_recovers_after_transient_status():
    sleeper = SleepRecorder()
    session = FakeSession(
        [FakeResponse({}, status_code=503, text="down"), FakeResponse(tour_payload([]))]
    )
    http = _http(session, max_retries=1, backoff_factor=0.0, sleep=sleeper)

    body = http.get("areaCode2")

    assert body["items"] == {"item": []}
    assert len(session.calls) == 2
    assert sleeper.delays == [0.0]


def test_retry_exhausted_raises_typed_error():
    sleeper = SleepRecorder()
    session = FakeSession(
        [FakeResponse({}, status_code=503, text="d"), FakeResponse({}, status_code=503, text="d")]
    )
    http = _http(session, max_retries=1, backoff_factor=0.0, sleep=sleeper)

    with pytest.raises(TourApiServerError):
        http.get("areaCode2")
    assert len(session.calls) == 2


def test_retry_transport_error_then_success():
    sleeper = SleepRecorder()
    session = RaisingSession(errors=1, responses=[FakeResponse(tour_payload([]))])
    http = _http(session, max_retries=2, backoff_factor=0.0, sleep=sleeper)

    body = http.get("areaCode2")

    assert body["items"] == {"item": []}
    assert session.calls == 2
    assert sleeper.delays == [0.0]


def test_no_retry_by_default_keeps_legacy_behavior():
    session = FakeSession([FakeResponse({}, status_code=503, text="down")])
    http = _http(session)

    with pytest.raises(TourApiServerError):
        http.get("areaCode2")
    assert len(session.calls) == 1


def test_retry_after_header_is_honored():
    assert _parse_retry_after(HeaderResponse(429, headers={"Retry-After": "7"})) == 7.0
    assert _parse_retry_after(HeaderResponse(429, headers={"Retry-After": "bad"})) is None
    assert _parse_retry_after(HeaderResponse(429)) is None

    delay = _retry_delay(0, HeaderResponse(429, headers={"Retry-After": "7"}), 0.5, 20.0)
    assert delay == 7.0
    capped = _retry_delay(0, HeaderResponse(429, headers={"Retry-After": "99"}), 0.5, 20.0)
    assert capped == 20.0
    assert _retry_delay(3, None, 0.0, 20.0) == 0.0


def test_rate_limiter_token_bucket_logic():
    now = [0.0]
    limiter = TokenBucketRateLimiter(rate=1, per=1.0, burst=1, clock=lambda: now[0])

    assert limiter.acquire() == 0.0
    assert limiter.acquire() == pytest.approx(1.0)

    with pytest.raises(ValueError, match="rate"):
        TokenBucketRateLimiter(rate=0)
    with pytest.raises(ValueError, match="per"):
        TokenBucketRateLimiter(rate=1, per=0)


def test_rate_limiter_gates_http_requests():
    sleeper = SleepRecorder()
    limiter = TokenBucketRateLimiter(rate=1, per=1.0, burst=1, clock=lambda: 0.0)
    session = FakeSession([FakeResponse(tour_payload([])), FakeResponse(tour_payload([]))])
    http = _http(session, rate_limiter=limiter, sleep=sleeper)

    http.get("areaCode2")
    http.get("areaCode2")

    assert sleeper.delays == [pytest.approx(1.0)]


def test_http_debug_logging(caplog):
    session = FakeSession([FakeResponse(tour_payload([]))])
    http = _http(session)

    with caplog.at_level(logging.DEBUG, logger="visitkorea.http"):
        http.get("areaCode2")

    assert any("areaCode2" in record.message for record in caplog.records)


def test_client_accepts_httpx_timeout_object():
    session = FakeSession([FakeResponse(tour_payload([]))])
    timeout = httpx.Timeout(5.0, connect=2.0)
    client = KrTourApiClient("KEY", session=session, timeout=timeout)

    client.area_codes()

    assert session.calls[0]["timeout"] is timeout


def test_async_retry_recovers_after_transient_status():
    sleeper = AsyncSleepRecorder()

    class AsyncFakeSession:
        def __init__(self, responses: list[Any]) -> None:
            self.responses = responses
            self.calls: list[dict[str, Any]] = []

        async def get(self, url: str, *, params: Mapping[str, Any], timeout: Any) -> Any:
            self.calls.append({"url": url})
            return self.responses.pop(0)

    session = AsyncFakeSession(
        [FakeResponse({}, status_code=503, text="d"), FakeResponse(tour_payload([]))]
    )
    http = AsyncTourApiHttp(
        "KEY",
        base_url="http://example.com",
        service_name="KorService2",
        mobile_os="ETC",
        mobile_app="test",
        session=session,
        max_retries=1,
        backoff_factor=0.0,
        sleep=sleeper,
    )

    body = asyncio.run(http.get("areaCode2"))

    assert body["items"] == {"item": []}
    assert len(session.calls) == 2
    assert sleeper.delays == [0.0]
