"""HTTP helpers and TourAPI envelope/error mapping."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, NoReturn, Protocol, cast
from xml.etree import ElementTree

import httpx

from ._auth import normalize_service_key
from ._convert import without_none
from ._ratelimit import RateLimiter
from .exceptions import (
    TourApiAuthError,
    TourApiParseError,
    TourApiRateLimitError,
    TourApiRequestError,
    TourApiServerError,
)

logger = logging.getLogger("visitkorea.http")

TimeoutValue = float | httpx.Timeout
SyncSleep = Callable[[float], None]
AsyncSleep = Callable[[float], Awaitable[None]]


class ResponseLike(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class SessionLike(Protocol):
    def get(
        self, url: str, *, params: Mapping[str, Any], timeout: TimeoutValue
    ) -> ResponseLike: ...


class AsyncSessionLike(Protocol):
    async def get(
        self, url: str, *, params: Mapping[str, Any], timeout: TimeoutValue
    ) -> ResponseLike: ...


TRANSIENT_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
DEFAULT_MAX_RETRIES = 0
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_MAX_BACKOFF = 20.0
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; visitkorea/0.1; "
    "+https://github.com/digitie/python-visitkorea-api)"
)


def build_session(retries: int = 3) -> httpx.Client:
    """Build an httpx sync client with conservative connection retries."""

    transport = httpx.HTTPTransport(retries=max(0, retries))
    return httpx.Client(
        headers={"User-Agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


def build_async_session(retries: int = 3) -> httpx.AsyncClient:
    """Build an httpx async client with conservative connection retries."""

    transport = httpx.AsyncHTTPTransport(retries=max(0, retries))
    return httpx.AsyncClient(
        headers={"User-Agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


class TourApiHttp:
    """Low-level JSON client for the data.go.kr TourAPI envelope."""

    def __init__(
        self,
        service_key: str,
        *,
        base_url: str,
        service_name: str,
        mobile_os: str,
        mobile_app: str,
        session: SessionLike | None = None,
        timeout: TimeoutValue = 10.0,
        retries: int = 3,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        retry_statuses: frozenset[int] = TRANSIENT_STATUSES,
        rate_limiter: RateLimiter | None = None,
        sleep: SyncSleep = time.sleep,
    ) -> None:
        normalized_key = normalize_service_key(service_key)
        if not normalized_key:
            raise TourApiAuthError("service_key is required", failure_kind="auth")
        self.service_key = normalized_key
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name.strip("/")
        self.mobile_os = mobile_os
        self.mobile_app = mobile_app
        self.session = cast("SessionLike", session or build_session(retries))
        self._owns_session = session is None
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.retry_statuses = retry_statuses
        self.rate_limiter = rate_limiter
        self._sleep = sleep

    def get(self, endpoint: str, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        endpoint_path = endpoint.strip("/")
        url = f"{self.base_url}/{self.service_name}/{endpoint_path}"
        request_params = without_none(
            tourapi_request_params(
                service_key=self.service_key,
                mobile_os=self.mobile_os,
                mobile_app=self.mobile_app,
                params=params,
            )
        )

        attempt = 0
        while True:
            if self.rate_limiter is not None:
                wait = self.rate_limiter.acquire()
                if wait > 0:
                    self._sleep(wait)
            try:
                response = self.session.get(url, params=request_params, timeout=self.timeout)
            except httpx.HTTPError as exc:
                if attempt < self.max_retries and isinstance(exc, httpx.TransportError):
                    logger.debug(
                        "visitkorea retrying %s/%s after transport error (attempt %s)",
                        self.service_name,
                        endpoint_path,
                        attempt + 1,
                    )
                    self._sleep(_retry_delay(attempt, None, self.backoff_factor, self.max_backoff))
                    attempt += 1
                    continue
                _raise_for_transport_error(
                    exc,
                    endpoint=endpoint_path,
                    service_name=self.service_name,
                    service_key=self.service_key,
                )
            if response.status_code in self.retry_statuses and attempt < self.max_retries:
                logger.debug(
                    "visitkorea retrying %s/%s after HTTP %s (attempt %s)",
                    self.service_name,
                    endpoint_path,
                    response.status_code,
                    attempt + 1,
                )
                self._sleep(
                    _retry_delay(attempt, response, self.backoff_factor, self.max_backoff)
                )
                attempt += 1
                continue
            logger.debug(
                "visitkorea %s/%s -> HTTP %s",
                self.service_name,
                endpoint_path,
                response.status_code,
            )
            return _decode_response(
                response,
                endpoint=endpoint_path,
                service_name=self.service_name,
                service_key=self.service_key,
            )

    def close(self) -> None:
        """Close an owned httpx sync client."""

        if self._owns_session and hasattr(self.session, "close"):
            self.session.close()


class AsyncTourApiHttp:
    """Low-level async JSON client for the data.go.kr TourAPI envelope."""

    def __init__(
        self,
        service_key: str,
        *,
        base_url: str,
        service_name: str,
        mobile_os: str,
        mobile_app: str,
        session: AsyncSessionLike | None = None,
        timeout: TimeoutValue = 10.0,
        retries: int = 3,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        retry_statuses: frozenset[int] = TRANSIENT_STATUSES,
        rate_limiter: RateLimiter | None = None,
        sleep: AsyncSleep = asyncio.sleep,
    ) -> None:
        normalized_key = normalize_service_key(service_key)
        if not normalized_key:
            raise TourApiAuthError("service_key is required", failure_kind="auth")
        self.service_key = normalized_key
        self.base_url = base_url.rstrip("/")
        self.service_name = service_name.strip("/")
        self.mobile_os = mobile_os
        self.mobile_app = mobile_app
        self.session = cast("AsyncSessionLike", session or build_async_session(retries))
        self._owns_session = session is None
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.retry_statuses = retry_statuses
        self.rate_limiter = rate_limiter
        self._sleep = sleep

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        endpoint_path = endpoint.strip("/")
        url = f"{self.base_url}/{self.service_name}/{endpoint_path}"
        request_params = without_none(
            tourapi_request_params(
                service_key=self.service_key,
                mobile_os=self.mobile_os,
                mobile_app=self.mobile_app,
                params=params,
            )
        )

        attempt = 0
        while True:
            if self.rate_limiter is not None:
                wait = self.rate_limiter.acquire()
                if wait > 0:
                    await self._sleep(wait)
            try:
                response = await self.session.get(url, params=request_params, timeout=self.timeout)
            except httpx.HTTPError as exc:
                if attempt < self.max_retries and isinstance(exc, httpx.TransportError):
                    logger.debug(
                        "visitkorea retrying %s/%s after transport error (attempt %s)",
                        self.service_name,
                        endpoint_path,
                        attempt + 1,
                    )
                    await self._sleep(
                        _retry_delay(attempt, None, self.backoff_factor, self.max_backoff)
                    )
                    attempt += 1
                    continue
                _raise_for_transport_error(
                    exc,
                    endpoint=endpoint_path,
                    service_name=self.service_name,
                    service_key=self.service_key,
                )
            if response.status_code in self.retry_statuses and attempt < self.max_retries:
                logger.debug(
                    "visitkorea retrying %s/%s after HTTP %s (attempt %s)",
                    self.service_name,
                    endpoint_path,
                    response.status_code,
                    attempt + 1,
                )
                await self._sleep(
                    _retry_delay(attempt, response, self.backoff_factor, self.max_backoff)
                )
                attempt += 1
                continue
            logger.debug(
                "visitkorea %s/%s -> HTTP %s",
                self.service_name,
                endpoint_path,
                response.status_code,
            )
            return _decode_response(
                response,
                endpoint=endpoint_path,
                service_name=self.service_name,
                service_key=self.service_key,
            )

    async def aclose(self) -> None:
        """Close an owned httpx async client."""

        if self._owns_session and hasattr(self.session, "aclose"):
            await self.session.aclose()


def tourapi_request_params(
    *,
    service_key: str,
    mobile_os: str,
    mobile_app: str,
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the full request params sent to TourAPI."""

    request_params: dict[str, Any] = {
        "serviceKey": normalize_service_key(service_key) or service_key,
        "MobileOS": mobile_os,
        "MobileApp": mobile_app,
        "_type": "json",
    }
    if params:
        request_params.update(dict(params))
    for key, value in tuple(request_params.items()):
        if _is_service_key_param(key):
            request_params[key] = normalize_service_key(value)
    return request_params


def public_request_params(
    *,
    mobile_os: str,
    mobile_app: str,
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return request params safe to expose in response provenance."""

    request_params = tourapi_request_params(
        service_key="",
        mobile_os=mobile_os,
        mobile_app=mobile_app,
        params=params,
    )
    return {
        key: value
        for key, value in without_none(request_params).items()
        if not _is_service_key_param(key)
    }


def _is_service_key_param(key: object) -> bool:
    return str(key).replace("_", "").lower() == "servicekey"


def _decode_response(
    response: ResponseLike,
    *,
    endpoint: str,
    service_name: str,
    service_key: str,
) -> Mapping[str, Any]:
    _raise_for_status(
        response,
        endpoint=endpoint,
        service_name=service_name,
        service_key=service_key,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        _raise_for_xml_error(
            response.text,
            endpoint=endpoint,
            service_name=service_name,
            service_key=service_key,
        )
        message = _redact_secret(str(exc), service_key)
        raise TourApiParseError(
            f"TourAPI response was not valid JSON: {message}",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        ) from exc
    return _extract_body(payload, endpoint=endpoint, service_name=service_name)


def _raise_for_transport_error(
    exc: httpx.HTTPError,
    *,
    endpoint: str,
    service_name: str,
    service_key: str,
) -> NoReturn:
    message = _redact_secret(str(exc), service_key)
    raise TourApiServerError(
        f"TourAPI HTTP request failed: {message}",
        endpoint=endpoint,
        service_name=service_name,
        failure_kind="server",
    ) from exc


def _raise_for_status(
    response: ResponseLike,
    *,
    endpoint: str,
    service_name: str,
    service_key: str,
) -> None:
    status = response.status_code
    text = _redact_secret(response.text, service_key)[:300]
    if status in {401, 403}:
        raise TourApiAuthError(
            f"HTTP {status}: {text}",
            status_code=status,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="auth",
        )
    if status == 429:
        raise TourApiRateLimitError(
            f"HTTP {status}: {text}",
            status_code=status,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="rate_limit",
        )
    if 400 <= status < 500:
        raise TourApiRequestError(
            f"HTTP {status}: {text}",
            status_code=status,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="request",
        )
    if 500 <= status < 600:
        raise TourApiServerError(
            f"HTTP {status}: {text}",
            status_code=status,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="server",
        )


def _extract_body(payload: Any, *, endpoint: str, service_name: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TourApiParseError(
            "TourAPI JSON root was not an object",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        )

    if "OpenAPI_ServiceResponse" in payload:
        _raise_for_data_error(
            payload["OpenAPI_ServiceResponse"],
            endpoint=endpoint,
            service_name=service_name,
        )

    try:
        response = payload["response"]
        header = response["header"]
    except (KeyError, TypeError) as exc:
        raise TourApiParseError(
            "TourAPI response did not contain response.header",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        ) from exc

    if not isinstance(response, Mapping) or not isinstance(header, Mapping):
        raise TourApiParseError(
            "TourAPI response/header was not an object",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        )

    code = str(header.get("resultCode", "")).strip()
    message = str(header.get("resultMsg", "")).strip()
    body = response.get("body", {})
    if code in {"00", "0000", "0", "NORMAL_CODE", ""}:
        if not isinstance(body, Mapping):
            raise TourApiParseError(
                "TourAPI response.body was not an object",
                endpoint=endpoint,
                service_name=service_name,
                failure_kind="parse",
            )
        return body
    if code == "03":
        return body if isinstance(body, Mapping) else {}
    _raise_for_result_code(code, message, endpoint=endpoint, service_name=service_name)
    raise AssertionError("unreachable")


def _raise_for_xml_error(
    text: str,
    *,
    endpoint: str,
    service_name: str,
    service_key: str,
) -> None:
    text = text.strip()
    if not text.startswith("<"):
        return
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return

    values: dict[str, str] = {}
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if element.text and element.text.strip():
            values[tag] = element.text.strip()

    code = values.get("returnReasonCode", "")
    message = (
        values.get("returnAuthMsg")
        or values.get("errMsg")
        or values.get("resultMsg")
        or "TourAPI XML error response"
    )
    _raise_for_result_code(
        code,
        message,
        endpoint=endpoint,
        service_name=service_name,
        service_key=service_key,
    )


def _raise_for_data_error(data: Any, *, endpoint: str, service_name: str) -> None:
    if not isinstance(data, Mapping):
        raise TourApiParseError(
            "OpenAPI_ServiceResponse was not an object",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        )
    header = data.get("cmmMsgHeader", data)
    if not isinstance(header, Mapping):
        raise TourApiParseError(
            "OpenAPI_ServiceResponse header was not an object",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        )
    code = str(header.get("returnReasonCode", "")).strip()
    message = str(
        header.get("returnAuthMsg")
        or header.get("errMsg")
        or header.get("resultMsg")
        or "TourAPI service error"
    )
    _raise_for_result_code(code, message, endpoint=endpoint, service_name=service_name)


def _raise_for_result_code(
    code: str,
    message: str,
    *,
    endpoint: str,
    service_name: str,
    service_key: str | None = None,
) -> None:
    text = f"TourAPI returned {code}: {message}" if code else message
    text = _redact_secret(text, service_key)
    upper = text.upper()
    if code in {"20", "30", "31", "32"} or "SERVICE_KEY" in upper or "AUTH" in upper:
        raise TourApiAuthError(
            text,
            result_code=code or None,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="auth",
        )
    if code in {"22"} or "LIMIT" in upper or "QUOTA" in upper or "TRAFFIC" in upper:
        raise TourApiRateLimitError(
            text,
            result_code=code or None,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="rate_limit",
        )
    if code in {"04", "99"} or code.startswith("5"):
        raise TourApiServerError(
            text,
            result_code=code or None,
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="server",
        )
    raise TourApiRequestError(
        text,
        result_code=code or None,
        endpoint=endpoint,
        service_name=service_name,
        failure_kind="request",
    )


def _retry_delay(
    attempt: int,
    response: ResponseLike | None,
    backoff_factor: float,
    max_backoff: float,
) -> float:
    """Return the delay before the next retry, honoring Retry-After when present."""

    if response is not None:
        retry_after = _parse_retry_after(response)
        if retry_after is not None:
            return min(retry_after, max_backoff)
    base = backoff_factor * (2.0**attempt)
    if base <= 0:
        return 0.0
    return min(base + base * 0.1 * random.random(), max_backoff)


def _parse_retry_after(response: ResponseLike) -> float | None:
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    value = getter("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _redact_secret(text: str, secret: str | None) -> str:
    if not secret:
        return text
    return text.replace(secret, "[redacted]")
