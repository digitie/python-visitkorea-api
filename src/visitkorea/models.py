"""Pydantic models returned by the public client."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Generic, TypeAlias, TypeVar

from kraddr.base import PlaceCoordinate
from pydantic import BaseModel, ConfigDict, Field

RawRecord = Mapping[str, Any]
T = TypeVar("T")


class TourApiModel(BaseModel):
    """Base class for immutable public TourAPI models."""

    model_config = ConfigDict(frozen=True)


Wgs84Coordinate: TypeAlias = PlaceCoordinate


class TourApiCallContext(TourApiModel):
    """Metadata describing the TourAPI call that produced a response."""

    service_name: str | None = None
    endpoint: str | None = None
    request_params: RawRecord = Field(default_factory=dict)
    collected_at: datetime | None = None


class Page(TourApiModel, Generic[T]):
    """A paginated TourAPI response."""

    items: tuple[T, ...]
    total_count: int
    page_no: int
    num_of_rows: int
    raw: RawRecord = Field(repr=False)
    context: TourApiCallContext = Field(default_factory=TourApiCallContext)

    @property
    def is_empty(self) -> bool:
        return not self.items

    @property
    def has_next_page(self) -> bool:
        if self.num_of_rows <= 0:
            return False
        return self.page_no * self.num_of_rows < self.total_count

    @property
    def next_page_no(self) -> int | None:
        if not self.has_next_page:
            return None
        return self.page_no + 1

    @property
    def service_name(self) -> str | None:
        return self.context.service_name

    @property
    def endpoint(self) -> str | None:
        return self.context.endpoint

    @property
    def request_params(self) -> RawRecord:
        return self.context.request_params

    @property
    def collected_at(self) -> datetime | None:
        return self.context.collected_at


class TourItem(TourApiModel):
    """Common list/search item from TourAPI."""

    content_id: str | None
    content_type_id: str | None
    title: str | None
    addr1: str | None
    addr2: str | None
    area_code: str | None
    sigungu_code: str | None
    cat1: str | None
    cat2: str | None
    cat3: str | None
    l_dong_regn_cd: str | None
    l_dong_signgu_cd: str | None
    lcls_systm1: str | None
    lcls_systm2: str | None
    lcls_systm3: str | None
    created_time: datetime | None
    modified_time: datetime | None
    tel: str | None
    first_image: str | None
    first_image2: str | None
    map_x: float | None
    map_y: float | None
    map_level: str | None
    distance_m: float | None
    zipcode: str | None
    copyright_division_code: str | None
    show_flag: str | None
    raw: RawRecord = Field(repr=False)

    @property
    def coordinate(self) -> PlaceCoordinate | None:
        """Return standardized WGS84 coordinates when both axes are present."""

        if self.map_x is None or self.map_y is None:
            return None
        return PlaceCoordinate(lat=self.map_y, lon=self.map_x)


class RelatedTourItem(TourApiModel):
    """Related-tour record from TarRlteTarService1.

    `areaCd` and `signguCd` are TourAPI region codes for this service, not legal-dong
    codes. Legal-dong code fields use names such as `lDongRegnCd` in other TourAPI
    services.
    """

    baseYm: str | None
    tAtsCd: str | None
    tAtsNm: str | None
    areaCd: str | None
    areaNm: str | None
    signguCd: str | None
    signguNm: str | None
    rlteTatsCd: str | None
    rlteTatsNm: str | None
    rlteRegnCd: str | None
    rlteRegnNm: str | None
    rlteSignguCd: str | None
    rlteSignguNm: str | None
    rlteCtgryLclsNm: str | None
    rlteCtgryMclsNm: str | None
    rlteCtgrySclsNm: str | None
    rlteRank: str | None
    raw: RawRecord = Field(repr=False)


class TourDetail(TourApiModel):
    """Common detail information for one content item."""

    content_id: str | None
    content_type_id: str | None
    title: str | None
    homepage: str | None
    overview: str | None
    tel: str | None
    tel_name: str | None
    addr1: str | None
    addr2: str | None
    zipcode: str | None
    area_code: str | None
    sigungu_code: str | None
    cat1: str | None
    cat2: str | None
    cat3: str | None
    l_dong_regn_cd: str | None
    l_dong_signgu_cd: str | None
    lcls_systm1: str | None
    lcls_systm2: str | None
    lcls_systm3: str | None
    first_image: str | None
    first_image2: str | None
    map_x: float | None
    map_y: float | None
    map_level: str | None
    created_time: datetime | None
    modified_time: datetime | None
    copyright_division_code: str | None
    raw: RawRecord = Field(repr=False)
    context: TourApiCallContext = Field(default_factory=TourApiCallContext)

    @property
    def coordinate(self) -> PlaceCoordinate | None:
        """Return standardized WGS84 coordinates when both axes are present."""

        if self.map_x is None or self.map_y is None:
            return None
        return PlaceCoordinate(lat=self.map_y, lon=self.map_x)


class CodeItem(TourApiModel):
    """Code lookup item for area, category, legal dong, or classification codes."""

    code: str | None
    name: str | None
    rnum: int | None
    raw: RawRecord = Field(repr=False)


_INTRO_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "info_center": (
        "infocenter",
        "infocenterculture",
        "infocenterleports",
        "infocenterlodging",
        "infocentershopping",
        "infocenterfood",
        "infocentertourcourse",
    ),
    "use_time": (
        "usetime",
        "usetimeculture",
        "usetimeleports",
        "usetimefestival",
        "opentime",
        "opentimefood",
        "playtime",
    ),
    "rest_date": (
        "restdate",
        "restdateculture",
        "restdateleports",
        "restdateshopping",
        "restdatefood",
    ),
    "parking_info": (
        "parking",
        "parkingculture",
        "parkingleports",
        "parkinglodging",
        "parkingshopping",
        "parkingfood",
    ),
    "use_fee": ("usefee", "usefeeleports"),
    "pet_allowed": (
        "chkpet",
        "chkpetculture",
        "chkpetleports",
        "chkpetshopping",
    ),
}


class IntroInfo(TourApiModel):
    """Introduction detail record. The field set depends on content_type_id.

    Content-type-specific fields stay in `raw`. The convenience properties below read
    the documented per-type aliases from `raw`, returning the first present value or
    `None`, so an unknown content type simply yields `None` without losing any data.
    """

    content_id: str | None
    content_type_id: str | None
    raw: RawRecord = Field(repr=False)

    def _first(self, group: str) -> str | None:
        for name in _INTRO_FIELD_ALIASES[group]:
            value = self.raw.get(name)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @property
    def info_center(self) -> str | None:
        """Information/contact center text for the content's type."""

        return self._first("info_center")

    @property
    def use_time(self) -> str | None:
        """Operating/use hours or play time for the content's type."""

        return self._first("use_time")

    @property
    def rest_date(self) -> str | None:
        """Closed/rest day text for the content's type."""

        return self._first("rest_date")

    @property
    def parking_info(self) -> str | None:
        """Parking availability text for the content's type."""

        return self._first("parking_info")

    @property
    def use_fee(self) -> str | None:
        """Admission/use fee text for the content's type."""

        return self._first("use_fee")

    @property
    def pet_allowed(self) -> str | None:
        """Pet-allowed text for the content's type."""

        return self._first("pet_allowed")


class PetTourInfo(TourApiModel):
    """Pet-companion detail record from detailPetTour2.

    The typed fields below use the documented detailPetTour2 parameter names. Any
    field not modeled here is preserved in `raw`.
    """

    content_id: str | None
    content_type_id: str | None
    pet_companion_type: str | None
    pet_companion_possible: str | None
    pet_companion_need: str | None
    accident_risk: str | None
    related_facility_etc: str | None
    related_furnished_items: str | None
    related_rental_items: str | None
    related_purchase_items: str | None
    etc_companion_info: str | None
    raw: RawRecord = Field(repr=False)


class RepeatInfo(TourApiModel):
    """Repeated detail record such as course stops or facility sub-items."""

    content_id: str | None
    content_type_id: str | None
    serial_num: str | None
    info_name: str | None
    info_text: str | None
    field_group: str | None
    sub_name: str | None
    sub_detail_overview: str | None
    sub_detail_img: str | None
    raw: RawRecord = Field(repr=False)


class ImageInfo(TourApiModel):
    """Image metadata returned by detailImage2."""

    content_id: str | None
    serial_num: str | None
    image_name: str | None
    origin_img_url: str | None
    small_image_url: str | None
    copyright_division_code: str | None
    raw: RawRecord = Field(repr=False)
