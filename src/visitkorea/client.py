"""User-facing TourAPI client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Iterator, Mapping
from datetime import date, datetime
from typing import Any, TypeVar

from kraddr.base import PlaceCoordinate

from ._auth import DATA_GO_KR_ENV_NAMES, DEFAULT_SERVICE_KEY_SOURCE, resolve_service_key
from ._convert import (
    enum_value,
    strip_or_none,
    to_float_or_none,
    to_int_or_none,
    to_yyyymmdd,
    yn,
)
from ._http import AsyncSessionLike, AsyncTourApiHttp, SessionLike, TourApiHttp
from ._pagination import async_iter_paginated_pages, iter_paginated_pages
from ._provenance import call_context
from ._time import parse_tour_datetime
from .enums import SERVICE_NAME_BY_LANGUAGE, AreaCode, Arrange, ContentType, Language, MobileOS
from .exceptions import TourApiAuthError, TourApiNoDataError, TourApiParseError, TourApiRequestError
from .models import (
    CodeItem,
    ImageInfo,
    IntroInfo,
    Page,
    RawRecord,
    RepeatInfo,
    TourDetail,
    TourItem,
)

DEFAULT_BASE_URL = "http://apis.data.go.kr/B551011"
DEFAULT_ENV_NAMES = DATA_GO_KR_ENV_NAMES
T = TypeVar("T")


class KrTourApiClient:
    """Client for Korea Tourism Organization TourAPI services.

    The default service is `KorService2`, the current Korean tourism information
    gateway on data.go.kr. Other language service names can be selected with
    `language=` or by passing `service_name=` directly.
    """

    def __init__(
        self,
        service_key: str | None = None,
        *,
        language: Language | str = Language.KOREAN,
        service_name: str | None = None,
        mobile_os: MobileOS | str = MobileOS.ETC,
        mobile_app: str = "visitkorea",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        retries: int = 3,
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
        resolved_service_name = service_name or _service_name_for_language(language)
        self.service_key = key
        self.service_name = resolved_service_name
        self.mobile_os = str(enum_value(mobile_os))
        self.mobile_app = mobile_app
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http = TourApiHttp(
            key,
            base_url=self.base_url,
            service_name=resolved_service_name,
            mobile_os=self.mobile_os,
            mobile_app=mobile_app,
            session=session,
            timeout=timeout,
            retries=retries,
        )

    @classmethod
    def from_env(
        cls,
        name: str = "DATA_GO_KR_SERVICE_KEY",
        *,
        fallback_names: tuple[str, ...] = (),
        service_key_source: str = DEFAULT_SERVICE_KEY_SOURCE,
        env_file_paths: Iterable[str] | None = None,
        **kwargs: Any,
    ) -> KrTourApiClient:
        """Create a client from environment variables."""

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
    ) -> AsyncKrTourApiClient:
        """Create an asyncio-native client with the same public methods."""

        return AsyncKrTourApiClient(service_key=service_key, **kwargs)

    def __enter__(self) -> KrTourApiClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the owned httpx client when this instance created it."""

        self._http.close()

    def raw_endpoint(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
    ) -> Page[RawRecord]:
        """Call a TourAPI endpoint and return normalized raw item mappings."""

        return self._get_page(endpoint, dict(params or {}), lambda row: row)

    def iter_pages(
        self,
        fetch_page: Callable[..., Page[T]],
        *args: Any,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> Iterator[Page[T]]:
        """Iterate a page-returning typed client method.

        The helper follows `Page.total_count`, `page_no`, and `num_of_rows`.
        `max_pages` or `max_items` can be set as an extra guard for unusual API
        responses. NO_DATA list responses produce an empty iterator, while TourAPI
        auth, quota, and server errors are raised unchanged.
        """

        def get_page(next_page_no: int, page_size: int) -> Page[T]:
            return fetch_page(
                *args,
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

    def area_based_list(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        """Search tourism information by area filters."""

        params = self._list_params(
            content_type_id=content_type_id,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,
            cat2=cat2,
            cat3=cat3,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        return self._get_page("areaBasedList2", params, _tour_item)

    def location_based_list(
        self,
        *,
        radius: int,
        map_x: float | None = None,
        map_y: float | None = None,
        coordinate: PlaceCoordinate | tuple[float, float] | Mapping[str, Any] | None = None,
        content_type_id: ContentType | str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.DISTANCE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        """Search tourism information around WGS84 coordinates."""

        coordinate_value = _resolve_coordinate(map_x=map_x, map_y=map_y, coordinate=coordinate)
        if not 1 <= int(radius) <= 20000:
            raise ValueError("radius must be between 1 and 20000 meters")
        params = self._list_params(
            content_type_id=content_type_id,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params.update(
            {"mapX": coordinate_value.lon, "mapY": coordinate_value.lat, "radius": int(radius)}
        )
        return self._get_page("locationBasedList2", params, _tour_item)

    def search_keyword(
        self,
        keyword: str,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        """Search tourism information by keyword."""

        if not keyword.strip():
            raise ValueError("keyword must not be empty")
        params = self._list_params(
            content_type_id=content_type_id,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,
            cat2=cat2,
            cat3=cat3,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params["keyword"] = keyword
        return self._get_page("searchKeyword2", params, _tour_item)

    def search_festival(
        self,
        event_start_date: str | date | datetime,
        *,
        event_end_date: str | date | datetime | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        """Search event/festival information by event date."""

        params = self._list_params(
            area_code=area_code,
            sigungu_code=sigungu_code,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params["eventStartDate"] = to_yyyymmdd(event_start_date, field="event_start_date")
        params["eventEndDate"] = to_yyyymmdd(event_end_date, field="event_end_date")
        return self._get_page("searchFestival2", params, _tour_item)

    def search_stay(
        self,
        *,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        """Search accommodation information."""

        params = self._list_params(
            area_code=area_code,
            sigungu_code=sigungu_code,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        return self._get_page("searchStay2", params, _tour_item)

    def detail_common(
        self,
        content_id: str,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> TourDetail:
        """Fetch common detail information for a content ID."""

        if not content_id:
            raise ValueError("content_id must not be empty")
        page = self._get_page(
            "detailCommon2",
            self._page_params(page_no=page_no, num_of_rows=num_of_rows)
            | {"contentId": content_id},
            _tour_detail,
        )
        if not page.items:
            raise TourApiNoDataError(
                f"detailCommon2 returned no item for content_id={content_id}",
                result_code="03",
                endpoint="detailCommon2",
                service_name=self.service_name,
                failure_kind="no_data",
            )
        return page.items[0].model_copy(update={"context": page.context})

    def detail_intro(
        self,
        content_id: str,
        content_type_id: ContentType | str,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[IntroInfo]:
        """Fetch introduction fields. The raw fields vary by content type."""

        params = self._detail_params(content_id, content_type_id, page_no, num_of_rows)
        return self._get_page("detailIntro2", params, _intro_info)

    def detail_info(
        self,
        content_id: str,
        content_type_id: ContentType | str,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[RepeatInfo]:
        """Fetch repeated detail records."""

        params = self._detail_params(content_id, content_type_id, page_no, num_of_rows)
        return self._get_page("detailInfo2", params, _repeat_info)

    def detail_images(
        self,
        content_id: str,
        *,
        image_yn: bool | str | None = True,
        sub_image_yn: bool | str | None = True,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[ImageInfo]:
        """Fetch image metadata for a content ID."""

        if not content_id:
            raise ValueError("content_id must not be empty")
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "contentId": content_id,
            "imageYN": yn(image_yn),
            "subImageYN": yn(sub_image_yn),
        }
        return self._get_page("detailImage2", params, _image_info)

    def area_based_sync_list(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        show_flag: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        """Fetch tourism synchronization list items."""

        if show_flag is not None and show_flag not in {"0", "1"}:
            raise ValueError("show_flag must be '0' or '1'")
        params = self._list_params(
            content_type_id=content_type_id,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,
            cat2=cat2,
            cat3=cat3,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params["showFlag"] = show_flag
        return self._get_page("areaBasedSyncList2", params, _tour_item)

    def area_codes(
        self,
        area_code: AreaCode | str | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        """Fetch area codes, or sigungu codes when area_code is provided."""

        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "areaCode": enum_value(area_code)
        }
        return self._get_page("areaCode2", params, _code_item)

    def category_codes(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        """Fetch service category codes."""

        _validate_category_chain(cat1=cat1, cat2=cat2, cat3=cat3)
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "contentTypeId": enum_value(content_type_id),
            "cat1": cat1,
            "cat2": cat2,
            "cat3": cat3,
        }
        return self._get_page("categoryCode2", params, _code_item)

    def legal_dong_codes(
        self,
        *,
        l_dong_regn_cd: str | None = None,
        list_yn: bool | str | None = False,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        """Fetch legal-dong codes from ldongCode2."""

        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "lDongRegnCd": l_dong_regn_cd,
            "lDongListYn": yn(list_yn),
        }
        return self._get_page("ldongCode2", params, _code_item)

    def classification_system_codes(
        self,
        *,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        list_yn: bool | str | None = False,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        """Fetch TourAPI classification-system codes."""

        _validate_lcls_chain(
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
        )
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "lclsSystm1": lcls_systm1,
            "lclsSystm2": lcls_systm2,
            "lclsSystm3": lcls_systm3,
            "lclsSystmListYn": yn(list_yn),
        }
        return self._get_page("lclsSystmCode2", params, _code_item)

    def _detail_params(
        self,
        content_id: str,
        content_type_id: ContentType | str,
        page_no: int,
        num_of_rows: int,
    ) -> dict[str, Any]:
        if not content_id:
            raise ValueError("content_id must not be empty")
        return self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "contentId": content_id,
            "contentTypeId": enum_value(content_type_id),
        }

    def _list_params(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = None,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> dict[str, Any]:
        _validate_page(page_no, num_of_rows)
        _validate_legacy_area(area_code=area_code, sigungu_code=sigungu_code)
        _validate_category_chain(cat1=cat1, cat2=cat2, cat3=cat3)
        _validate_ldong_chain(
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
        )
        _validate_lcls_chain(
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
        )
        return {
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "arrange": enum_value(arrange),
            "contentTypeId": enum_value(content_type_id),
            "modifiedtime": to_yyyymmdd(modified_time, field="modified_time"),
            "areaCode": enum_value(area_code),
            "sigunguCode": sigungu_code,
            "cat1": cat1,
            "cat2": cat2,
            "cat3": cat3,
            "lDongRegnCd": l_dong_regn_cd,
            "lDongSignguCd": l_dong_signgu_cd,
            "lclsSystm1": lcls_systm1,
            "lclsSystm2": lcls_systm2,
            "lclsSystm3": lcls_systm3,
        }

    def _page_params(self, *, page_no: int, num_of_rows: int) -> dict[str, int]:
        _validate_page(page_no, num_of_rows)
        return {"pageNo": page_no, "numOfRows": num_of_rows}

    def _get_page(
        self,
        endpoint: str,
        params: Mapping[str, Any],
        parser: Callable[[Mapping[str, Any]], T],
    ) -> Page[T]:
        body = self._http.get(endpoint, params=params)
        rows = _extract_items(body, endpoint, service_name=self.service_name)
        try:
            parsed = tuple(parser(row) for row in rows)
        except (TypeError, ValueError) as exc:
            raise TourApiParseError(
                f"{endpoint}: failed to parse item: {exc}",
                endpoint=endpoint,
                service_name=self.service_name,
                failure_kind="parse",
            ) from exc
        return Page(
            items=parsed,
            total_count=to_int_or_none(body.get("totalCount")) or len(parsed),
            page_no=to_int_or_none(body.get("pageNo")) or to_int_or_none(params.get("pageNo")) or 1,
            num_of_rows=(
                to_int_or_none(body.get("numOfRows"))
                or to_int_or_none(params.get("numOfRows"))
                or len(parsed)
            ),
            raw=body,
            context=call_context(
                service_name=self.service_name,
                endpoint=endpoint,
                mobile_os=self.mobile_os,
                mobile_app=self.mobile_app,
                params=params,
            ),
        )


class AsyncKrTourApiClient:
    """Asyncio-native client for Korea Tourism Organization TourAPI services."""

    def __init__(
        self,
        service_key: str | None = None,
        *,
        language: Language | str = Language.KOREAN,
        service_name: str | None = None,
        mobile_os: MobileOS | str = MobileOS.ETC,
        mobile_app: str = "visitkorea",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        retries: int = 3,
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
        resolved_service_name = service_name or _service_name_for_language(language)
        self.service_key = key
        self.service_name = resolved_service_name
        self.mobile_os = str(enum_value(mobile_os))
        self.mobile_app = mobile_app
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http = AsyncTourApiHttp(
            key,
            base_url=self.base_url,
            service_name=resolved_service_name,
            mobile_os=self.mobile_os,
            mobile_app=mobile_app,
            session=session,
            timeout=timeout,
            retries=retries,
        )

    @classmethod
    def from_env(
        cls,
        name: str = "DATA_GO_KR_SERVICE_KEY",
        *,
        fallback_names: tuple[str, ...] = (),
        service_key_source: str = DEFAULT_SERVICE_KEY_SOURCE,
        env_file_paths: Iterable[str] | None = None,
        **kwargs: Any,
    ) -> AsyncKrTourApiClient:
        """Create an async client from environment variables."""

        service_key = resolve_service_key(
            source=service_key_source,
            env_names=(name, *fallback_names),
            env_file_paths=env_file_paths,
        )
        if not service_key:
            names = ", ".join((name, *fallback_names))
            raise TourApiAuthError(f"none of these environment variables are set: {names}")
        return cls(service_key=service_key, **kwargs)

    async def __aenter__(self) -> AsyncKrTourApiClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned httpx async client when this instance created it."""

        await self._http.aclose()

    async def raw_endpoint(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
    ) -> Page[RawRecord]:
        """Call a TourAPI endpoint and return normalized raw item mappings."""

        return await self._get_page(endpoint, dict(params or {}), lambda row: row)

    async def iter_pages(
        self,
        fetch_page: Callable[..., Awaitable[Page[T]]],
        *args: Any,
        page_no: int = 1,
        num_of_rows: int = 10,
        max_pages: int | None = None,
        max_items: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Page[T]]:
        """Asynchronously iterate a page-returning typed client method."""

        async def get_page(next_page_no: int, page_size: int) -> Page[T]:
            return await fetch_page(
                *args,
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

    async def area_based_list(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        params = self._list_params(
            content_type_id=content_type_id,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,
            cat2=cat2,
            cat3=cat3,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        return await self._get_page("areaBasedList2", params, _tour_item)

    async def location_based_list(
        self,
        *,
        radius: int,
        map_x: float | None = None,
        map_y: float | None = None,
        coordinate: PlaceCoordinate | tuple[float, float] | Mapping[str, Any] | None = None,
        content_type_id: ContentType | str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.DISTANCE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        coordinate_value = _resolve_coordinate(map_x=map_x, map_y=map_y, coordinate=coordinate)
        if not 1 <= int(radius) <= 20000:
            raise ValueError("radius must be between 1 and 20000 meters")
        params = self._list_params(
            content_type_id=content_type_id,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params.update(
            {"mapX": coordinate_value.lon, "mapY": coordinate_value.lat, "radius": int(radius)}
        )
        return await self._get_page("locationBasedList2", params, _tour_item)

    async def search_keyword(
        self,
        keyword: str,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        if not keyword.strip():
            raise ValueError("keyword must not be empty")
        params = self._list_params(
            content_type_id=content_type_id,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,
            cat2=cat2,
            cat3=cat3,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params["keyword"] = keyword
        return await self._get_page("searchKeyword2", params, _tour_item)

    async def search_festival(
        self,
        event_start_date: str | date | datetime,
        *,
        event_end_date: str | date | datetime | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        params = self._list_params(
            area_code=area_code,
            sigungu_code=sigungu_code,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params["eventStartDate"] = to_yyyymmdd(event_start_date, field="event_start_date")
        params["eventEndDate"] = to_yyyymmdd(event_end_date, field="event_end_date")
        return await self._get_page("searchFestival2", params, _tour_item)

    async def search_stay(
        self,
        *,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        params = self._list_params(
            area_code=area_code,
            sigungu_code=sigungu_code,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            modified_time=modified_time,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        return await self._get_page("searchStay2", params, _tour_item)

    async def detail_common(
        self,
        content_id: str,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> TourDetail:
        if not content_id:
            raise ValueError("content_id must not be empty")
        page = await self._get_page(
            "detailCommon2",
            self._page_params(page_no=page_no, num_of_rows=num_of_rows)
            | {"contentId": content_id},
            _tour_detail,
        )
        if not page.items:
            raise TourApiNoDataError(
                f"detailCommon2 returned no item for content_id={content_id}",
                result_code="03",
                endpoint="detailCommon2",
                service_name=self.service_name,
                failure_kind="no_data",
            )
        return page.items[0].model_copy(update={"context": page.context})

    async def detail_intro(
        self,
        content_id: str,
        content_type_id: ContentType | str,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[IntroInfo]:
        params = self._detail_params(content_id, content_type_id, page_no, num_of_rows)
        return await self._get_page("detailIntro2", params, _intro_info)

    async def detail_info(
        self,
        content_id: str,
        content_type_id: ContentType | str,
        *,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[RepeatInfo]:
        params = self._detail_params(content_id, content_type_id, page_no, num_of_rows)
        return await self._get_page("detailInfo2", params, _repeat_info)

    async def detail_images(
        self,
        content_id: str,
        *,
        image_yn: bool | str | None = True,
        sub_image_yn: bool | str | None = True,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[ImageInfo]:
        if not content_id:
            raise ValueError("content_id must not be empty")
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "contentId": content_id,
            "imageYN": yn(image_yn),
            "subImageYN": yn(sub_image_yn),
        }
        return await self._get_page("detailImage2", params, _image_info)

    async def area_based_sync_list(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        show_flag: str | None = None,
        arrange: Arrange | str | None = Arrange.MODIFIED_WITH_IMAGE,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> Page[TourItem]:
        if show_flag is not None and show_flag not in {"0", "1"}:
            raise ValueError("show_flag must be '0' or '1'")
        params = self._list_params(
            content_type_id=content_type_id,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,
            cat2=cat2,
            cat3=cat3,
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
            arrange=arrange,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )
        params["showFlag"] = show_flag
        return await self._get_page("areaBasedSyncList2", params, _tour_item)

    async def area_codes(
        self,
        area_code: AreaCode | str | None = None,
        *,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "areaCode": enum_value(area_code)
        }
        return await self._get_page("areaCode2", params, _code_item)

    async def category_codes(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        _validate_category_chain(cat1=cat1, cat2=cat2, cat3=cat3)
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "contentTypeId": enum_value(content_type_id),
            "cat1": cat1,
            "cat2": cat2,
            "cat3": cat3,
        }
        return await self._get_page("categoryCode2", params, _code_item)

    async def legal_dong_codes(
        self,
        *,
        l_dong_regn_cd: str | None = None,
        list_yn: bool | str | None = False,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "lDongRegnCd": l_dong_regn_cd,
            "lDongListYn": yn(list_yn),
        }
        return await self._get_page("ldongCode2", params, _code_item)

    async def classification_system_codes(
        self,
        *,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        list_yn: bool | str | None = False,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> Page[CodeItem]:
        _validate_lcls_chain(
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
        )
        params = self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "lclsSystm1": lcls_systm1,
            "lclsSystm2": lcls_systm2,
            "lclsSystm3": lcls_systm3,
            "lclsSystmListYn": yn(list_yn),
        }
        return await self._get_page("lclsSystmCode2", params, _code_item)

    def _detail_params(
        self,
        content_id: str,
        content_type_id: ContentType | str,
        page_no: int,
        num_of_rows: int,
    ) -> dict[str, Any]:
        if not content_id:
            raise ValueError("content_id must not be empty")
        return self._page_params(page_no=page_no, num_of_rows=num_of_rows) | {
            "contentId": content_id,
            "contentTypeId": enum_value(content_type_id),
        }

    def _list_params(
        self,
        *,
        content_type_id: ContentType | str | None = None,
        area_code: AreaCode | str | None = None,
        sigungu_code: str | None = None,
        cat1: str | None = None,
        cat2: str | None = None,
        cat3: str | None = None,
        l_dong_regn_cd: str | None = None,
        l_dong_signgu_cd: str | None = None,
        lcls_systm1: str | None = None,
        lcls_systm2: str | None = None,
        lcls_systm3: str | None = None,
        arrange: Arrange | str | None = None,
        modified_time: str | date | datetime | None = None,
        page_no: int = 1,
        num_of_rows: int = 10,
    ) -> dict[str, Any]:
        _validate_page(page_no, num_of_rows)
        _validate_legacy_area(area_code=area_code, sigungu_code=sigungu_code)
        _validate_category_chain(cat1=cat1, cat2=cat2, cat3=cat3)
        _validate_ldong_chain(
            l_dong_regn_cd=l_dong_regn_cd,
            l_dong_signgu_cd=l_dong_signgu_cd,
        )
        _validate_lcls_chain(
            lcls_systm1=lcls_systm1,
            lcls_systm2=lcls_systm2,
            lcls_systm3=lcls_systm3,
        )
        return {
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "arrange": enum_value(arrange),
            "contentTypeId": enum_value(content_type_id),
            "modifiedtime": to_yyyymmdd(modified_time, field="modified_time"),
            "areaCode": enum_value(area_code),
            "sigunguCode": sigungu_code,
            "cat1": cat1,
            "cat2": cat2,
            "cat3": cat3,
            "lDongRegnCd": l_dong_regn_cd,
            "lDongSignguCd": l_dong_signgu_cd,
            "lclsSystm1": lcls_systm1,
            "lclsSystm2": lcls_systm2,
            "lclsSystm3": lcls_systm3,
        }

    def _page_params(self, *, page_no: int, num_of_rows: int) -> dict[str, int]:
        _validate_page(page_no, num_of_rows)
        return {"pageNo": page_no, "numOfRows": num_of_rows}

    async def _get_page(
        self,
        endpoint: str,
        params: Mapping[str, Any],
        parser: Callable[[Mapping[str, Any]], T],
    ) -> Page[T]:
        body = await self._http.get(endpoint, params=params)
        rows = _extract_items(body, endpoint, service_name=self.service_name)
        try:
            parsed = tuple(parser(row) for row in rows)
        except (TypeError, ValueError) as exc:
            raise TourApiParseError(
                f"{endpoint}: failed to parse item: {exc}",
                endpoint=endpoint,
                service_name=self.service_name,
                failure_kind="parse",
            ) from exc
        return Page(
            items=parsed,
            total_count=to_int_or_none(body.get("totalCount")) or len(parsed),
            page_no=to_int_or_none(body.get("pageNo")) or to_int_or_none(params.get("pageNo")) or 1,
            num_of_rows=(
                to_int_or_none(body.get("numOfRows"))
                or to_int_or_none(params.get("numOfRows"))
                or len(parsed)
            ),
            raw=body,
            context=call_context(
                service_name=self.service_name,
                endpoint=endpoint,
                mobile_os=self.mobile_os,
                mobile_app=self.mobile_app,
                params=params,
            ),
        )


TourApiClient = KrTourApiClient
AsyncTourApiClient = AsyncKrTourApiClient


def _first_env(names: tuple[str, ...]) -> str | None:
    return resolve_service_key(source=DEFAULT_SERVICE_KEY_SOURCE, env_names=names)


def _service_name_for_language(language: Language | str) -> str:
    try:
        return SERVICE_NAME_BY_LANGUAGE[str(language).lower()]
    except KeyError as exc:
        supported = ", ".join(sorted(SERVICE_NAME_BY_LANGUAGE))
        raise ValueError(f"unsupported language {language!r}; supported: {supported}") from exc


def _resolve_coordinate(
    *,
    map_x: float | None,
    map_y: float | None,
    coordinate: PlaceCoordinate | tuple[float, float] | Mapping[str, Any] | None,
) -> PlaceCoordinate:
    if coordinate is not None:
        if map_x is not None or map_y is not None:
            raise ValueError("coordinate cannot be combined with map_x or map_y")
        if isinstance(coordinate, PlaceCoordinate):
            return coordinate
        if isinstance(coordinate, tuple):
            return PlaceCoordinate.from_tuple(coordinate)
        if isinstance(coordinate, Mapping):
            coordinate_value = PlaceCoordinate.from_mapping(coordinate)
            if coordinate_value is None:
                raise ValueError(
                    "coordinate mapping requires longitude/latitude, lon/lat, or mapX/mapY"
                )
            return coordinate_value
        raise TypeError("coordinate must be PlaceCoordinate, (latitude, longitude), or mapping")
    if map_x is None or map_y is None:
        raise ValueError("location_based_list requires coordinate or both map_x and map_y")
    return PlaceCoordinate(lat=map_y, lon=map_x)


def _extract_items(
    body: Mapping[str, Any],
    endpoint: str,
    *,
    service_name: str | None = None,
) -> tuple[Mapping[str, Any], ...]:
    items = body.get("items")
    if items in (None, "", []):
        return ()
    item_data: Any
    if isinstance(items, Mapping):
        item_data = items.get("item")
    else:
        item_data = items
    if item_data in (None, "", []):
        return ()
    if isinstance(item_data, Mapping):
        return (item_data,)
    if isinstance(item_data, list) and all(isinstance(item, Mapping) for item in item_data):
        return tuple(item_data)
    raise TourApiParseError(
        f"{endpoint}: response.body.items.item was not an object or list",
        endpoint=endpoint,
        service_name=service_name,
        failure_kind="parse",
    )


def _tour_item(row: Mapping[str, Any]) -> TourItem:
    return TourItem(
        content_id=strip_or_none(row.get("contentid")),
        content_type_id=strip_or_none(row.get("contenttypeid")),
        title=strip_or_none(row.get("title")),
        addr1=strip_or_none(row.get("addr1")),
        addr2=strip_or_none(row.get("addr2")),
        area_code=strip_or_none(row.get("areacode")),
        sigungu_code=strip_or_none(row.get("sigungucode")),
        cat1=strip_or_none(row.get("cat1")),
        cat2=strip_or_none(row.get("cat2")),
        cat3=strip_or_none(row.get("cat3")),
        l_dong_regn_cd=strip_or_none(row.get("lDongRegnCd")),
        l_dong_signgu_cd=strip_or_none(row.get("lDongSignguCd")),
        lcls_systm1=strip_or_none(row.get("lclsSystm1")),
        lcls_systm2=strip_or_none(row.get("lclsSystm2")),
        lcls_systm3=strip_or_none(row.get("lclsSystm3")),
        created_time=parse_tour_datetime(row.get("createdtime")),
        modified_time=parse_tour_datetime(row.get("modifiedtime")),
        tel=strip_or_none(row.get("tel")),
        first_image=strip_or_none(row.get("firstimage")),
        first_image2=strip_or_none(row.get("firstimage2")),
        map_x=to_float_or_none(row.get("mapx")),
        map_y=to_float_or_none(row.get("mapy")),
        map_level=strip_or_none(row.get("mlevel")),
        distance_m=to_float_or_none(row.get("dist")),
        zipcode=strip_or_none(row.get("zipcode")),
        copyright_division_code=strip_or_none(row.get("cpyrhtDivCd")),
        show_flag=strip_or_none(row.get("showflag") or row.get("showFlag")),
        raw=row,
    )


def _tour_detail(row: Mapping[str, Any]) -> TourDetail:
    return TourDetail(
        content_id=strip_or_none(row.get("contentid")),
        content_type_id=strip_or_none(row.get("contenttypeid")),
        title=strip_or_none(row.get("title")),
        homepage=strip_or_none(row.get("homepage")),
        overview=strip_or_none(row.get("overview")),
        tel=strip_or_none(row.get("tel")),
        tel_name=strip_or_none(row.get("telname")),
        addr1=strip_or_none(row.get("addr1")),
        addr2=strip_or_none(row.get("addr2")),
        zipcode=strip_or_none(row.get("zipcode")),
        area_code=strip_or_none(row.get("areacode")),
        sigungu_code=strip_or_none(row.get("sigungucode")),
        cat1=strip_or_none(row.get("cat1")),
        cat2=strip_or_none(row.get("cat2")),
        cat3=strip_or_none(row.get("cat3")),
        l_dong_regn_cd=strip_or_none(row.get("lDongRegnCd")),
        l_dong_signgu_cd=strip_or_none(row.get("lDongSignguCd")),
        lcls_systm1=strip_or_none(row.get("lclsSystm1")),
        lcls_systm2=strip_or_none(row.get("lclsSystm2")),
        lcls_systm3=strip_or_none(row.get("lclsSystm3")),
        first_image=strip_or_none(row.get("firstimage")),
        first_image2=strip_or_none(row.get("firstimage2")),
        map_x=to_float_or_none(row.get("mapx")),
        map_y=to_float_or_none(row.get("mapy")),
        map_level=strip_or_none(row.get("mlevel")),
        created_time=parse_tour_datetime(row.get("createdtime")),
        modified_time=parse_tour_datetime(row.get("modifiedtime")),
        copyright_division_code=strip_or_none(row.get("cpyrhtDivCd")),
        raw=row,
    )


def _code_item(row: Mapping[str, Any]) -> CodeItem:
    return CodeItem(
        code=strip_or_none(
            row.get("code")
            or row.get("lDongRegnCd")
            or row.get("lDongSignguCd")
            or row.get("lclsSystm1Cd")
            or row.get("lclsSystm2Cd")
            or row.get("lclsSystm3Cd")
        ),
        name=strip_or_none(
            row.get("name")
            or row.get("lDongRegnNm")
            or row.get("lDongSignguNm")
            or row.get("lclsSystm1Nm")
            or row.get("lclsSystm2Nm")
            or row.get("lclsSystm3Nm")
        ),
        rnum=to_int_or_none(row.get("rnum")),
        raw=row,
    )


def _intro_info(row: Mapping[str, Any]) -> IntroInfo:
    return IntroInfo(
        content_id=strip_or_none(row.get("contentid")),
        content_type_id=strip_or_none(row.get("contenttypeid")),
        raw=row,
    )


def _repeat_info(row: Mapping[str, Any]) -> RepeatInfo:
    return RepeatInfo(
        content_id=strip_or_none(row.get("contentid")),
        content_type_id=strip_or_none(row.get("contenttypeid")),
        serial_num=strip_or_none(row.get("serialnum")),
        info_name=strip_or_none(row.get("infoname")),
        info_text=strip_or_none(row.get("infotext")),
        field_group=strip_or_none(row.get("fldgubun")),
        sub_name=strip_or_none(row.get("subname")),
        sub_detail_overview=strip_or_none(row.get("subdetailoverview")),
        sub_detail_img=strip_or_none(row.get("subdetailimg")),
        raw=row,
    )


def _image_info(row: Mapping[str, Any]) -> ImageInfo:
    return ImageInfo(
        content_id=strip_or_none(row.get("contentid")),
        serial_num=strip_or_none(row.get("serialnum")),
        image_name=strip_or_none(row.get("imgname")),
        origin_img_url=strip_or_none(row.get("originimgurl")),
        small_image_url=strip_or_none(row.get("smallimageurl")),
        copyright_division_code=strip_or_none(row.get("cpyrhtDivCd")),
        raw=row,
    )


def _validate_page(page_no: int, num_of_rows: int) -> None:
    if page_no < 1:
        raise ValueError("page_no must be >= 1")
    if not 1 <= num_of_rows <= 1000:
        raise ValueError("num_of_rows must be between 1 and 1000")


def _validate_legacy_area(*, area_code: AreaCode | str | None, sigungu_code: str | None) -> None:
    if sigungu_code and not area_code:
        raise TourApiRequestError("sigungu_code requires area_code")


def _validate_category_chain(
    *,
    cat1: str | None,
    cat2: str | None,
    cat3: str | None,
) -> None:
    if cat2 and not cat1:
        raise TourApiRequestError("cat2 requires cat1")
    if cat3 and (not cat1 or not cat2):
        raise TourApiRequestError("cat3 requires cat1 and cat2")


def _validate_ldong_chain(
    *,
    l_dong_regn_cd: str | None,
    l_dong_signgu_cd: str | None,
) -> None:
    if l_dong_signgu_cd and not l_dong_regn_cd:
        raise TourApiRequestError("l_dong_signgu_cd requires l_dong_regn_cd")


def _validate_lcls_chain(
    *,
    lcls_systm1: str | None,
    lcls_systm2: str | None,
    lcls_systm3: str | None,
) -> None:
    if lcls_systm2 and not lcls_systm1:
        raise TourApiRequestError("lcls_systm2 requires lcls_systm1")
    if lcls_systm3 and (not lcls_systm1 or not lcls_systm2):
        raise TourApiRequestError("lcls_systm3 requires lcls_systm1 and lcls_systm2")
