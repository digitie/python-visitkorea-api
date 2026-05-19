from __future__ import annotations

import asyncio

import pytest

from visitkorea import (
    AreaCode,
    Arrange,
    AsyncKrTourApiClient,
    AsyncTourApiHubClient,
    ContentType,
    KrTourApiClient,
    RelatedTourItem,
)
from visitkorea._http import DEFAULT_USER_AGENT, build_async_session
from visitkorea.exceptions import TourApiRequestError

from .conftest import FakeAsyncSession, FakeResponse, tour_payload
from .test_client import sample_tour_item
from .test_hub import sample_related_tour_item


def test_build_async_session_uses_httpx_user_agent():
    async def run() -> None:
        client = build_async_session(retries=0)
        try:
            assert client.headers["User-Agent"] == DEFAULT_USER_AGENT
        finally:
            await client.aclose()

    asyncio.run(run())


def test_async_typed_client_sends_request_and_parses_page(fake_async_client_factory):
    async def run() -> None:
        client, session = fake_async_client_factory(
            FakeResponse(tour_payload({"code": "1", "name": "서울", "rnum": "1"})),
        )

        page = await client.area_codes(num_of_rows=5)
        await client.aclose()

        assert page.items[0].code == "1"
        assert page.context.endpoint == "areaCode2"
        assert page.context.request_params["numOfRows"] == 5
        assert "serviceKey" not in page.context.request_params
        assert session.calls[0]["url"].endswith("/KorService2/areaCode2")
        assert session.calls[0]["params"]["serviceKey"] == "TEST_KEY"
        assert session.closed is False

    asyncio.run(run())


def test_async_typed_client_iter_pages(fake_async_client_factory):
    async def run() -> None:
        client, session = fake_async_client_factory(
            FakeResponse(
                tour_payload(
                    [{"code": "1", "name": "서울"}, {"code": "2", "name": "인천"}],
                    page_no=1,
                    num_of_rows=2,
                    total_count=3,
                )
            ),
            FakeResponse(
                tour_payload(
                    {"code": "3", "name": "대전"},
                    page_no=2,
                    num_of_rows=2,
                    total_count=3,
                )
            ),
        )

        pages = [page async for page in client.iter_pages(client.area_codes, num_of_rows=2)]

        assert [page.page_no for page in pages] == [1, 2]
        assert [item.code for page in pages for item in page.items] == ["1", "2", "3"]
        assert [call["params"]["pageNo"] for call in session.calls] == [1, 2]

    asyncio.run(run())


def test_async_hub_generic_and_related_tour_helpers():
    async def run() -> None:
        session = FakeAsyncSession(
            [
                FakeResponse(tour_payload({"contentid": "1", "title": "캠핑"})),
                FakeResponse(tour_payload(sample_related_tour_item())),
            ]
        )
        async with AsyncTourApiHubClient("KEY", session=session) as hub:
            page = await hub.call("gocamping", "based_list", facltNm="숲")
            related = await hub.related_tour.area_based_list(
                base_ym="202504",
                area_cd="51",
                signgu_cd="51130",
            )

        assert page.items[0]["title"] == "캠핑"
        assert session.calls[0]["url"].endswith("/GoCamping/basedList")
        assert session.calls[0]["params"]["facltNm"] == "숲"
        assert isinstance(related.items[0], RelatedTourItem)
        assert related.items[0].rlteTatsNm == "뮤지엄산"
        assert session.calls[1]["url"].endswith("/TarRlteTarService1/areaBasedList1")
        assert session.closed is False

    asyncio.run(run())


def test_sync_client_aio_factory_returns_async_client():
    client = KrTourApiClient.aio("KEY", session=FakeAsyncSession([]))

    assert isinstance(client, AsyncKrTourApiClient)


def test_async_typed_client_endpoint_parity():
    async def run() -> None:
        row = sample_tour_item()
        session = FakeAsyncSession(
            [
                FakeResponse(tour_payload(row)),
                FakeResponse(tour_payload(row)),
                FakeResponse(tour_payload(row)),
                FakeResponse(tour_payload(row)),
                FakeResponse(tour_payload(row)),
                FakeResponse(tour_payload(row | {"homepage": "<a>홈</a>", "overview": "설명"})),
                FakeResponse(tour_payload({"contentid": "1", "contenttypeid": "12"})),
                FakeResponse(tour_payload({"contentid": "1", "contenttypeid": "25"})),
                FakeResponse(tour_payload({"contentid": "1", "originimgurl": "https://e.test/a.jpg"})),
                FakeResponse(tour_payload(row | {"showFlag": "1"})),
                FakeResponse(tour_payload({"code": "A", "name": "분류"})),
                FakeResponse(tour_payload({"lDongRegnCd": "11", "lDongRegnNm": "서울특별시"})),
                FakeResponse(tour_payload({"lclsSystm1Cd": "HS", "lclsSystm1Nm": "역사관광"})),
                FakeResponse(tour_payload({"custom": "value"})),
            ]
        )
        client = AsyncKrTourApiClient("KEY", session=session)

        area = await client.area_based_list(area_code=AreaCode.SEOUL, num_of_rows=5)
        location = await client.location_based_list(
            coordinate={"mapX": 126.9, "mapY": 37.5},
            radius=500,
        )
        keyword = await client.search_keyword(
            "궁",
            content_type_id=ContentType.TOURIST_ATTRACTION,
            arrange=Arrange.MODIFIED_WITH_IMAGE,
        )
        festival = await client.search_festival("20260501", event_end_date="20260531")
        stay = await client.search_stay(area_code=AreaCode.SEOUL)
        detail = await client.detail_common("126508")
        intro = await client.detail_intro("1", "12")
        repeat = await client.detail_info("1", "25")
        image = await client.detail_images("1", image_yn=True, sub_image_yn=False)
        sync = await client.area_based_sync_list(show_flag="1", area_code="1", sigungu_code="23")
        category = await client.category_codes(content_type_id="12", cat1="A01")
        legal = await client.legal_dong_codes(list_yn=True)
        lcls = await client.classification_system_codes(list_yn=True)
        raw = await client.raw_endpoint("customEndpoint2", {"foo": "bar"})

        assert area.items[0].title == "경복궁"
        assert location.items[0].coordinate is not None
        assert keyword.context.request_params["keyword"] == "궁"
        assert festival.context.request_params["eventStartDate"] == "20260501"
        assert stay.context.endpoint == "searchStay2"
        assert detail.overview == "설명"
        assert intro.items[0].content_id == "1"
        assert repeat.items[0].content_id == "1"
        assert image.items[0].origin_img_url == "https://e.test/a.jpg"
        assert sync.items[0].show_flag == "1"
        assert category.items[0].code == "A"
        assert legal.items[0].code == "11"
        assert lcls.items[0].code == "HS"
        assert raw.items[0]["custom"] == "value"
        assert [call["params"]["pageNo"] for call in session.calls[:2]] == [1, 1]

    asyncio.run(run())


def test_async_hub_catalog_dynamic_iterators_and_errors():
    async def run() -> None:
        first = sample_related_tour_item()
        second = sample_related_tour_item() | {"rlteRank": "2", "rlteTatsNm": "원주소금산출렁다리"}
        session = FakeAsyncSession(
            [
                FakeResponse(tour_payload({"galContentId": "A"})),
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
                FakeResponse(
                    tour_payload(
                        [{"code": "1", "name": "서울"}, {"code": "2", "name": "인천"}],
                        page_no=1,
                        num_of_rows=2,
                        total_count=3,
                    )
                ),
                FakeResponse(
                    tour_payload(
                        {"code": "3", "name": "대전"},
                        page_no=2,
                        num_of_rows=2,
                        total_count=3,
                    )
                ),
                FakeResponse(tour_payload([first, second])),
                FakeResponse(tour_payload(first, page_no=1, num_of_rows=1, total_count=2)),
                FakeResponse(tour_payload(second, page_no=2, num_of_rows=1, total_count=2)),
            ]
        )
        hub = AsyncTourApiHubClient("KEY", session=session)

        assert hub.services
        assert any(row["service_id"] == "kor" for row in hub.catalog())
        gallery = await hub.photo_gallery.gallery_list(page_no=2, num_of_rows=3)
        pages = [page async for page in hub.iter_pages("kor", "area_based_list", num_of_rows=2)]
        code_pages = [page async for page in hub.kor.iter_pages("area_code", num_of_rows=2)]
        related = await hub.related_tour.search_keyword(
            "뮤지엄산",
            base_ym="202504",
            area_cd="51",
            signgu_cd="51130",
            num_of_rows=2,
        )
        related_pages = [
            page
            async for page in hub.related_tour.iter_search_keyword(
                "뮤지엄산",
                base_ym="202504",
                area_cd="51",
                signgu_cd="51130",
                num_of_rows=1,
                max_pages=2,
            )
        ]

        assert gallery.items[0]["galContentId"] == "A"
        assert [item["contentid"] for page in pages for item in page.items] == ["1", "2", "3"]
        assert [item["code"] for page in code_pages for item in page.items] == ["1", "2", "3"]
        assert [item.rlteTatsNm for item in related.items] == ["뮤지엄산", "원주소금산출렁다리"]
        assert [page.items[0].rlteRank for page in related_pages] == ["1", "2"]

        with pytest.raises(TourApiRequestError):
            hub.service("missing")
        with pytest.raises(AttributeError):
            _ = hub.missing
        with pytest.raises(AttributeError):
            _ = hub.kor.missing

    asyncio.run(run())
