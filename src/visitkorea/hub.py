"""Generic client for every OpenAPI service in the TourAPI Hub catalog."""

from __future__ import annotations

import functools
import re
from collections.abc import AsyncIterator, Callable, Iterable, Mapping
from typing import Any, cast

from kraddr.base import PlaceCoordinate

from ._auth import DEFAULT_SERVICE_KEY_SOURCE, resolve_service_key
from ._convert import enum_value, strip_or_none, to_int_or_none, to_yyyymmdd, without_none, yn
from ._http import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_BACKOFF,
    DEFAULT_MAX_RETRIES,
    SessionLike,
    TimeoutValue,
    TourApiHttp,
    build_session,
)
from ._pagination import iter_paginated_pages
from ._provenance import call_context
from ._ratelimit import AsyncTokenBucket
from ._redact import credential_values, redact_debug, redact_exception, redact_result
from ._service_views import TypedServiceView, _parse_rows, require_item_parser
from .client import DEFAULT_BASE_URL, DEFAULT_ENV_NAMES, _extract_items
from .debug import DebugRun, debug_error, redact_sensitive
from .enums import MobileOS
from .exceptions import TourApiAuthError, TourApiError, TourApiRequestError
from .models import Page, RawRecord, RelatedTourItem
from .operation_schema import get_api_catalog_entry
from .services import SERVICE_BY_KEY, SERVICE_DEFINITIONS, ServiceDefinition, get_api_catalog


class TourApiHubClient:
    """Asyncio-native catalog-aware client for every TourAPI Hub service."""

    def __init__(
        self,
        service_key: str | None = None,
        *,
        mobile_os: MobileOS | str = MobileOS.ETC,
        mobile_app: str = "visitkorea",
        base_url: str = DEFAULT_BASE_URL,
        timeout: TimeoutValue = 10.0,
        retries: int = 3,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        max_rps: float = 5.0,
        rate_limiter: AsyncTokenBucket | None = None,
        session: SessionLike | None = None,
        service_key_source: str = DEFAULT_SERVICE_KEY_SOURCE,
    ) -> None:
        key = resolve_service_key(
            service_key,
            source=service_key_source,
            env_names=DEFAULT_ENV_NAMES,
        )
        if not key:
            raise TourApiAuthError(
                "service_key is required. Pass service_key=... or set DATA_GO_KR_SERVICE_KEY."
            )
        self.service_key = key
        self.mobile_os = str(enum_value(mobile_os))
        self.mobile_app = mobile_app
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.rate_limiter = rate_limiter if rate_limiter is not None else AsyncTokenBucket(max_rps)
        self._session = session
        self.closed = False
        TourApiHttp._validate_session(session)
        self._owns_session = session is None
        self._service_clients: dict[str, TourApiServiceClient] = {}

    @classmethod
    def from_env(
        cls,
        name: str = "DATA_GO_KR_SERVICE_KEY",
        *,
        fallback_names: tuple[str, ...] = (),
        service_key_source: str = DEFAULT_SERVICE_KEY_SOURCE,
        env_file_paths: Iterable[str] | None = None,
        **kwargs: Any,
    ) -> TourApiHubClient:
        """Create an async catalog-aware client from environment variables."""

        service_key = resolve_service_key(
            source=service_key_source,
            env_names=(name, *fallback_names),
            env_file_paths=env_file_paths,
        )
        if not service_key:
            names = ", ".join((name, *fallback_names))
            raise TourApiAuthError(f"none of these environment variables are set: {names}")
        return cls(service_key=service_key, **kwargs)

    async def __aenter__(self) -> TourApiHubClient:
        if self.closed:
            raise RuntimeError("client is closed")
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if not self.closed:
            self.closed = True
            for child in self._service_clients.values():
                await child._http.aclose()
            close = getattr(self._session, "aclose", None)
            if self._owns_session and callable(close):
                await close()

    @property
    def session(self) -> SessionLike:
        if self.closed:
            raise RuntimeError("client is closed")
        if self._session is None:
            self._session = cast("SessionLike", build_session())
        TourApiHttp._validate_session(self._session)
        return self._session

    @property
    def services(self) -> tuple[ServiceDefinition, ...]:
        """Return the official service catalog bundled with the package."""

        return SERVICE_DEFINITIONS

    def catalog(self) -> tuple[dict[str, Any], ...]:
        """Return UI-friendly service and operation catalog rows."""

        return get_api_catalog()

    def service(self, key: str) -> TourApiServiceClient:
        """Return an async service-specific generic client by key, service name, or alias."""

        try:
            definition = SERVICE_BY_KEY[key.lower()]
        except KeyError as exc:
            known = ", ".join(service.key for service in SERVICE_DEFINITIONS)
            raise TourApiRequestError(f"unknown TourAPI service {key!r}; known: {known}") from exc
        if self.closed:
            raise RuntimeError("client is closed")
        cached = self._service_clients.get(definition.key)
        if cached is not None:
            return cached
        client_class = (
            RelatedTourServiceClient if definition.key == "related_tour" else TourApiServiceClient
        )
        client = client_class(
            definition,
            service_key=self.service_key,
            mobile_os=self.mobile_os,
            mobile_app=self.mobile_app,
            base_url=self.base_url,
            timeout=self.timeout,
            retries=self.retries,
            max_retries=self.max_retries,
            backoff_factor=self.backoff_factor,
            max_backoff=self.max_backoff,
            rate_limiter=self.rate_limiter,
            session=self.session,
        )
        client._http._parent_is_closed = lambda: self.closed
        self._service_clients[definition.key] = client
        return client

    @property
    def related_tour(self) -> RelatedTourServiceClient:
        """Async typed client for TarRlteTarService1 related-tour operations."""

        return cast("RelatedTourServiceClient", self.service("related_tour"))

    async def call(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """Call one operation from any registered service asynchronously."""

        return await self.service(service).call(operation, params=params, **kwargs)

    async def debug_fetch(
        self,
        service_id: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        response_type: str = "json",
        use_typed: bool = False,
    ) -> DebugRun:
        """Call one catalog operation and return full request/response/trace detail.

        Routes purely through the catalog + generic service `.call()`/`.typed.call()`;
        there is no per-service or per-function branching here, so this method backs
        the debug UI and fixture generation for every service uniformly. `params` uses
        pythonic field names (the same ones `get_api_catalog_entry()` lists), matching
        the `**kwargs` convention already used by `TourApiServiceClient.call()`.
        `use_typed=True` parses items with the service's registered `.typed` row
        parser (see `SERVICE_ITEM_PARSERS`) when one exists, and raises otherwise.
        """

        if response_type != "json":
            raise TourApiRequestError(
                "visitkorea TourAPI always responds with JSON; "
                f"response_type={response_type!r} is not supported."
            )

        pythonic_params = dict(params or {})
        input_data = redact_sensitive(
            {
                "service_id": service_id,
                "operation": operation,
                "params": pythonic_params,
                "page_no": page_no,
                "num_of_rows": num_of_rows,
                "response_type": response_type,
                "use_typed": use_typed,
            }
        )
        trace: list[str] = [
            f"service_id={service_id}",
            f"operation={operation}",
            f"use_typed={use_typed}",
        ]

        try:
            catalog_entry = get_api_catalog_entry(service_id, operation)
        except Exception as exc:
            trace.append(f"catalog_lookup_failed={type(exc).__name__}")
            return redact_debug(
                DebugRun(
                    function=f"{service_id}.{operation}",
                    input=input_data,
                    request={},
                    response={},
                    parsed=None,
                    processed=None,
                    trace=trace,
                    error=debug_error(exc),
                    catalog=None,
                ),
                self.service_key,
                *credential_values(params),
            )

        trace.append(f"dataset={catalog_entry['dataset_name']}")
        trace.append(f"service_key_apply_url={catalog_entry['service_key_apply_url']}")

        try:
            service_client = self.service(service_id)
            resolved_operation = service_client._resolve_operation(operation)
            caller = service_client.typed if use_typed else service_client
            page = await caller.call(
                resolved_operation,
                page_no=page_no,
                num_of_rows=num_of_rows,
                **pythonic_params,
            )
        except Exception as exc:
            trace.append(f"call_failed={type(exc).__name__}")
            return redact_debug(
                DebugRun(
                    function=f"{service_id}.{operation}",
                    input=input_data,
                    request={"method": "GET", "query": redact_sensitive(pythonic_params)},
                    response={},
                    parsed=None,
                    processed=None,
                    trace=trace,
                    error=debug_error(exc),
                    catalog=catalog_entry,
                ),
                self.service_key,
                *credential_values(params),
            )

        request_url = f"{self.base_url}/{catalog_entry['service_name']}/{resolved_operation}"
        trace.append(f"items={len(page.items)}")
        trace.append(f"total_count={page.total_count}")
        return redact_debug(
            DebugRun(
                function=f"{service_id}.{resolved_operation}",
                input=input_data,
                request={
                    "method": "GET",
                    "url": request_url,
                    "query": redact_sensitive(dict(page.context.request_params)),
                    "headers": {"Accept": "application/json"},
                },
                response={"status_code": 200, "headers": {}, "body": page.raw},
                parsed=page,
                processed=tuple(page.items),
                trace=trace,
                catalog=catalog_entry,
            ),
            self.service_key,
            *credential_values(params),
        )

    async def iter_pages(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Page[RawRecord]]:
        """Asynchronously iterate generic Hub pages for one service operation."""

        base_params = _without_page_params(params)

        async def get_page(next_page_no: int, page_size: int) -> Page[RawRecord]:
            return await self.call(
                service,
                operation,
                params=base_params,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        async for page in iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        ):
            yield page

    def __getattr__(self, name: str) -> TourApiServiceClient:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.service(name)
        except TourApiRequestError as exc:
            raise AttributeError(name) from exc


class TourApiServiceClient:
    """Async generic operation caller for one TourAPI service."""

    def __init__(
        self,
        definition: ServiceDefinition,
        *,
        service_key: str,
        mobile_os: str,
        mobile_app: str,
        base_url: str,
        timeout: TimeoutValue,
        retries: int,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        max_rps: float = 5.0,
        rate_limiter: AsyncTokenBucket | None = None,
        session: SessionLike | None,
    ) -> None:
        self.definition = definition
        self.rate_limiter = rate_limiter if rate_limiter is not None else AsyncTokenBucket(max_rps)
        self._operation_by_alias = _operation_aliases(definition.operations)
        self._http = TourApiHttp(
            service_key,
            base_url=base_url,
            service_name=definition.service_name,
            mobile_os=mobile_os,
            mobile_app=mobile_app,
            session=session,
            timeout=timeout,
            retries=retries,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            max_backoff=max_backoff,
            rate_limiter=self.rate_limiter,
        )

    @property
    def operations(self) -> tuple[str, ...]:
        """Operations supported by this service according to the downloaded manual."""

        return self.definition.operations

    async def __aenter__(self) -> TourApiServiceClient:
        self._http._ready()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """자체 생성 세션을 닫는다. 주입 세션의 소유권은 호출자에게 있다."""
        await self._http.aclose()

    async def call(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """공개 원문 페이지에서 인증값을 제거해 반환한다."""
        page = await self._call(
            operation, params=params, page_no=page_no, num_of_rows=num_of_rows, **kwargs
        )
        return redact_result(
            page, self._http.service_key, *credential_values(params), *credential_values(kwargs)
        )

    async def _call(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """Call an operation and return normalized raw item records asynchronously.

        Unlike the typed client's detail_* methods, this never raises
        TourApiNoDataError on an empty result; it returns an empty Page.
        """

        try:
            endpoint = self._resolve_operation(operation)
            request_params = _page_params(params={}, page_no=page_no, num_of_rows=num_of_rows)
            if params:
                request_params.update(dict(params))
            request_params.update(_pythonic_params(kwargs))
            body = await self._http.get(endpoint, params=without_none(request_params))
            rows = _extract_items(body, endpoint, service_name=self.definition.service_name)
            return Page(
                items=rows,
                total_count=to_int_or_none(body.get("totalCount")) or len(rows),
                page_no=to_int_or_none(body.get("pageNo"))
                or to_int_or_none(request_params.get("pageNo"))
                or 1,
                num_of_rows=to_int_or_none(body.get("numOfRows"))
                or to_int_or_none(request_params.get("numOfRows"))
                or len(rows),
                raw=body,
                context=call_context(
                    service_name=self.definition.service_name,
                    endpoint=endpoint,
                    mobile_os=self._http.mobile_os,
                    mobile_app=self._http.mobile_app,
                    params=request_params,
                ),
            )

        except TourApiError as exc:
            redact_exception(
                exc, self._http.service_key, *credential_values(params), *credential_values(kwargs)
            )
            raise exc from None

    async def iter_pages(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Page[RawRecord]]:
        """Asynchronously iterate generic pages for one operation in this service."""

        base_params = _without_page_params(params)

        async def get_page(next_page_no: int, page_size: int) -> Page[RawRecord]:
            return await self.call(
                operation,
                params=base_params,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        async for page in iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        ):
            yield page

    @property
    def typed(self) -> TypedServiceView:
        """Return a view whose operations parse rows into this service's typed model."""

        return TypedServiceView(self, require_item_parser(self.definition.key))

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            operation = self._resolve_operation(name)
        except TourApiRequestError as exc:
            raise AttributeError(name) from exc

        async def caller(
            params: Mapping[str, Any] | None = None,
            *,
            page_no: int | None = 1,
            num_of_rows: int | None = 10,
            **kwargs: Any,
        ) -> Page[RawRecord]:
            return await self.call(
                operation,
                params=params,
                page_no=page_no,
                num_of_rows=num_of_rows,
                **kwargs,
            )

        return caller

    def _resolve_operation(self, operation: str) -> str:
        if operation in self.definition.operations:
            return operation
        key = operation.lower()
        try:
            return self._operation_by_alias[key]
        except KeyError as exc:
            known = ", ".join(sorted(self._operation_by_alias))
            raise TourApiRequestError(
                f"{self.definition.key}: unknown operation {operation!r}; known aliases: {known}"
            ) from exc


class RelatedTourServiceClient(TourApiServiceClient):
    """Async typed helper for TarRlteTarService1 related tourism records."""

    @property
    def typed(self) -> TypedServiceView:
        """Not available: use area_based_list()/search_keyword() for typed access."""

        raise TourApiRequestError(
            "related_tour: no generic typed model is registered; use "
            "area_based_list()/search_keyword() for typed access instead of .typed"
        )

    async def area_based_list(
        self,
        *,
        base_ym: str,
        area_cd: str,
        signgu_cd: str,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RelatedTourItem]:
        """Fetch related tourist attractions by TourAPI region code asynchronously."""

        params = {
            "baseYm": base_ym,
            "areaCd": area_cd,
            "signguCd": signgu_cd,
        }
        params.update(_pythonic_params(kwargs))
        return await self._typed_related_page(
            "areaBasedList1",
            params=params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def search_keyword(
        self,
        keyword: str,
        *,
        base_ym: str,
        area_cd: str,
        signgu_cd: str,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RelatedTourItem]:
        """Search related tourist attractions by keyword and TourAPI region code."""

        params = {
            "baseYm": base_ym,
            "areaCd": area_cd,
            "signguCd": signgu_cd,
            "keyword": keyword,
        }
        params.update(_pythonic_params(kwargs))
        return await self._typed_related_page(
            "searchKeyword1",
            params=params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    async def iter_area_based_list(
        self,
        *,
        base_ym: str,
        area_cd: str,
        signgu_cd: str,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Page[RelatedTourItem]]:
        """Asynchronously iterate `area_based_list()` typed pages."""

        async def get_page(next_page_no: int, page_size: int) -> Page[RelatedTourItem]:
            return await self.area_based_list(
                base_ym=base_ym,
                area_cd=area_cd,
                signgu_cd=signgu_cd,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        async for page in iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        ):
            yield page

    async def iter_search_keyword(
        self,
        keyword: str,
        *,
        base_ym: str,
        area_cd: str,
        signgu_cd: str,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Page[RelatedTourItem]]:
        """Asynchronously iterate `search_keyword()` typed pages."""

        async def get_page(next_page_no: int, page_size: int) -> Page[RelatedTourItem]:
            return await self.search_keyword(
                keyword,
                base_ym=base_ym,
                area_cd=area_cd,
                signgu_cd=signgu_cd,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        async for page in iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        ):
            yield page

    async def _typed_related_page(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any],
        page_no: int | None,
        num_of_rows: int | None,
    ) -> Page[RelatedTourItem]:
        try:
            request_params = _page_params(params=params, page_no=page_no, num_of_rows=num_of_rows)
            body = await self._http.get(endpoint, params=without_none(request_params))
            rows = _extract_items(body, endpoint, service_name=self.definition.service_name)
            parsed = _parse_rows(
                rows,
                _related_tour_item,
                endpoint=endpoint,
                service_name=self.definition.service_name,
            )
            return redact_result(
                Page(
                    items=parsed,
                    total_count=to_int_or_none(body.get("totalCount")) or len(parsed),
                    page_no=to_int_or_none(body.get("pageNo")) or page_no or 1,
                    num_of_rows=to_int_or_none(body.get("numOfRows")) or num_of_rows or len(parsed),
                    raw=body,
                    context=call_context(
                        service_name=self.definition.service_name,
                        endpoint=endpoint,
                        mobile_os=self._http.mobile_os,
                        mobile_app=self._http.mobile_app,
                        params=request_params,
                    ),
                ),
                self._http.service_key,
                *credential_values(params),
            )

        except TourApiError as exc:
            redact_exception(exc, self._http.service_key, *credential_values(params))
            raise exc from None


@functools.cache
def _operation_aliases(operations: tuple[str, ...]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    counts: dict[str, int] = {}
    for operation in operations:
        snake = _snake_case(operation)
        candidates = {operation.lower(), snake}
        stripped = re.sub(r"_?\d+$", "", snake)
        if stripped != snake:
            candidates.add(stripped)
        for candidate in candidates:
            counts[candidate] = counts.get(candidate, 0) + 1
            aliases[candidate] = operation
    return {key: value for key, value in aliases.items() if counts[key] == 1}


def _snake_case(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.replace("__", "_").lower()


def _page_params(
    *,
    params: Mapping[str, Any],
    page_no: int | None,
    num_of_rows: int | None,
) -> dict[str, Any]:
    request_params: dict[str, Any] = {}
    if page_no is not None:
        request_params["pageNo"] = page_no
    if num_of_rows is not None:
        request_params["numOfRows"] = num_of_rows
    request_params.update(dict(params))
    return request_params


def _without_page_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    cleaned = dict(params or {})
    cleaned.pop("pageNo", None)
    cleaned.pop("numOfRows", None)
    return cleaned


PYTHONIC_PARAM_ALIASES: dict[str, str] = {
    "area_cd": "areaCd",
    "area_code": "areaCode",
    "base_ym": "baseYm",
    "base_ymd": "baseYmd",
    "content_id": "contentId",
    "content_type_id": "contentTypeId",
    "course_idx": "courseIdx",
    "event_end_date": "eventEndDate",
    "event_start_date": "eventStartDate",
    "facility_name": "facltNm",
    "gallery_content_id": "galContentId",
    "gallery_search_keyword": "galSearchKeyword",
    "gallery_title": "galTitle",
    "image_yn": "imageYN",
    "l_dong_list_yn": "lDongListYn",
    "l_dong_regn_cd": "lDongRegnCd",
    "l_dong_signgu_cd": "lDongSignguCd",
    "lcls_systm1": "lclsSystm1",
    "lcls_systm2": "lclsSystm2",
    "lcls_systm3": "lclsSystm3",
    "lcls_systm_list_yn": "lclsSystmListYn",
    "map_x": "mapX",
    "map_y": "mapY",
    "mobile_app": "MobileApp",
    "mobile_os": "MobileOS",
    "modified_time": "modifiedtime",
    "num_of_rows": "numOfRows",
    "page_no": "pageNo",
    "route_idx": "routeIdx",
    "show_flag": "showFlag",
    "sigungu_code": "sigunguCode",
    "sigungu_name": "sigunguNm",
    "signgu_cd": "signguCd",
    "sub_image_yn": "subImageYN",
}
DATE_PARAM_ALIASES: dict[str, str] = {
    "base_ymd": "baseYmd",
    "event_end_date": "eventEndDate",
    "event_start_date": "eventStartDate",
    "modified_time": "modifiedtime",
}
YN_PARAM_ALIASES: dict[str, str] = {
    "image_yn": "imageYN",
    "l_dong_list_yn": "lDongListYn",
    "lcls_systm_list_yn": "lclsSystmListYn",
    "sub_image_yn": "subImageYN",
}


def _pythonic_params(params: Mapping[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    for key, value in params.items():
        if key == "coordinate":
            if value is None:
                continue
            if isinstance(value, PlaceCoordinate):
                coordinate = value
            elif isinstance(value, tuple):
                coordinate = PlaceCoordinate.from_tuple(value)
            elif isinstance(value, Mapping):
                mapped_coordinate = PlaceCoordinate.from_mapping(value)
                if mapped_coordinate is None:
                    raise ValueError(
                        "coordinate mapping requires longitude/latitude, lon/lat, or mapX/mapY"
                    )
                coordinate = mapped_coordinate
            else:
                raise TypeError(
                    "coordinate must be PlaceCoordinate, (latitude, longitude), or mapping"
                )
            converted.update({"mapX": coordinate.lon, "mapY": coordinate.lat})
        elif key in DATE_PARAM_ALIASES:
            converted[DATE_PARAM_ALIASES[key]] = to_yyyymmdd(value, field=key)
        elif key in YN_PARAM_ALIASES:
            converted[YN_PARAM_ALIASES[key]] = yn(value)
        elif key in PYTHONIC_PARAM_ALIASES:
            converted[PYTHONIC_PARAM_ALIASES[key]] = enum_value(value)
        else:
            converted[key] = enum_value(value)
    return converted


def _related_tour_item(row: Mapping[str, Any]) -> RelatedTourItem:
    return RelatedTourItem(
        baseYm=strip_or_none(row.get("baseYm")),
        tAtsCd=strip_or_none(row.get("tAtsCd")),
        tAtsNm=strip_or_none(row.get("tAtsNm")),
        areaCd=strip_or_none(row.get("areaCd")),
        areaNm=strip_or_none(row.get("areaNm")),
        signguCd=strip_or_none(row.get("signguCd")),
        signguNm=strip_or_none(row.get("signguNm")),
        rlteTatsCd=strip_or_none(row.get("rlteTatsCd")),
        rlteTatsNm=strip_or_none(row.get("rlteTatsNm")),
        rlteRegnCd=strip_or_none(row.get("rlteRegnCd")),
        rlteRegnNm=strip_or_none(row.get("rlteRegnNm")),
        rlteSignguCd=strip_or_none(row.get("rlteSignguCd")),
        rlteSignguNm=strip_or_none(row.get("rlteSignguNm")),
        rlteCtgryLclsNm=strip_or_none(row.get("rlteCtgryLclsNm")),
        rlteCtgryMclsNm=strip_or_none(row.get("rlteCtgryMclsNm")),
        rlteCtgrySclsNm=strip_or_none(row.get("rlteCtgrySclsNm")),
        rlteRank=strip_or_none(row.get("rlteRank")),
        raw=row,
    )
