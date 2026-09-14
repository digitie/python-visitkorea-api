"""HTTP helpers and TourAPI envelope/error mapping."""

from __future__ import annotations

import asyncio
import inspect
import logging
import math
import random
import re
from collections.abc import Awaitable, Callable, Mapping
from contextvars import ContextVar
from typing import Any, NoReturn, Protocol, cast
from xml.etree import ElementTree

import httpx

from ._auth import normalize_service_key
from ._convert import without_none
from ._httpx import send_after_token
from ._ratelimit import AsyncTokenBucket
from ._redact import credential_values, redact_exception, redact_secret
from .exceptions import (
    TourApiAuthError,
    TourApiError,
    TourApiParseError,
    TourApiRateLimitError,
    TourApiRequestError,
    TourApiServerError,
)

logger = logging.getLogger("visitkorea.http")
_request_secrets: ContextVar[tuple[str, ...]] = ContextVar("visitkorea_request_secrets", default=())

TimeoutValue = float | httpx.Timeout
AsyncSleep = Callable[[float], Awaitable[None]]


class ResponseLike(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class SessionLike(Protocol):
    async def get(
        self, url: str, *, params: Mapping[str, Any], timeout: TimeoutValue
    ) -> ResponseLike: ...


TRANSIENT_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
DEFAULT_MAX_RETRIES = 0
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_MAX_BACKOFF = 20.0
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; visitkorea/0.1; +https://github.com/digitie/python-visitkorea-api)"
)


def build_session(retries: int = 3) -> httpx.AsyncClient:
    """자동 재시도 없이 비동기 세션을 만든다. 재시도는 토큰 획득 후 수행한다."""

    transport = httpx.AsyncHTTPTransport(retries=0)
    return httpx.AsyncClient(
        headers={"User-Agent": DEFAULT_USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


class TourApiHttp:
    """Low-level async JSON client for the data.go.kr TourAPI envelope."""

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
        max_rps: float = 5.0,
        rate_limiter: AsyncTokenBucket | None = None,
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
        self._session = session
        self.closed = False
        self._parent_is_closed: Callable[[], bool] | None = None
        self._validate_session(session)
        self.retries = max(0, retries)
        self._owns_session = session is None
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.retry_statuses = retry_statuses
        self.rate_limiter = rate_limiter if rate_limiter is not None else AsyncTokenBucket(max_rps)
        self._sleep = sleep

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        token = _request_secrets.set((self.service_key, *credential_values(params)))
        try:
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

            self._ready()
            attempt = 0
            connection_attempt = 0
            while True:
                await self.rate_limiter.acquire()
                session = self._ready()
                try:
                    if isinstance(session, httpx.AsyncClient):
                        request = session.build_request(
                            "GET", url, params=request_params, timeout=self.timeout
                        )
                        response = await send_after_token(
                            session, request, self.rate_limiter, before_send=self._before_send
                        )
                    else:
                        response = await session.get(
                            url, params=request_params, timeout=self.timeout
                        )
                except httpx.HTTPError as exc:
                    if (
                        isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout))
                        and connection_attempt < self.retries
                    ):
                        delay = (
                            0.0 if connection_attempt == 0 else 0.5 * 2 ** (connection_attempt - 1)
                        )
                        connection_attempt += 1
                        await self._sleep(delay)
                        continue
                    connection_attempt = 0
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
                connection_attempt = 0
                if (
                    response.status_code not in {401, 403}
                    and response.status_code in self.retry_statuses
                    and attempt < self.max_retries
                ):
                    close = getattr(response, "aclose", None)
                    if callable(close):
                        await close()
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
                body = _decode_response(
                    response,
                    endpoint=endpoint_path,
                    service_name=self.service_name,
                    service_key=self.service_key,
                )
                return body

        except TourApiError as exc:
            redact_exception(exc, self.service_key, *credential_values(params))
            raise exc from None
        finally:
            _request_secrets.reset(token)

    @staticmethod
    def _validate_session(session: SessionLike | None) -> None:
        if session is not None and not inspect.iscoroutinefunction(getattr(session, "get", None)):
            raise TypeError("session.get must be async")
        if (
            isinstance(session, httpx.AsyncClient)
            and session.auth is not None
            and type(session.auth) not in {httpx.Auth, httpx.BasicAuth}
        ):
            raise TypeError("Digest/custom Auth may send unmetered requests")

    def _ready(self) -> SessionLike:
        if self.closed or (self._parent_is_closed is not None and self._parent_is_closed()):
            raise RuntimeError("client is closed")
        if self._session is None:
            self._session = cast("SessionLike", build_session())
        self._validate_session(self._session)
        return self._session

    def _before_send(self) -> None:
        self._ready()

    @property
    def session(self) -> SessionLike:
        return self._ready()

    async def aclose(self) -> None:
        if not self.closed:
            self.closed = True
            close = getattr(self._session, "aclose", None)
            if self._owns_session and callable(close):
                await close()


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
        ) from None
    return _extract_body(
        payload, endpoint=endpoint, service_name=service_name, service_key=service_key
    )


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
    ) from None


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


def _extract_body(
    payload: Any, *, endpoint: str, service_name: str, service_key: str
) -> Mapping[str, Any]:
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
            service_key=service_key,
        )

    try:
        response = payload["response"]
        header = response["header"]
    except (KeyError, TypeError):
        raise TourApiParseError(
            "TourAPI response did not contain response.header",
            endpoint=endpoint,
            service_name=service_name,
            failure_kind="parse",
        ) from None

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
    _raise_for_result_code(
        code, message, endpoint=endpoint, service_name=service_name, service_key=service_key
    )
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


def _raise_for_data_error(data: Any, *, endpoint: str, service_name: str, service_key: str) -> None:
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
    _raise_for_result_code(
        code, message, endpoint=endpoint, service_name=service_name, service_key=service_key
    )


def _raise_for_result_code(
    code: str,
    message: str,
    *,
    endpoint: str,
    service_name: str,
    service_key: str | None,
) -> None:
    text = f"TourAPI returned {code}: {message}" if code else message
    text = _redact_secret(text, service_key)
    upper = f"{code}: {message}".upper()
    if code in {"20", "21", "30", "31", "32"} or "SERVICE_KEY" in upper or "AUTH" in upper:
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
        seconds = float(value)
        return max(0.0, seconds) if math.isfinite(seconds) else None
    except (TypeError, ValueError):
        return None


def _redact_secret(text: str, secret: str | None) -> str:
    return str(redact_secret(text, secret or ""))


class _KeyLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = re.sub(
            r"(?i)(service_?key|authkey|api_?key|access_token)=([^&\s]+)",
            r"\1=<REDACTED>",
            redact_secret(record.getMessage(), *_request_secrets.get()),
        )
        record.args = ()
        return True


for _log_name in ("httpx", "visitkorea.http"):
    logging.getLogger(_log_name).addFilter(_KeyLogFilter())
