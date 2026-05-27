"""Official TourAPI service catalog from api.visitkorea.or.kr manuals."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

from ._auth import DEFAULT_SERVICE_KEY_SOURCE, service_key_env_names


@dataclass(frozen=True, slots=True)
class ServiceDefinition:
    """One OpenAPI service listed on api.visitkorea.or.kr useUtilExercises."""

    key: str
    title: str
    service_name: str
    operations: tuple[str, ...]
    manual_path: str
    apply_url: str
    category: str
    description: str
    aliases: tuple[str, ...] = ()

    @property
    def manual_url(self) -> str:
        return f"https://api.visitkorea.or.kr{self.manual_path}"

    @property
    def dataset_name(self) -> str:
        """Human-readable dataset name shown on data.go.kr."""

        return self.title


SERVICE_DEFINITIONS: Final[tuple[ServiceDefinition, ...]] = (
    ServiceDefinition(
        key="kor",
        title="한국관광공사_국문 관광정보 서비스",
        service_name="KorService2",
        operations=(
            "areaCode2",  # v4.4 매뉴얼 미기재, API는 정상 동작
            "categoryCode2",  # v4.4 매뉴얼 미기재, API는 정상 동작
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "detailPetTour2",
            "ldongCode2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596499508.zip",
        apply_url="https://www.data.go.kr/data/15101578/openapi.do",
        category="국내여행",
        description="국문 관광정보의 코드, 목록, 위치, 키워드, 상세, 이미지 정보를 제공합니다.",
        aliases=("korean", "kor_service", "KorService2"),
    ),
    ServiceDefinition(
        key="eng",
        title="한국관광공사_영문 관광정보서비스",
        service_name="EngService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "ldongCode2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596531873.zip",
        apply_url="https://www.data.go.kr/data/15101753/openapi.do",
        category="국내여행",
        description="영문 관광정보 서비스를 제공합니다.",
        aliases=("english", "en", "EngService2"),
    ),
    ServiceDefinition(
        key="chs",
        title="한국관광공사_중문 간체 관광정보서비스",
        service_name="ChsService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1704160495049.zip",
        apply_url="https://www.data.go.kr/data/15101764/openapi.do",
        category="국내여행",
        description="중문 간체 관광정보 서비스를 제공합니다.",
        aliases=("zh-cn", "simplified_chinese", "ChsService2"),
    ),
    ServiceDefinition(
        key="cht",
        title="한국관광공사_중문 번체 관광정보서비스",
        service_name="ChtService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596423271.zip",
        apply_url="https://www.data.go.kr/data/15101769/openapi.do",
        category="국내여행",
        description="중문 번체 관광정보 서비스를 제공합니다.",
        aliases=("zh-tw", "traditional_chinese", "ChtService2"),
    ),
    ServiceDefinition(
        key="jpn",
        title="한국관광공사_일문 관광정보서비스",
        service_name="JpnService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596480579.zip",
        apply_url="https://www.data.go.kr/data/15101760/openapi.do",
        category="국내여행",
        description="일문 관광정보 서비스를 제공합니다.",
        aliases=("ja", "jp", "japanese", "JpnService2"),
    ),
    ServiceDefinition(
        key="ger",
        title="한국관광공사_독어 관광정보서비스",
        service_name="GerService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596457504.zip",
        apply_url="https://www.data.go.kr/data/15101805/openapi.do",
        category="국내여행",
        description="독어 관광정보 서비스를 제공합니다.",
        aliases=("de", "german", "GerService2"),
    ),
    ServiceDefinition(
        key="fre",
        title="한국관광공사_불어 관광정보서비스",
        service_name="FreService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596408255.zip",
        apply_url="https://www.data.go.kr/data/15101808/openapi.do",
        category="국내여행",
        description="불어 관광정보 서비스를 제공합니다.",
        aliases=("fr", "french", "FreService2"),
    ),
    ServiceDefinition(
        key="spn",
        title="한국관광공사_서어 관광정보서비스",
        service_name="SpnService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596391866.zip",
        apply_url="https://www.data.go.kr/data/15101811/openapi.do",
        category="국내여행",
        description="서어 관광정보 서비스를 제공합니다.",
        aliases=("es", "spanish", "SpnService2"),
    ),
    ServiceDefinition(
        key="rus",
        title="한국관광공사_노어 관광정보서비스",
        service_name="RusService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "searchFestival2",
            "searchStay2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "areaBasedSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596057411.zip",
        apply_url="https://www.data.go.kr/data/15101831/openapi.do",
        category="국내여행",
        description="노어 관광정보 서비스를 제공합니다.",
        aliases=("ru", "russian", "RusService2"),
    ),
    ServiceDefinition(
        key="with",
        title="한국관광공사_무장애 여행 정보",
        service_name="KorWithService2",
        operations=(
            "areaCode2",
            "categoryCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "detailWithTour2",
            "areaBasedSyncList2",
            "ldongCode2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596514908.zip",
        apply_url="https://www.data.go.kr/data/15101897/openapi.do",
        category="국내여행",
        description="장애인, 어르신, 영유아 동반 여행을 위한 무장애 관광정보를 제공합니다.",
        aliases=("accessible", "barrier_free", "KorWithService2"),
    ),
    ServiceDefinition(
        key="green",
        title="한국관광공사_생태 관광 정보",
        service_name="GreenTourService1",
        operations=("areaCode1", "areaBasedList1", "areaBasedSyncList1"),
        manual_path="/upload/manual/guide/file/1704160406003.zip",
        apply_url="https://www.data.go.kr/data/15101908/openapi.do",
        category="국내관광",
        description="친환경관광 및 공정관광 정보를 제공합니다.",
        aliases=("green_tour", "GreenTourService1"),
    ),
    ServiceDefinition(
        key="photo_gallery",
        title="한국관광공사_관광사진 정보",
        service_name="PhotoGalleryService1",
        operations=(
            "galleryList1",
            "gallerySearchList1",
            "galleryDetailList1",
            "gallerySyncDetailList1",
        ),
        manual_path="/upload/manual/guide/file/1704160396374.zip",
        apply_url="https://www.data.go.kr/data/15101914/openapi.do",
        category="국내관광",
        description="관광사진갤러리 사진 제목, 촬영장소, 촬영일 등의 정보를 제공합니다.",
        aliases=("photo", "gallery", "PhotoGalleryService1"),
    ),
    ServiceDefinition(
        key="gocamping",
        title="한국관광공사_고캠핑 정보 조회서비스",
        service_name="GoCamping",
        operations=(
            "basedList",
            "locationBasedList",
            "searchList",
            "imageList",
            "basedSyncList",
        ),
        manual_path="/upload/manual/guide/file/1704160387374.zip",
        apply_url="https://www.data.go.kr/data/15101933/openapi.do",
        category="국내여행",
        description="고캠핑 홈페이지에서 제공하는 캠핑장 정보를 제공합니다.",
        aliases=("camping", "GoCamping"),
    ),
    ServiceDefinition(
        key="odii",
        title="한국관광공사_관광지 오디오 가이드정보",
        service_name="Odii",
        operations=(
            "themeBasedList",
            "themeLocationBasedList",
            "themeSearchList",
            "storyBasedList",
            "storyLocationBasedList",
            "storySearchList",
            "themeBasedSyncList",
            "storyBasedSyncList",
        ),
        manual_path="/upload/manual/guide/file/1720672146251.zip",
        apply_url="https://www.data.go.kr/data/15101971/openapi.do",
        category="국내여행",
        description="오디(odii)의 테마, 스토리, 음성, 대본, 사진 정보를 제공합니다.",
        aliases=("audio", "Odii"),
    ),
    ServiceDefinition(
        key="datalab",
        title="한국관광공사_관광빅데이터 정보서비스",
        service_name="DataLabService",
        operations=("metcoRegnVisitrDDList", "locgoRegnVisitrDDList"),
        manual_path="/upload/manual/guide/file/1704160370032.zip",
        apply_url="https://www.data.go.kr/data/15101972/openapi.do",
        category="국내여행",
        description="한국관광 데이터랩의 광역/기초지자체별 방문자수 정보를 제공합니다.",
        aliases=("bigdata", "DataLabService"),
    ),
    ServiceDefinition(
        key="durunubi",
        title="한국관광공사_두루누비 정보 서비스",
        service_name="Durunubi",
        operations=("routeList", "courseList"),
        manual_path="/upload/manual/guide/file/1704160359411.zip",
        apply_url="https://www.data.go.kr/data/15101974/openapi.do",
        category="국내여행",
        description="걷기, 자전거 등 두루누비 길 정보와 코스 정보를 제공합니다.",
        aliases=("Durunubi",),
    ),
    ServiceDefinition(
        key="employment",
        title="한국관광공사_관광인_채용정보_서비스",
        service_name="tursmService",
        operations=("empmnInfoList", "empmnInfoDetail", "code", "syncList"),
        manual_path="/upload/manual/guide/file/1704160822554.zip",
        apply_url="https://www.data.go.kr/data/15125070/openapi.do",
        category="국내여행",
        description="관광전문인력포털 관광인의 채용정보를 제공합니다.",
        aliases=("job", "jobs", "tursmService"),
    ),
    ServiceDefinition(
        key="tats_concentration",
        title="한국관광공사_관광지 집중률 방문자 추이 예측 정보",
        service_name="TatsCnctrRateService",
        operations=("tatsCnctrRateList", "tatsCnctrRatedList"),
        manual_path="/upload/manual/guide/file/1725501618773.zip",
        apply_url="https://www.data.go.kr/data/15128555/openapi.do",
        category="국내여행",
        description="지역별 관광지별 향후 30일 관광객 집중률 방문자 추이 예측 정보를 제공합니다.",
        aliases=("concentration", "TatsCnctrRateService"),
    ),
    ServiceDefinition(
        key="local_hub",
        title="한국관광공사_기초지자체 중심 관광지 정보",
        service_name="LocgoHubTarService1",
        operations=("areaBasedList1",),
        manual_path="/upload/manual/guide/file/1725501897980.zip",
        apply_url="https://www.data.go.kr/data/15128559/openapi.do",
        category="국내여행",
        description="기초지자체 중심 관광지 100위 정보를 제공합니다.",
        aliases=("hub_tour", "LocgoHubTarService1"),
    ),
    ServiceDefinition(
        key="related_tour",
        title="한국관광공사_관광지별 연관 관광지 정보",
        service_name="TarRlteTarService1",
        operations=("areaBasedList1", "searchKeyword1"),
        manual_path="/upload/manual/guide/file/1725502022236.zip",
        apply_url="https://www.data.go.kr/data/15128560/openapi.do",
        category="국내여행",
        description="중심 관광지와 연결성이 높은 연관 관광지 정보를 제공합니다.",
        aliases=("related", "TarRlteTarService1"),
    ),
    ServiceDefinition(
        key="pet",
        title="한국관광공사_반려동물_동반여행_서비스",
        service_name="KorPetTourService2",
        operations=(
            "ldongCode2",
            "areaBasedList2",
            "locationBasedList2",
            "searchKeyword2",
            "detailCommon2",
            "detailIntro2",
            "detailInfo2",
            "detailImage2",
            "detailPetTour2",
            "petTourSyncList2",
            "lclsSystmCode2",
        ),
        manual_path="/upload/manual/guide/file/1737596366080.zip",
        apply_url="https://www.data.go.kr/data/15135102/openapi.do",
        category="국내여행",
        description="반려동물 동반여행 가능한 관광정보를 제공합니다.",
        aliases=("pet_tour", "KorPetTourService2"),
    ),
    ServiceDefinition(
        key="medical",
        title="한국관광공사_의료관광정보",
        service_name="MdclTursmService",
        operations=(
            "ldongCode",
            "areaBasedList",
            "locationBasedList",
            "searchKeyword",
            "mdclTursmSyncList",
            "detailCommon",
            "detailIntro",
            "detailMdclTursm",
        ),
        manual_path="/upload/manual/guide/file/1725080563660.zip",
        apply_url="https://www.data.go.kr/data/15143913/openapi.do",
        category="국내여행",
        description="국내 의료 관광정보를 제공합니다.",
        aliases=("mdcl", "MdclTursmService"),
    ),
    ServiceDefinition(
        key="wellness",
        title="한국관광공사_웰니스관광정보",
        service_name="WellnessTursmService",
        operations=(
            "ldongCode",
            "areaBasedList",
            "locationBasedList",
            "searchKeyword",
            "wellnessTursmSyncList",
            "detailCommon",
            "detailIntro",
            "detailInfo",
            "detailImage",
        ),
        manual_path="/upload/manual/guide/file/1725080513010.zip",
        apply_url="https://www.data.go.kr/data/15144030/openapi.do",
        category="국내여행",
        description="국내 웰니스 관광정보를 제공합니다.",
        aliases=("WellnessTursmService",),
    ),
    ServiceDefinition(
        key="photo_award",
        title="한국관광공사_관광공모전(사진) 수상작 정보",
        service_name="PhokoAwrdService",
        operations=("ldongCode", "phokoAwrdList", "phokoAwrdSyncList"),
        manual_path="/upload/manual/guide/file/1725092509540.zip",
        apply_url="https://www.data.go.kr/data/15145706/openapi.do",
        category="국내여행",
        description="관광공모전 사진 부문 수상작 정보를 제공합니다.",
        aliases=("award", "phoko", "PhokoAwrdService"),
    ),
    ServiceDefinition(
        key="area_diversity",
        title="한국관광공사_지역별 관광 다양성",
        service_name="AreaTarDivService",
        operations=("areaTouDivList", "areaExpDivList", "areaIntlDivList"),
        manual_path="/upload/manual/guide/file/manual_areaTarDivService.zip",
        apply_url="https://www.data.go.kr/data/15151365/openapi.do",
        category="국내여행",
        description="지역별 관광객, 경험, 국제적 다양성 정보를 제공합니다.",
        aliases=("diversity", "AreaTarDivService"),
    ),
    ServiceDefinition(
        key="area_demand_strength",
        title="한국관광공사_지역별 관광 수요 강도",
        service_name="AreaTarDemDsService",
        operations=("areaTarSjrnDsList", "areaTarExpDsList"),
        manual_path="/upload/manual/guide/file/manual_areaTarDemDsService.zip",
        apply_url="https://www.data.go.kr/data/15151868/openapi.do",
        category="국내여행",
        description="지역별 관광 체류 강도와 소비 강도 정보를 제공합니다.",
        aliases=("demand_strength", "AreaTarDemDsService"),
    ),
    ServiceDefinition(
        key="area_resource_demand",
        title="한국관광공사_지역별 관광 자원 수요",
        service_name="AreaTarResDemService",
        operations=("areaTarSvcDemList", "areaCulResDemList"),
        manual_path="/upload/manual/guide/file/manual_areaTarResDemService.zip",
        apply_url="https://www.data.go.kr/data/15152138/openapi.do",
        category="국내여행",
        description="지역별 관광 서비스 수요와 문화 자원 수요 정보를 제공합니다.",
        aliases=("resource_demand", "AreaTarResDemService"),
    ),
)


SERVICE_BY_KEY: Final[dict[str, ServiceDefinition]] = {
    alias.lower(): service
    for service in SERVICE_DEFINITIONS
    for alias in (service.key, service.service_name, *service.aliases)
}


def get_api_catalog(*, include_operations: bool = True) -> tuple[dict[str, Any], ...]:
    """Return a UI-friendly catalog for every bundled TourAPI dataset.

    Each row includes the human-readable dataset name, service-key application URL,
    manual URL, and operation metadata. The result contains no credentials and can be
    shown directly in a debug UI.
    """

    rows: list[dict[str, Any]] = []
    env_names = service_key_env_names(DEFAULT_SERVICE_KEY_SOURCE)
    for service in SERVICE_DEFINITIONS:
        operations: tuple[str | None, ...] = service.operations if include_operations else (None,)
        for operation in operations:
            rows.append(
                {
                    "service_id": service.key,
                    "dataset_name": service.dataset_name,
                    "service_name": service.service_name,
                    "operation": operation,
                    "operation_alias": _operation_alias(operation) if operation else None,
                    "category": service.category,
                    "description": service.description,
                    "data_source": "data.go.kr",
                    "catalog_source": "api.visitkorea.or.kr",
                    "service_key_source": DEFAULT_SERVICE_KEY_SOURCE,
                    "service_key_env_names": env_names,
                    "service_key_apply_url": service.apply_url,
                    "manual_url": service.manual_url,
                }
            )
    return tuple(rows)


def get_service_catalog() -> tuple[dict[str, Any], ...]:
    """Return one catalog row per dataset instead of one row per operation."""

    return get_api_catalog(include_operations=False)


def _operation_alias(operation: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", operation)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"_?\d+$", "", value.replace("__", "_").lower())
