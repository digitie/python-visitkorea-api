"""Operation descriptions and form-oriented parameter metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

from .enums import AreaCode, Arrange, ContentType
from .exceptions import TourApiRequestError
from .services import SERVICE_BY_KEY, SERVICE_DEFINITIONS

ParameterKind = Literal["text", "number", "date", "month", "enum", "boolean", "coordinate"]


@dataclass(frozen=True, slots=True)
class ParameterOption:
    """One human-readable option for a form parameter."""

    value: str
    label: str


@dataclass(frozen=True, slots=True)
class OperationParameter:
    """Metadata for one pythonic operation parameter."""

    name: str
    api_name: str
    label: str
    kind: ParameterKind = "text"
    description: str = ""
    required: bool = False
    default: str | int | float | bool | None = None
    options: tuple[ParameterOption, ...] = ()
    min_value: int | float | None = None
    max_value: int | float | None = None
    placeholder: str | None = None


@dataclass(frozen=True, slots=True)
class OperationSchema:
    """UI-friendly operation description and parameter list."""

    service_id: str
    service_name: str
    operation: str
    pythonic_name: str
    summary: str
    details: str
    parameters: tuple[OperationParameter, ...]


CONTENT_TYPE_OPTIONS: Final = tuple(
    ParameterOption(
        value=str(item.value),
        label=f"{item.name.replace('_', ' ').title()} ({item.value})",
    )
    for item in ContentType
)
AREA_CODE_OPTIONS: Final = tuple(
    ParameterOption(
        value=str(item.value),
        label=f"{item.name.replace('_', ' ').title()} ({item.value})",
    )
    for item in AreaCode
)
ARRANGE_OPTIONS: Final = (
    ParameterOption(Arrange.TITLE.value, "Title (A)"),
    ParameterOption(Arrange.MODIFIED.value, "Modified date (C)"),
    ParameterOption(Arrange.CREATED.value, "Created date (D)"),
    ParameterOption(Arrange.DISTANCE.value, "Distance (E)"),
    ParameterOption(Arrange.TITLE_WITH_IMAGE.value, "Title with image (O)"),
    ParameterOption(Arrange.MODIFIED_WITH_IMAGE.value, "Modified date with image (Q)"),
    ParameterOption(Arrange.CREATED_WITH_IMAGE.value, "Created date with image (R)"),
    ParameterOption(Arrange.DISTANCE_WITH_IMAGE.value, "Distance with image (S)"),
)
SHOW_FLAG_OPTIONS: Final = (
    ParameterOption("1", "Visible or active item (1)"),
    ParameterOption("0", "Hidden or deleted item (0)"),
)


def get_operation_schema(service_id: str, operation: str) -> OperationSchema:
    """Return a human-readable schema for one service operation."""

    service = SERVICE_BY_KEY.get(service_id.lower())
    if service is None:
        known = ", ".join(service.key for service in SERVICE_DEFINITIONS)
        raise TourApiRequestError(f"unknown TourAPI service {service_id!r}; known: {known}")
    endpoint = _resolve_operation(operation, service.operations)
    family = _operation_family(service.key, endpoint)
    summary, details = _operation_copy(service.key, endpoint, family)
    return OperationSchema(
        service_id=service.key,
        service_name=service.service_name,
        operation=endpoint,
        pythonic_name=_snake_case(endpoint),
        summary=summary,
        details=details,
        parameters=_parameters_for_operation(service.key, endpoint, family),
    )


def get_operation_parameters(service_id: str, operation: str) -> tuple[OperationParameter, ...]:
    """Return form parameters for one service operation."""

    return get_operation_schema(service_id, operation).parameters


def _resolve_operation(operation: str, operations: tuple[str, ...]) -> str:
    if operation in operations:
        return operation
    normalized = operation.lower()
    aliases = {_snake_case(item): item for item in operations}
    aliases.update({item.lower(): item for item in operations})
    try:
        return aliases[normalized]
    except KeyError as exc:
        known = ", ".join(sorted(aliases))
        raise TourApiRequestError(
            f"unknown operation {operation!r}; known aliases: {known}"
        ) from exc


def _operation_family(service_id: str, operation: str) -> str:
    lowered = operation.lower()
    if service_id == "related_tour":
        return "related_keyword" if "search" in lowered else "related_area"
    if lowered.startswith("areacode"):
        return "area_code"
    if lowered.startswith("categorycode"):
        return "category_code"
    if lowered.startswith("ldongcode"):
        return "legal_dong_code"
    if lowered.startswith("lclssystmcode"):
        return "classification_code"
    if "locationbased" in lowered or "themelocationbased" in lowered:
        return "location_list"
    if "searchfestival" in lowered:
        return "festival_search"
    if "searchstay" in lowered:
        return "stay_search"
    search_list_operations = {"searchlist", "themesearchlist", "storysearchlist"}
    if "searchkeyword" in lowered or lowered in search_list_operations:
        return "keyword_search"
    if lowered.startswith("gallerysearch"):
        return "gallery_search"
    if "detailimage" in lowered or lowered == "imagelist":
        return "image_detail"
    if "detailintro" in lowered:
        return "intro_detail"
    if "detailpettour" in lowered:
        return "pet_detail"
    if "detailinfo" in lowered or "detailmdcltursm" in lowered:
        return "structured_detail"
    if "detailcommon" in lowered or lowered.startswith("gallerydetail"):
        return "common_detail"
    if "sync" in lowered:
        return "sync_list"
    if "areabased" in lowered or lowered in {"basedlist", "themebasedlist", "storybasedlist"}:
        return "area_list"
    if "phokoawrd" in lowered:
        return "award_list"
    if "visitrdd" in lowered:
        return "visitor_data"
    if "course" in lowered or "route" in lowered:
        return "course_list"
    if "empmn" in lowered:
        return "employment"
    if "tatscnctr" in lowered:
        return "concentration"
    if lowered.startswith("area"):
        return "regional_analytics"
    return "generic"


def _operation_copy(
    service_id: str,
    operation: str,
    family: str,
) -> tuple[str, str]:
    if family == "area_code":
        return (
            "Region code lookup.",
            "Use this before regional list searches. Leave area_code empty for top-level "
            "regions, or pass an area_code to fetch sigungu codes below it.",
        )
    if family == "category_code":
        return (
            "Tour category code lookup.",
            "Fetch cat1/cat2/cat3 category codes. Select a content type first when the "
            "category tree differs by content type.",
        )
    if family == "legal_dong_code":
        return (
            "Legal-dong code lookup.",
            "Fetch legal administrative region codes. Use l_dong_regn_cd first, then "
            "l_dong_signgu_cd in downstream list operations.",
        )
    if family == "classification_code":
        return (
            "TourAPI classification-system code lookup.",
            "Fetch the lcls_systm hierarchy used by newer TourAPI list endpoints.",
        )
    if family == "location_list":
        return (
            "Nearby item search around a WGS84 coordinate.",
            "Enter longitude/latitude and a radius in meters. The UI sends pythonic "
            "coordinate data and the client expands it to mapX/mapY.",
        )
    if family == "festival_search":
        return (
            "Festival and event search by event date.",
            "event_start_date is required. Optional area and classification filters narrow "
            "the event list.",
        )
    if family == "keyword_search":
        return (
            "Keyword search.",
            "Search by a human keyword, then optionally narrow by content type, region, "
            "category, legal-dong, or classification filters.",
        )
    if family == "gallery_search":
        return (
            "Photo gallery keyword search.",
            "Search KTO tourism photo-gallery items by a gallery keyword.",
        )
    if family == "stay_search":
        return (
            "Accommodation list search.",
            "Fetch lodging records with optional region and classification filters.",
        )
    if family == "common_detail":
        return (
            "Common detail lookup for one content item.",
            "Use content_id from a list/search response to retrieve shared title, address, "
            "overview, image, and coordinate fields.",
        )
    if family == "intro_detail":
        return (
            "Intro-detail lookup for one content item.",
            "Use content_id and content_type_id to fetch content-type-specific intro fields.",
        )
    if family == "structured_detail":
        return (
            "Structured detail lookup.",
            "Fetch repeat/detail fields for one content item. The returned raw fields vary "
            "by content type and service.",
        )
    if family == "pet_detail":
        return (
            "Pet-companion detail lookup.",
            "Use content_id to fetch pet-companion travel fields. detailPetTour2 only needs "
            "the content ID and does not take a content type.",
        )
    if family == "image_detail":
        return (
            "Image metadata lookup.",
            "Fetch image URLs for one content item. image_yn and sub_image_yn are exposed "
            "as boolean form controls where supported.",
        )
    if family == "sync_list":
        return (
            "Synchronization list.",
            "Fetch records intended for incremental synchronization. Use show_flag when "
            "the service exposes active/deleted item state.",
        )
    if family == "related_area":
        return (
            "Related tourist-attraction list by TourAPI region code.",
            "Use base_ym plus area_cd/signgu_cd from this service's TourAPI region-code "
            "system. These are not legal-dong codes.",
        )
    if family == "related_keyword":
        return (
            "Related tourist-attraction keyword search.",
            "Search related attractions inside a base month and TourAPI region-code scope. "
            "area_cd and signgu_cd are not legal-dong codes.",
        )
    if family == "visitor_data":
        return (
            "Tourism visitor analytics.",
            "Fetch daily visitor-statistics style records. Add source-specific filters in "
            "the additional pythonic parameter fields when needed.",
        )
    if family == "course_list":
        return (
            "Route or course list.",
            "Fetch course-style records such as walking, cycling, or thematic routes.",
        )
    if family == "employment":
        return (
            "Tourism employment information.",
            "Fetch job-list, detail, or synchronization records from the tourism employment "
            "service.",
        )
    if family == "concentration":
        return (
            "Tourist-attraction concentration forecast.",
            "Fetch attraction crowding/concentration trend and forecast records.",
        )
    if family == "regional_analytics":
        return (
            "Regional tourism analytics.",
            "Fetch regional demand, diversity, resource-demand, or related analytic metrics.",
        )
    if family == "award_list":
        return (
            "Tourism photo-award list.",
            "Fetch KTO photo-award records and optional legal-dong filters.",
        )
    if family == "area_list":
        return (
            "Area-based list search.",
            "Fetch records by area, content type, category, legal-dong, and classification "
            "filters.",
        )
    return (
        f"{operation} operation.",
        f"Generic operation from the {service_id} dataset. Use the additional pythonic "
        "parameter fields for service-specific inputs not listed in the common form.",
    )


def _parameters_for_operation(
    service_id: str,
    operation: str,
    family: str,
) -> tuple[OperationParameter, ...]:
    if family == "area_code":
        return (_area_code_param(required=False),)
    if family == "category_code":
        return (_content_type_param(required=False), _text("cat1"), _text("cat2"), _text("cat3"))
    if family == "legal_dong_code":
        return (
            _text("l_dong_regn_cd", "lDongRegnCd", "Legal-dong region code"),
            _bool("l_dong_list_yn", "lDongListYn", "Return legal-dong list"),
        )
    if family == "classification_code":
        return (
            _text("lcls_systm1", "lclsSystm1", "Classification level 1"),
            _text("lcls_systm2", "lclsSystm2", "Classification level 2"),
            _text("lcls_systm3", "lclsSystm3", "Classification level 3"),
            _bool("lcls_systm_list_yn", "lclsSystmListYn", "Return classification list"),
        )
    if family == "location_list":
        return (
            _coordinate(required=True),
            _number(
                "radius",
                "radius",
                "Radius in meters",
                required=True,
                minimum=1,
                maximum=20000,
            ),
            _content_type_param(required=False),
            *_classification_filters(include_area=False),
            _arrange(default=Arrange.DISTANCE.value),
            _date("modified_time", "modifiedtime", "Modified date"),
        )
    if family == "festival_search":
        return (
            _date("event_start_date", "eventStartDate", "Event start date", required=True),
            _date("event_end_date", "eventEndDate", "Event end date"),
            *_classification_filters(include_content_type=False),
            _arrange(default=Arrange.MODIFIED_WITH_IMAGE.value),
            _date("modified_time", "modifiedtime", "Modified date"),
        )
    if family in {"keyword_search", "gallery_search"}:
        keyword_name = "gallery_search_keyword" if family == "gallery_search" else "keyword"
        api_name = "galSearchKeyword" if family == "gallery_search" else "keyword"
        return (
            _text(keyword_name, api_name, "Keyword", required=True),
            *_classification_filters(),
            _arrange(default=Arrange.MODIFIED_WITH_IMAGE.value),
        )
    if family == "stay_search":
        return (
            *_classification_filters(include_content_type=False),
            _arrange(default=Arrange.MODIFIED_WITH_IMAGE.value),
            _date("modified_time", "modifiedtime", "Modified date"),
        )
    if family in {"common_detail", "pet_detail"}:
        return (_text("content_id", "contentId", "Content ID", required=True),)
    if family in {"intro_detail", "structured_detail"}:
        return (
            _text("content_id", "contentId", "Content ID", required=True),
            _content_type_param(required=operation.lower() in {"detailintro2", "detailinfo2"}),
        )
    if family == "image_detail":
        return (
            _text("content_id", "contentId", "Content ID", required=True),
            _bool("image_yn", "imageYN", "Include representative image", default=True),
            _bool("sub_image_yn", "subImageYN", "Include sub images", default=True),
        )
    if family == "sync_list":
        return (
            *_classification_filters(),
            _show_flag(),
            _arrange(default=Arrange.MODIFIED_WITH_IMAGE.value),
        )
    if family in {"related_area", "related_keyword"}:
        params = [
            _month("base_ym", "baseYm", "Base month", required=True),
            _text("area_cd", "areaCd", "TourAPI area code", required=True),
            _text("signgu_cd", "signguCd", "TourAPI sigungu code", required=True),
        ]
        if family == "related_keyword":
            params.insert(0, _text("keyword", "keyword", "Keyword", required=True))
        return tuple(params)
    if family in {"visitor_data", "regional_analytics", "concentration"}:
        return (
            _month("base_ym", "baseYm", "Base month"),
            _date("base_ymd", "baseYmd", "Base date"),
            _text("area_cd", "areaCd", "TourAPI area code"),
            _text("signgu_cd", "signguCd", "TourAPI sigungu code"),
        )
    if family == "award_list":
        return (
            _text("l_dong_regn_cd", "lDongRegnCd", "Legal-dong region code"),
            _text("l_dong_signgu_cd", "lDongSignguCd", "Legal-dong sigungu code"),
        )
    if family == "employment":
        return (
            _text("content_id", "contentId", "Content ID"),
            _text("keyword", "keyword", "Keyword"),
        )
    if family == "course_list":
        return (
            _text("route_idx", "routeIdx", "Route ID"),
            _text("course_idx", "courseIdx", "Course ID"),
        )
    return _generic_parameters(service_id, operation)


def _classification_filters(
    *,
    include_area: bool = True,
    include_content_type: bool = True,
) -> tuple[OperationParameter, ...]:
    params: list[OperationParameter] = []
    if include_content_type:
        params.append(_content_type_param(required=False))
    if include_area:
        params.extend(
            [
                _area_code_param(required=False),
                _text("sigungu_code", "sigunguCode", "Sigungu code"),
            ]
        )
    params.extend(
        [
            _text("cat1"),
            _text("cat2"),
            _text("cat3"),
            _text("l_dong_regn_cd", "lDongRegnCd", "Legal-dong region code"),
            _text("l_dong_signgu_cd", "lDongSignguCd", "Legal-dong sigungu code"),
            _text("lcls_systm1", "lclsSystm1", "Classification level 1"),
            _text("lcls_systm2", "lclsSystm2", "Classification level 2"),
            _text("lcls_systm3", "lclsSystm3", "Classification level 3"),
        ]
    )
    return tuple(params)


def _generic_parameters(service_id: str, operation: str) -> tuple[OperationParameter, ...]:
    lowered = operation.lower()
    params: list[OperationParameter] = []
    if "search" in lowered:
        params.append(_text("keyword", "keyword", "Keyword"))
    if "detail" in lowered:
        params.append(_text("content_id", "contentId", "Content ID"))
    if not params:
        params.append(
            OperationParameter(
                name="service_specific",
                api_name="serviceSpecific",
                label="Service-specific parameters",
                description=(
                    f"{service_id}.{operation} has no common parameter schema yet. "
                    "Use additional pythonic key/value fields below."
                ),
            )
        )
    return tuple(params)


def _content_type_param(*, required: bool) -> OperationParameter:
    return OperationParameter(
        name="content_type_id",
        api_name="contentTypeId",
        label="Content type",
        kind="enum",
        description="TourAPI content type ID.",
        required=required,
        options=CONTENT_TYPE_OPTIONS,
    )


def _area_code_param(*, required: bool) -> OperationParameter:
    return OperationParameter(
        name="area_code",
        api_name="areaCode",
        label="Area code",
        kind="enum",
        description="TourAPI region code.",
        required=required,
        options=AREA_CODE_OPTIONS,
    )


def _arrange(*, default: str | None = None) -> OperationParameter:
    return OperationParameter(
        name="arrange",
        api_name="arrange",
        label="Sort order",
        kind="enum",
        description="TourAPI arrange code.",
        default=default,
        options=ARRANGE_OPTIONS,
    )


def _show_flag() -> OperationParameter:
    return OperationParameter(
        name="show_flag",
        api_name="showFlag",
        label="Show flag",
        kind="enum",
        description="Active/deleted item filter where supported.",
        options=SHOW_FLAG_OPTIONS,
    )


def _text(
    name: str,
    api_name: str | None = None,
    label: str | None = None,
    *,
    required: bool = False,
) -> OperationParameter:
    resolved_api_name = api_name or name
    return OperationParameter(
        name=name,
        api_name=resolved_api_name,
        label=label or name.replace("_", " ").title(),
        description=f"Sent as {resolved_api_name}.",
        required=required,
        placeholder=resolved_api_name,
    )


def _number(
    name: str,
    api_name: str,
    label: str,
    *,
    required: bool = False,
    minimum: int | float | None = None,
    maximum: int | float | None = None,
) -> OperationParameter:
    return OperationParameter(
        name=name,
        api_name=api_name,
        label=label,
        kind="number",
        description=f"Sent as {api_name}.",
        required=required,
        min_value=minimum,
        max_value=maximum,
    )


def _date(
    name: str,
    api_name: str,
    label: str,
    *,
    required: bool = False,
) -> OperationParameter:
    return OperationParameter(
        name=name,
        api_name=api_name,
        label=label,
        kind="date",
        description="Use YYYYMMDD.",
        required=required,
        placeholder="YYYYMMDD",
    )


def _month(
    name: str,
    api_name: str,
    label: str,
    *,
    required: bool = False,
) -> OperationParameter:
    return OperationParameter(
        name=name,
        api_name=api_name,
        label=label,
        kind="month",
        description="Use YYYYMM.",
        required=required,
        placeholder="YYYYMM",
    )


def _bool(
    name: str,
    api_name: str,
    label: str,
    *,
    default: bool | None = None,
) -> OperationParameter:
    return OperationParameter(
        name=name,
        api_name=api_name,
        label=label,
        kind="boolean",
        description=f"Sent as {api_name}=Y/N.",
        default=default,
    )


def _coordinate(*, required: bool) -> OperationParameter:
    return OperationParameter(
        name="coordinate",
        api_name="mapX/mapY",
        label="Coordinate",
        kind="coordinate",
        description="WGS84 longitude/latitude. Sent as mapX/mapY.",
        required=required,
    )


def _snake_case(value: str) -> str:
    cleaned = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    return re.sub(r"_?\d+$", "", cleaned.replace("__", "_").lower())
