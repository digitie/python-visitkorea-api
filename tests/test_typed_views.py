from __future__ import annotations

import asyncio

import pytest

from visitkorea import (
    AsyncTourApiHubClient,
    DataLabVisitorItem,
    DurunubiCourseItem,
    GoCampingItem,
    MedicalTourItem,
    TourApiHubClient,
)
from visitkorea.exceptions import TourApiRequestError

from .conftest import FakeAsyncSession, FakeResponse, FakeSession, tour_payload


def test_typed_service_view_parses_known_services():
    session = FakeSession(
        [
            FakeResponse(
                tour_payload(
                    {
                        "contentId": "100",
                        "facltNm": "숲속야영장",
                        "doNm": "강원특별자치도",
                        "mapX": "128.39",
                        "mapY": "37.55",
                        "unmodeled": "원문보존",
                    }
                )
            ),
            FakeResponse(tour_payload({"baseYmd": "20260501", "touNum": "1234", "areaNm": "서울"})),
            FakeResponse(tour_payload({"contentid": "9", "title": "의료기관", "mapx": "127.0"})),
        ]
    )
    hub = TourApiHubClient("KEY", session=session)

    camping = hub.gocamping.typed.based_list(facltNm="숲")
    visitors = hub.datalab.typed.call("metcoRegnVisitrDDList", baseYm="202605")
    medical = hub.medical.typed.area_based_list()

    item = camping.items[0]
    assert isinstance(item, GoCampingItem)
    assert item.facility_name == "숲속야영장"
    assert item.do_name == "강원특별자치도"
    assert item.coordinate is not None
    assert item.raw["unmodeled"] == "원문보존"
    assert session.calls[0]["url"].endswith("/GoCamping/basedList")
    assert isinstance(visitors.items[0], DataLabVisitorItem)
    assert visitors.items[0].visitor_count == "1234"
    assert isinstance(medical.items[0], MedicalTourItem)
    assert medical.items[0].title == "의료기관"


def test_typed_service_view_iter_pages_and_unregistered_service():
    session = FakeSession(
        [
            FakeResponse(
                tour_payload(
                    [
                        {"crsIdx": "1", "crsKorNm": "둘레길A"},
                        {"crsIdx": "2", "crsKorNm": "둘레길B"},
                    ],
                    page_no=1,
                    num_of_rows=2,
                    total_count=3,
                )
            ),
            FakeResponse(
                tour_payload(
                    {"crsIdx": "3", "crsKorNm": "둘레길C"},
                    page_no=2,
                    num_of_rows=2,
                    total_count=3,
                )
            ),
        ]
    )
    hub = TourApiHubClient("KEY", session=session)

    pages = list(hub.durunubi.typed.iter_pages("courseList", num_of_rows=2))

    names = [item.name for page in pages for item in page.items]
    assert names == ["둘레길A", "둘레길B", "둘레길C"]
    assert all(isinstance(item, DurunubiCourseItem) for page in pages for item in page.items)
    assert [call["params"]["pageNo"] for call in session.calls] == [1, 2]

    with pytest.raises(TourApiRequestError, match="no typed model"):
        _ = hub.kor.typed


def test_typed_service_view_generic_call_stays_raw():
    session = FakeSession([FakeResponse(tour_payload({"contentId": "1", "facltNm": "캠핑"}))])
    hub = TourApiHubClient("KEY", session=session)

    page = hub.gocamping.based_list(facltNm="숲")

    assert not isinstance(page.items[0], GoCampingItem)
    assert page.items[0]["facltNm"] == "캠핑"


def test_async_typed_service_view():
    async def run() -> None:
        session = FakeAsyncSession(
            [
                FakeResponse(tour_payload({"contentId": "1", "facltNm": "캠핑장"})),
                FakeResponse(
                    tour_payload(
                        [{"contentId": "2", "facltNm": "A"}],
                        page_no=1,
                        num_of_rows=1,
                        total_count=1,
                    )
                ),
            ]
        )
        hub = AsyncTourApiHubClient("KEY", session=session)

        page = await hub.gocamping.typed.based_list(facltNm="숲")
        pages = [p async for p in hub.gocamping.typed.iter_pages("basedList", num_of_rows=1)]

        assert isinstance(page.items[0], GoCampingItem)
        assert page.items[0].facility_name == "캠핑장"
        assert pages[0].items[0].facility_name == "A"

    asyncio.run(run())
