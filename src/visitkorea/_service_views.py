"""Row parsers and typed views that re-type generic Hub pages per service."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from typing import TYPE_CHECKING, Any, cast

from ._convert import strip_or_none, to_float_or_none
from .exceptions import TourApiRequestError
from .models import Page, RawRecord, TourApiModel
from .service_models import (
    DataLabVisitorItem,
    DurunubiCourseItem,
    GoCampingItem,
    MedicalTourItem,
    OdiiItem,
    WellnessTourItem,
)

if TYPE_CHECKING:
    from .hub import AsyncTourApiServiceClient, TourApiServiceClient

ItemParser = Callable[[Mapping[str, Any]], TourApiModel]


def _gocamping_item(row: Mapping[str, Any]) -> GoCampingItem:
    return GoCampingItem(
        content_id=strip_or_none(row.get("contentId")),
        facility_name=strip_or_none(row.get("facltNm")),
        line_intro=strip_or_none(row.get("intro") or row.get("lineIntro")),
        induty=strip_or_none(row.get("induty")),
        do_name=strip_or_none(row.get("doNm")),
        sigungu_name=strip_or_none(row.get("sigunguNm")),
        addr1=strip_or_none(row.get("addr1")),
        addr2=strip_or_none(row.get("addr2")),
        tel=strip_or_none(row.get("tel")),
        homepage=strip_or_none(row.get("homepage")),
        first_image_url=strip_or_none(row.get("firstImageUrl")),
        map_x=to_float_or_none(row.get("mapX")),
        map_y=to_float_or_none(row.get("mapY")),
        raw=row,
    )


def _durunubi_course_item(row: Mapping[str, Any]) -> DurunubiCourseItem:
    return DurunubiCourseItem(
        route_idx=strip_or_none(row.get("routeIdx")),
        course_idx=strip_or_none(row.get("crsIdx")),
        name=strip_or_none(row.get("crsKorNm")),
        distance=strip_or_none(row.get("crsDstnc")),
        required_time=strip_or_none(row.get("crsTotlRti")),
        level=strip_or_none(row.get("crsLevel")),
        summary=strip_or_none(row.get("crsSummary")),
        contents=strip_or_none(row.get("crsContents")),
        sigun=strip_or_none(row.get("sigun")),
        gpx_path=strip_or_none(row.get("gpxpath")),
        raw=row,
    )


def _datalab_visitor_item(row: Mapping[str, Any]) -> DataLabVisitorItem:
    return DataLabVisitorItem(
        base_ymd=strip_or_none(row.get("baseYmd")),
        daywk_name=strip_or_none(row.get("daywkDivNm")),
        area_code=strip_or_none(row.get("areaCode")),
        area_name=strip_or_none(row.get("areaNm")),
        signgu_code=strip_or_none(row.get("signguCode")),
        signgu_name=strip_or_none(row.get("signguNm")),
        tour_division_name=strip_or_none(row.get("touDivNm")),
        visitor_count=strip_or_none(row.get("touNum")),
        raw=row,
    )


def _odii_item(row: Mapping[str, Any]) -> OdiiItem:
    return OdiiItem(
        story_id=strip_or_none(row.get("stid") or row.get("stId")),
        title=strip_or_none(row.get("stTitle") or row.get("audioTitle") or row.get("themaName")),
        theme_id=strip_or_none(row.get("themaId")),
        theme_name=strip_or_none(row.get("themaName")),
        mp3_path=strip_or_none(row.get("mp3path") or row.get("audioPath")),
        script=strip_or_none(row.get("scriptDetail") or row.get("script")),
        image_path=strip_or_none(row.get("imgPath") or row.get("imageUrl")),
        map_x=to_float_or_none(row.get("mapX")),
        map_y=to_float_or_none(row.get("mapY")),
        raw=row,
    )


def _medical_tour_item(row: Mapping[str, Any]) -> MedicalTourItem:
    return MedicalTourItem(
        content_id=strip_or_none(row.get("contentid")),
        content_type_id=strip_or_none(row.get("contenttypeid")),
        title=strip_or_none(row.get("title")),
        addr1=strip_or_none(row.get("addr1")),
        addr2=strip_or_none(row.get("addr2")),
        tel=strip_or_none(row.get("tel")),
        first_image=strip_or_none(row.get("firstimage")),
        map_x=to_float_or_none(row.get("mapx")),
        map_y=to_float_or_none(row.get("mapy")),
        raw=row,
    )


def _wellness_tour_item(row: Mapping[str, Any]) -> WellnessTourItem:
    return WellnessTourItem(
        content_id=strip_or_none(row.get("contentid")),
        content_type_id=strip_or_none(row.get("contenttypeid")),
        title=strip_or_none(row.get("title")),
        addr1=strip_or_none(row.get("addr1")),
        addr2=strip_or_none(row.get("addr2")),
        tel=strip_or_none(row.get("tel")),
        first_image=strip_or_none(row.get("firstimage")),
        map_x=to_float_or_none(row.get("mapx")),
        map_y=to_float_or_none(row.get("mapy")),
        raw=row,
    )


SERVICE_ITEM_PARSERS: dict[str, ItemParser] = {
    "gocamping": _gocamping_item,
    "durunubi": _durunubi_course_item,
    "datalab": _datalab_visitor_item,
    "odii": _odii_item,
    "medical": _medical_tour_item,
    "wellness": _wellness_tour_item,
}


def require_item_parser(service_key: str) -> ItemParser:
    """Return the typed-row parser for a service key, or raise if none is registered."""

    parser = SERVICE_ITEM_PARSERS.get(service_key)
    if parser is None:
        known = ", ".join(sorted(SERVICE_ITEM_PARSERS))
        raise TourApiRequestError(
            f"{service_key}: no typed model is registered; typed services are: {known}"
        )
    return parser


def _retype_page(page: Page[RawRecord], parser: ItemParser) -> Page[TourApiModel]:
    parsed = tuple(parser(row) for row in page.items)
    return cast("Page[TourApiModel]", page.model_copy(update={"items": parsed}))


class TypedServiceView:
    """Generic view that parses one service's raw rows into its typed model."""

    def __init__(self, client: TourApiServiceClient, parser: ItemParser) -> None:
        self._client = client
        self._parser = parser

    @property
    def operations(self) -> tuple[str, ...]:
        return self._client.operations

    def call(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[TourApiModel]:
        page = self._client.call(
            operation, params=params, page_no=page_no, num_of_rows=num_of_rows, **kwargs
        )
        return _retype_page(page, self._parser)

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
    ) -> Iterator[Page[TourApiModel]]:
        for page in self._client.iter_pages(
            operation,
            params=params,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
            **kwargs,
        ):
            yield _retype_page(page, self._parser)

    def __getattr__(self, name: str) -> Callable[..., Page[TourApiModel]]:
        if name.startswith("_"):
            raise AttributeError(name)

        def caller(
            params: Mapping[str, Any] | None = None,
            *,
            page_no: int | None = 1,
            num_of_rows: int | None = 10,
            **kwargs: Any,
        ) -> Page[TourApiModel]:
            return self.call(
                name, params=params, page_no=page_no, num_of_rows=num_of_rows, **kwargs
            )

        return caller


class AsyncTypedServiceView:
    """Async generic view that parses one service's raw rows into its typed model."""

    def __init__(self, client: AsyncTourApiServiceClient, parser: ItemParser) -> None:
        self._client = client
        self._parser = parser

    @property
    def operations(self) -> tuple[str, ...]:
        return self._client.operations

    async def call(
        self,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        page_no: int | None = 1,
        num_of_rows: int | None = 10,
        **kwargs: Any,
    ) -> Page[TourApiModel]:
        page = await self._client.call(
            operation, params=params, page_no=page_no, num_of_rows=num_of_rows, **kwargs
        )
        return _retype_page(page, self._parser)

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
    ) -> AsyncIterator[Page[TourApiModel]]:
        async for page in self._client.iter_pages(
            operation,
            params=params,
            page_no=page_no,
            num_of_rows=num_of_rows,
            max_pages=max_pages,
            max_items=max_items,
            **kwargs,
        ):
            yield _retype_page(page, self._parser)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith("_"):
            raise AttributeError(name)

        async def caller(
            params: Mapping[str, Any] | None = None,
            *,
            page_no: int | None = 1,
            num_of_rows: int | None = 10,
            **kwargs: Any,
        ) -> Page[TourApiModel]:
            return await self.call(
                name, params=params, page_no=page_no, num_of_rows=num_of_rows, **kwargs
            )

        return caller
