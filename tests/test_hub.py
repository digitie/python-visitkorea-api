from __future__ import annotations

import pytest
from kraddr.base import PlaceCoordinate
from pydantic import ValidationError

from visitkorea import (
    SERVICE_DEFINITIONS,
    RelatedTourItem,
    RelatedTourServiceClient,
    TourApiHubClient,
    get_api_catalog,
    get_service_catalog,
    service_key_env_names,
)
from visitkorea.exceptions import TourApiRequestError

from .conftest import FakeResponse, FakeSession, tour_payload

EXPECTED_SERVICE_KEYS = {
    "area_demand_strength",
    "area_diversity",
    "area_resource_demand",
    "chs",
    "cht",
    "datalab",
    "durunubi",
    "employment",
    "eng",
    "fre",
    "ger",
    "gocamping",
    "green",
    "jpn",
    "kor",
    "local_hub",
    "medical",
    "odii",
    "pet",
    "photo_award",
    "photo_gallery",
    "related_tour",
    "rus",
    "spn",
    "tats_concentration",
    "wellness",
    "with",
}


def sample_related_tour_item() -> dict[str, str]:
    return {
        "baseYm": "202504",
        "tAtsCd": "3dbadaccd57c18ae536e552040025fa8",
        "tAtsNm": "간현관광지",
        "areaCd": "51",
        "areaNm": "강원특별자치도",
        "signguCd": "51130",
        "signguNm": "원주시",
        "rlteTatsCd": "0bfeca2105aa7bf8d83e4622e5da19ec",
        "rlteTatsNm": "뮤지엄산",
        "rlteRegnCd": "51",
        "rlteRegnNm": "강원특별자치도",
        "rlteSignguCd": "51130",
        "rlteSignguNm": "원주시",
        "rlteCtgryLclsNm": "관광지",
        "rlteCtgryMclsNm": "문화관광",
        "rlteCtgrySclsNm": "전시시설",
        "rlteRank": "1",
    }


def test_catalog_contains_all_manual_services():
    keys = {service.key for service in SERVICE_DEFINITIONS}

    assert len(SERVICE_DEFINITIONS) == 27
    assert keys == EXPECTED_SERVICE_KEYS
    assert sum(len(service.operations) for service in SERVICE_DEFINITIONS) == 211
    assert all(
        service.manual_url.startswith("https://api.visitkorea.or.kr/")
        for service in SERVICE_DEFINITIONS
    )


def test_api_catalog_rows_include_dataset_name_and_key_links():
    rows = get_api_catalog()
    kor_keyword = next(
        row
        for row in rows
        if row["service_id"] == "kor" and row["operation"] == "searchKeyword2"
    )

    assert len(rows) == 211
    assert kor_keyword["dataset_name"] == "한국관광공사_국문 관광정보 서비스"
    assert kor_keyword["operation_alias"] == "search_keyword"
    assert kor_keyword["data_source"] == "data.go.kr"
    assert kor_keyword["catalog_source"] == "api.visitkorea.or.kr"
    assert kor_keyword["service_key_source"] == "data.go.kr"
    assert kor_keyword["service_key_apply_url"].startswith("https://www.data.go.kr/")
    assert kor_keyword["manual_url"].startswith("https://api.visitkorea.or.kr/")
    assert "KTO_DATA_GO_KR_SERVICE_KEY" in kor_keyword["service_key_env_names"]

    service_rows = get_service_catalog()
    assert len(service_rows) == 27
    assert service_rows[0]["operation"] is None
    assert service_key_env_names("api.visitkorea")[0] == "VISITKOREA_API_SERVICE_KEY"


def test_all_catalog_operations_are_routable_without_live_api_calls():
    total_operations = sum(len(service.operations) for service in SERVICE_DEFINITIONS)
    session = FakeSession([FakeResponse(tour_payload(None)) for _ in range(total_operations)])
    hub = TourApiHubClient("KEY", session=session)

    for service in SERVICE_DEFINITIONS:
        service_client = hub.service(service.key)
        for operation in service.operations:
            page = service_client.call(operation, page_no=None, num_of_rows=None)

            assert page.items == ()
            call = session.calls[-1]
            assert call["url"].endswith(f"/{service.service_name}/{operation}")
            assert call["params"]["serviceKey"] == "KEY"
            assert call["params"]["MobileOS"] == "ETC"
            assert call["params"]["MobileApp"] == "visitkorea"
            assert call["params"]["_type"] == "json"

    assert len(session.calls) == total_operations


def test_hub_from_env_uses_fallback_names(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("KTO_SERVICE_KEY", raising=False)
    monkeypatch.setenv("TOURAPI_SERVICE_KEY", "ENVKEY")

    hub = TourApiHubClient.from_env(session=FakeSession([]))

    assert hub.service_key == "ENVKEY"


def test_hub_call_by_service_key_and_operation_alias():
    session = FakeSession([FakeResponse(tour_payload({"contentid": "1", "title": "캠핑"}))])
    hub = TourApiHubClient("KEY", session=session)

    page = hub.call("gocamping", "based_list", facltNm="숲")

    assert page.items[0]["title"] == "캠핑"
    call = session.calls[0]
    assert call["url"] == "http://apis.data.go.kr/B551011/GoCamping/basedList"
    assert call["params"]["serviceKey"] == "KEY"
    assert call["params"]["facltNm"] == "숲"
    assert call["params"]["pageNo"] == 1
    assert call["params"]["numOfRows"] == 10
    assert page.context.service_name == "GoCamping"
    assert page.context.endpoint == "basedList"
    assert page.context.collected_at is not None
    assert page.context.request_params["MobileOS"] == "ETC"
    assert page.context.request_params["MobileApp"] == "visitkorea"
    assert page.context.request_params["_type"] == "json"
    assert page.context.request_params["facltNm"] == "숲"
    assert "serviceKey" not in page.context.request_params


def test_related_tour_area_based_list_returns_typed_single_item():
    session = FakeSession([FakeResponse(tour_payload(sample_related_tour_item()))])
    hub = TourApiHubClient("KEY", session=session)

    assert isinstance(hub.related_tour, RelatedTourServiceClient)
    assert RelatedTourItem.__doc__ is not None
    assert "not legal-dong" in RelatedTourItem.__doc__

    page = hub.related_tour.area_based_list(
        base_ym="202504",
        area_cd="51",
        signgu_cd="51130",
    )

    assert isinstance(page.items[0], RelatedTourItem)
    item = page.items[0]
    assert item.baseYm == "202504"
    assert item.tAtsCd == "3dbadaccd57c18ae536e552040025fa8"
    assert item.tAtsNm == "간현관광지"
    assert item.areaCd == "51"
    assert item.signguCd == "51130"
    assert item.rlteTatsNm == "뮤지엄산"
    assert item.rlteCtgrySclsNm == "전시시설"
    assert item.rlteRank == "1"
    assert item.raw["rlteTatsCd"] == "0bfeca2105aa7bf8d83e4622e5da19ec"
    assert item.model_dump()["baseYm"] == "202504"
    with pytest.raises(ValidationError, match="frozen"):
        item.rlteRank = "2"  # type: ignore[misc]

    call = session.calls[0]
    assert call["url"].endswith("/TarRlteTarService1/areaBasedList1")
    assert call["params"]["baseYm"] == "202504"
    assert call["params"]["areaCd"] == "51"
    assert call["params"]["signguCd"] == "51130"
    assert page.context.endpoint == "areaBasedList1"
    assert "serviceKey" not in page.context.request_params


def test_related_tour_search_keyword_returns_typed_list_items():
    first = sample_related_tour_item()
    second = sample_related_tour_item() | {
        "rlteTatsCd": "488af5b2e04bba94e29498c4f9a5686d",
        "rlteTatsNm": "원주소금산출렁다리",
        "rlteCtgryMclsNm": "기타관광",
        "rlteRank": "2",
    }
    session = FakeSession([FakeResponse(tour_payload([first, second]))])
    hub = TourApiHubClient("KEY", session=session)

    page = hub.related_tour.search_keyword(
        "뮤지엄산",
        base_ym="202504",
        area_cd="51",
        signgu_cd="51130",
        num_of_rows=2,
    )

    assert [item.rlteTatsNm for item in page.items] == ["뮤지엄산", "원주소금산출렁다리"]
    assert page.items[1].rlteRank == "2"
    assert page.total_count == 2

    call = session.calls[0]
    assert call["url"].endswith("/TarRlteTarService1/searchKeyword1")
    assert call["params"]["keyword"] == "뮤지엄산"
    assert call["params"]["numOfRows"] == 2


def test_related_tour_generic_call_stays_raw_mapping():
    session = FakeSession([FakeResponse(tour_payload(sample_related_tour_item()))])
    hub = TourApiHubClient("KEY", session=session)

    page = hub.call(
        "related_tour",
        "area_based_list",
        baseYm="202504",
        areaCd="51",
        signguCd="51130",
    )

    assert not isinstance(page.items[0], RelatedTourItem)
    assert page.items[0]["rlteTatsNm"] == "뮤지엄산"


def test_hub_dynamic_service_and_operation_methods():
    session = FakeSession([FakeResponse(tour_payload({"galContentId": "A"}))])
    hub = TourApiHubClient("KEY", session=session)

    page = hub.photo.gallery_list(page_no=2, num_of_rows=3, galSearchKeyword="서울")

    assert page.page_no == 1
    assert page.items[0]["galContentId"] == "A"
    assert session.calls[0]["url"].endswith("/PhotoGalleryService1/galleryList1")
    assert session.calls[0]["params"]["pageNo"] == 2
    assert session.calls[0]["params"]["numOfRows"] == 3


def test_hub_pythonic_param_aliases():
    session = FakeSession([FakeResponse(tour_payload({"contentid": "1"}))])
    hub = TourApiHubClient("KEY", session=session)

    hub.kor.detail_common(content_id="1", content_type_id="12")

    params = session.calls[0]["params"]
    assert session.calls[0]["url"].endswith("/KorService2/detailCommon2")
    assert params["contentId"] == "1"
    assert params["contentTypeId"] == "12"


def test_hub_coordinate_alias_expands_to_tourapi_params():
    session = FakeSession(
        [
            FakeResponse(tour_payload({"contentid": "1"})),
            FakeResponse(tour_payload({"contentid": "2"})),
        ]
    )
    hub = TourApiHubClient("KEY", session=session)

    hub.kor.location_based_list(
        coordinate=PlaceCoordinate(lat=37.5796, lon=126.9769),
        radius=1000,
    )
    hub.kor.location_based_list(coordinate={"mapX": 127.0, "mapY": 37.5}, radius=500)

    params = session.calls[0]["params"]
    assert params["mapX"] == 126.9769
    assert params["mapY"] == 37.5796
    assert params["radius"] == 1000
    assert session.calls[1]["params"]["mapX"] == 127.0
    assert session.calls[1]["params"]["mapY"] == 37.5


def test_hub_iter_pages_increments_page_no_for_generic_call():
    session = FakeSession(
        [
            FakeResponse(
                tour_payload(
                    [{"contentid": "1"}, {"contentid": "2"}],
                    page_no=1,
                    num_of_rows=2,
                    total_count=3,
                )
            ),
            FakeResponse(
                tour_payload(
                    {"contentid": "3"},
                    page_no=2,
                    num_of_rows=2,
                    total_count=3,
                )
            ),
        ]
    )
    hub = TourApiHubClient("KEY", session=session)

    pages = list(hub.iter_pages("kor", "area_based_list", num_of_rows=2))

    assert [page.page_no for page in pages] == [1, 2]
    assert [item["contentid"] for page in pages for item in page.items] == ["1", "2", "3"]
    assert [call["params"]["pageNo"] for call in session.calls] == [1, 2]


def test_related_tour_iter_area_based_list_uses_typed_pages_and_guard():
    first = sample_related_tour_item()
    second = sample_related_tour_item() | {"rlteRank": "2", "rlteTatsNm": "원주소금산출렁다리"}
    session = FakeSession(
        [
            FakeResponse(
                tour_payload(first, page_no=1, num_of_rows=1, total_count=2),
            ),
            FakeResponse(
                tour_payload(second, page_no=2, num_of_rows=1, total_count=2),
            ),
        ]
    )
    hub = TourApiHubClient("KEY", session=session)

    pages = list(
        hub.related_tour.iter_area_based_list(
            base_ym="202504",
            area_cd="51",
            signgu_cd="51130",
            num_of_rows=1,
            max_pages=2,
        )
    )

    assert [page.page_no for page in pages] == [1, 2]
    assert all(isinstance(page.items[0], RelatedTourItem) for page in pages)
    assert [page.items[0].rlteRank for page in pages] == ["1", "2"]
    assert [call["params"]["pageNo"] for call in session.calls] == [1, 2]


def test_hub_unknown_service_and_operation_errors():
    hub = TourApiHubClient("KEY", session=FakeSession([]))

    with pytest.raises(TourApiRequestError, match="unknown TourAPI service"):
        hub.service("missing")
    with pytest.raises(TourApiRequestError, match="unknown operation"):
        hub.service("kor").call("missing")
    with pytest.raises(AttributeError):
        _ = hub.missing
    with pytest.raises(AttributeError):
        _ = hub.kor.missing
