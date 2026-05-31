"""Generic client for every OpenAPI service in the TourAPI Hub catalog."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable, Iterable, Iterator, Mapping
from typing import Any, cast

from kraddr.base import PlaceCoordinate

from ._auth import DEFAULT_SERVICE_KEY_SOURCE, resolve_service_key
from ._convert import enum_value, strip_or_none, to_int_or_none, to_yyyymmdd, without_none, yn
from ._http import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_BACKOFF,
    DEFAULT_MAX_RETRIES,
    AsyncSessionLike,
    AsyncTourApiHttp,
    SessionLike,
    TimeoutValue,
    TourApiHttp,
    build_async_session,
    build_session,
)
from ._pagination import async_iter_paginated_pages, iter_paginated_pages
from ._provenance import call_context
from ._ratelimit import RateLimiter
from ._service_views import (
    AsyncTypedServiceView,
    TypedServiceView,
    require_item_parser,
)
from .client import DEFAULT_BASE_URL, DEFAULT_ENV_NAMES, _extract_items
from .enums import MobileOS
from .exceptions import TourApiAuthError, TourApiRequestError
from .models import Page, RawRecord, RelatedTourItem
from .services import SERVICE_BY_KEY, SERVICE_DEFINITIONS, ServiceDefinition, get_api_catalog


class TourApiHubClient:
    """Catalog-aware client covering all services listed in useUtilExercises."""

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
        rate_limiter: RateLimiter | None = None,
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
        self.rate_limiter = rate_limiter
        self.session = cast("SessionLike", session or build_session(retries))
        self._owns_session = session is None

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
        """Create a catalog-aware client from environment variables."""

        service_key = resolve_service_key(
            source=service_key_source,
            env_names=(name, *fallback_names),
            env_file_paths=env_file_paths,
        )
        if not service_key:
            names = ", ".join((name, *fallback_names))
            raise TourApiAuthError(f"none of these environment variables are set: {names}")
        return cls(service_key=service_key, **kwargs)

    @classmethod
    def aio(
        cls,
        service_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncTourApiHubClient:
        """Create an asyncio-native catalog client."""

        return AsyncTourApiHubClient(service_key=service_key, **kwargs)

    def __enter__(self) -> TourApiHubClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the owned shared httpx client when this instance created it."""

        if self._owns_session and hasattr(self.session, "close"):
            self.session.close()

    @property
    def services(self) -> tuple[ServiceDefinition, ...]:
        """Return the official service catalog bundled with the package."""

        return SERVICE_DEFINITIONS

    def catalog(self) -> tuple[dict[str, Any], ...]:
        """Return UI-friendly service and operation catalog rows."""

        return get_api_catalog()

    def service(self, key: str) -> TourApiServiceClient:
        """Return a service-specific generic client by key, service name, or alias."""

        try:
            definition = SERVICE_BY_KEY[key.lower()]
        except KeyError as exc:
            known = ", ".join(service.key for service in SERVICE_DEFINITIONS)
            raise TourApiRequestError(f"unknown TourAPI service {key!r}; known: {known}") from exc
        client_class = (
            RelatedTourServiceClient
            if definition.key == "related_tour"
            else TourApiServiceClient
        )
        return client_class(
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

    @property
    def related_tour(self) -> RelatedTourServiceClient:
        """Typed client for TarRlteTarService1 related-tour operations."""

        return cast("RelatedTourServiceClient", self.service("related_tour"))

    def call(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """Call one operation from any registered service."""

        return self.service(service).call(operation, params=params, **kwargs)

    def iter_pages(
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
    ) -> Iterator[Page[RawRecord]]:
        """Iterate generic Hub pages for one service operation."""

        base_params = _without_page_params(params)

        def get_page(next_page_no: int, page_size: int) -> Page[RawRecord]:
            return self.call(
                service,
                operation,
                params=base_params,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        return iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        )

    def __getattr__(self, name: str) -> TourApiServiceClient:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.service(name)
        except TourApiRequestError as exc:
            raise AttributeError(name) from exc


class TourApiServiceClient:
    """Generic operation caller for one TourAPI service."""

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
        rate_limiter: RateLimiter | None = None,
        session: SessionLike | None,
    ) -> None:
        self.definition = definition
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
            rate_limiter=rate_limiter,
        )

    @property
    def operations(self) -> tuple[str, ...]:
        """Operations supported by this service according to the downloaded manual."""

        return self.definition.operations

    def call(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """Call an operation and return normalized raw item records."""

        endpoint = self._resolve_operation(operation)
        request_params = _page_params(params={}, page_no=page_no, num_of_rows=num_of_rows)
        if params:
            request_params.update(dict(params))
        request_params.update(_pythonic_params(kwargs))
        body = self._http.get(endpoint, params=without_none(request_params))
        rows = _extract_items(body, endpoint, service_name=self.definition.service_name)
        return Page(
            items=rows,
            total_count=to_int_or_none(body.get("totalCount")) or len(rows),
            page_no=to_int_or_none(body.get("pageNo")) or page_no or 1,
            num_of_rows=to_int_or_none(body.get("numOfRows")) or num_of_rows or len(rows),
            raw=body,
            context=call_context(
                service_name=self.definition.service_name,
                endpoint=endpoint,
                mobile_os=self._http.mobile_os,
                mobile_app=self._http.mobile_app,
                params=request_params,
            ),
        )

    def iter_pages(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> Iterator[Page[RawRecord]]:
        """Iterate generic pages for one operation in this service."""

        base_params = _without_page_params(params)

        def get_page(next_page_no: int, page_size: int) -> Page[RawRecord]:
            return self.call(
                operation,
                params=base_params,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        return iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        )

    @property
    def typed(self) -> TypedServiceView:
        """Return a view whose operations parse rows into this service's typed model."""

        return TypedServiceView(self, require_item_parser(self.definition.key))

    def __getattr__(self, name: str) -> Callable[..., Page[RawRecord]]:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            operation = self._resolve_operation(name)
        except TourApiRequestError as exc:
            raise AttributeError(name) from exc

        def caller(
            params: Mapping[str, Any] | None = None,
            *,
            page_no: int | None = 1,
            num_of_rows: int | None = 10,
            **kwargs: Any,
        ) -> Page[RawRecord]:
            return self.call(
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
    """Typed helper for TarRlteTarService1 related tourism records.

    `areaCd` and `signguCd` are TourAPI region codes for this service, not legal-dong
    codes. Pass them as `area_cd` and `signgu_cd` here; the request uses the official
    TourAPI parameter names.
    """

    def area_based_list(
        self,
        *,
        base_ym: str,
        area_cd: str,
        signgu_cd: str,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RelatedTourItem]:
        """Fetch related tourist attractions by TourAPI region code.

        `area_cd`/`signgu_cd` become `areaCd`/`signguCd`, which are TourAPI region
        codes for TarRlteTarService1 and not legal-dong codes.
        """

        params = {
            "baseYm": base_ym,
            "areaCd": area_cd,
            "signguCd": signgu_cd,
        }
        params.update(_pythonic_params(kwargs))
        return self._typed_related_page(
            "areaBasedList1",
            params=params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def search_keyword(
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
        """Search related tourist attractions by keyword and TourAPI region code.

        `area_cd`/`signgu_cd` become `areaCd`/`signguCd`, which are TourAPI region
        codes for TarRlteTarService1 and not legal-dong codes.
        """

        params = {
            "baseYm": base_ym,
            "areaCd": area_cd,
            "signguCd": signgu_cd,
            "keyword": keyword,
        }
        params.update(_pythonic_params(kwargs))
        return self._typed_related_page(
            "searchKeyword1",
            params=params,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

    def iter_area_based_list(
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
    ) -> Iterator[Page[RelatedTourItem]]:
        """Iterate `area_based_list()` typed pages."""

        def get_page(next_page_no: int, page_size: int) -> Page[RelatedTourItem]:
            return self.area_based_list(
                base_ym=base_ym,
                area_cd=area_cd,
                signgu_cd=signgu_cd,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        return iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        )

    def iter_search_keyword(
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
    ) -> Iterator[Page[RelatedTourItem]]:
        """Iterate `search_keyword()` typed pages."""

        def get_page(next_page_no: int, page_size: int) -> Page[RelatedTourItem]:
            return self.search_keyword(
                keyword,
                base_ym=base_ym,
                area_cd=area_cd,
                signgu_cd=signgu_cd,
                page_no=next_page_no,
                num_of_rows=page_size,
                **kwargs,
            )

        return iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        )

    def _typed_related_page(
        self,
        endpoint: str,
        *,
        params: Mapping[str, Any],
        page_no: int | None,
        num_of_rows: int | None,
    ) -> Page[RelatedTourItem]:
        request_params = _page_params(params=params, page_no=page_no, num_of_rows=num_of_rows)
        body = self._http.get(endpoint, params=without_none(request_params))
        rows = _extract_items(body, endpoint, service_name=self.definition.service_name)
        parsed = tuple(_related_tour_item(row) for row in rows)
        return Page(
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
        )


class AsyncTourApiHubClient:
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
        rate_limiter: RateLimiter | None = None,
        session: AsyncSessionLike | None = None,
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
        self.rate_limiter = rate_limiter
        self.session = cast("AsyncSessionLike", session or build_async_session(retries))
        self._owns_session = session is None

    @classmethod
    def from_env(
        cls,
        name: str = "DATA_GO_KR_SERVICE_KEY",
        *,
        fallback_names: tuple[str, ...] = (),
        service_key_source: str = DEFAULT_SERVICE_KEY_SOURCE,
        env_file_paths: Iterable[str] | None = None,
        **kwargs: Any,
    ) -> AsyncTourApiHubClient:
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

    async def __aenter__(self) -> AsyncTourApiHubClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned shared httpx async client when this instance created it."""

        if self._owns_session and hasattr(self.session, "aclose"):
            await self.session.aclose()

    @property
    def services(self) -> tuple[ServiceDefinition, ...]:
        """Return the official service catalog bundled with the package."""

        return SERVICE_DEFINITIONS

    def catalog(self) -> tuple[dict[str, Any], ...]:
        """Return UI-friendly service and operation catalog rows."""

        return get_api_catalog()

    def service(self, key: str) -> AsyncTourApiServiceClient:
        """Return an async service-specific generic client by key, service name, or alias."""

        try:
            definition = SERVICE_BY_KEY[key.lower()]
        except KeyError as exc:
            known = ", ".join(service.key for service in SERVICE_DEFINITIONS)
            raise TourApiRequestError(f"unknown TourAPI service {key!r}; known: {known}") from exc
        client_class = (
            AsyncRelatedTourServiceClient
            if definition.key == "related_tour"
            else AsyncTourApiServiceClient
        )
        return client_class(
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

    @property
    def related_tour(self) -> AsyncRelatedTourServiceClient:
        """Async typed client for TarRlteTarService1 related-tour operations."""

        return cast("AsyncRelatedTourServiceClient", self.service("related_tour"))

    async def call(
        self,
        service: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """Call one operation from any registered service asynchronously."""

        return await self.service(service).call(operation, params=params, **kwargs)

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

        async for page in async_iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        ):
            yield page

    def __getattr__(self, name: str) -> AsyncTourApiServiceClient:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.service(name)
        except TourApiRequestError as exc:
            raise AttributeError(name) from exc


class AsyncTourApiServiceClient:
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
        rate_limiter: RateLimiter | None = None,
        session: AsyncSessionLike | None,
    ) -> None:
        self.definition = definition
        self._operation_by_alias = _operation_aliases(definition.operations)
        self._http = AsyncTourApiHttp(
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
            rate_limiter=rate_limiter,
        )

    @property
    def operations(self) -> tuple[str, ...]:
        """Operations supported by this service according to the downloaded manual."""

        return self.definition.operations

    async def call(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[RawRecord]:
        """Call an operation and return normalized raw item records asynchronously."""

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
            page_no=to_int_or_none(body.get("pageNo")) or page_no or 1,
            num_of_rows=to_int_or_none(body.get("numOfRows")) or num_of_rows or len(rows),
            raw=body,
            context=call_context(
                service_name=self.definition.service_name,
                endpoint=endpoint,
                mobile_os=self._http.mobile_os,
                mobile_app=self._http.mobile_app,
                params=request_params,
            ),
        )

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

        async for page in async_iter_paginated_pages(
            get_page,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
        ):
            yield page

    @property
    def typed(self) -> AsyncTypedServiceView:
        """Return a view whose operations parse rows into this service's typed model."""

        return AsyncTypedServiceView(self, require_item_parser(self.definition.key))

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


class AsyncRelatedTourServiceClient(AsyncTourApiServiceClient):
    """Async typed helper for TarRlteTarService1 related tourism records."""

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

        async for page in async_iter_paginated_pages(
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

        async for page in async_iter_paginated_pages(
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
        request_params = _page_params(params=params, page_no=page_no, num_of_rows=num_of_rows)
        body = await self._http.get(endpoint, params=without_none(request_params))
        rows = _extract_items(body, endpoint, service_name=self.definition.service_name)
        parsed = tuple(_related_tour_item(row) for row in rows)
        return Page(
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
        )


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
