from __future__ import annotations

import os
from typing import Any

import pytest

from visitkorea import (
    AsyncTokenBucket,
    ContentType,
    GoCampingItem,
    KrTourApiClient,
    TourApiHubClient,
)
from visitkorea.exceptions import TourApiAuthError, TourApiNoDataError

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("VISITKOREA_RUN_LIVE") != "1", reason="VISITKOREA_RUN_LIVE=1 필요"
    ),
]


def _service_key() -> str:
    key = os.getenv("DATA_GO_KR_SERVICE_KEY")
    if not key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY is not set")
    return key


def _kor_client(**kwargs: Any) -> KrTourApiClient:
    return KrTourApiClient(_service_key(), mobile_app="visitkorea-live-test", timeout=20, **kwargs)


async def test_live_korean_area_codes_returns_tourapi_shape():
    key = _service_key()
    async with KrTourApiClient(
        key,
        mobile_app="visitkorea-live-test",
        timeout=20,
    ) as client:
        page = await client.area_codes(num_of_rows=5)

        assert page.page_no >= 1
        assert page.num_of_rows >= 1
        assert page.items
        assert page.total_count >= len(page.items)
        assert isinstance(page.raw, dict)
        assert page.context.service_name == "KorService2"
        assert page.context.endpoint == "areaCode2"
        assert page.context.request_params["MobileApp"] == "visitkorea-live-test"
        assert page.context.request_params["numOfRows"] == 5
        assert page.context.collected_at is not None
        assert "serviceKey" not in page.context.request_params
        assert key not in repr(page.context.request_params)
        for item in page.items:
            assert item.raw


async def test_live_foreign_service_or_explicit_auth_observation():
    key = _service_key()
    async with TourApiHubClient(key, mobile_app="visitkorea-live-test", timeout=20) as hub:
        try:
            page = await hub.eng.area_code(num_of_rows=1)
        except TourApiAuthError as exc:
            assert exc.failure_kind == "auth"
            assert exc.endpoint == "areaCode2"
            assert exc.service_name == "EngService2"
            assert key not in str(exc)
            assert key not in repr(exc.metadata)
            pytest.skip(
                f"EngService2/areaCode2 HTTP {exc.status_code}, result_code={exc.result_code}"
            )
        assert page.context.service_name == "EngService2"
        assert isinstance(page.items, tuple)


async def test_live_search_keyword_and_detail_chain():
    async with _kor_client() as client:
        page = await client.search_keyword(
            "경복궁",
            content_type_id=ContentType.TOURIST_ATTRACTION,
            num_of_rows=3,
        )

        assert page.context.endpoint == "searchKeyword2"
        assert page.items
        assert page.total_count >= len(page.items)
        if page.is_empty or not page.items[0].content_id:
            pytest.skip("no live keyword result to chain a detail lookup")

        item = page.items[0]
        assert item.raw

        detail = await client.detail_common(item.content_id)
        assert detail.content_id == item.content_id
        assert detail.context.endpoint == "detailCommon2"
        assert "serviceKey" not in detail.context.request_params


async def test_live_detail_pet_tour_returns_page_shape():
    async with _kor_client() as client:
        page = await client.search_keyword("반려견", num_of_rows=3)
        if page.is_empty or not page.items[0].content_id:
            pytest.skip("no live content id to query detailPetTour2")

        try:
            pet_page = await client.detail_pet_tour(page.items[0].content_id)
        except TourApiNoDataError:
            return

        assert pet_page.context.endpoint == "detailPetTour2"
        for info in pet_page.items:
            assert info.content_id is not None
            assert info.raw


async def test_live_retry_and_rate_limiter_plumbing_succeeds():
    async with _kor_client(
        max_retries=2,
        backoff_factor=0.2,
        rate_limiter=AsyncTokenBucket(max_rps=5),
    ) as client:
        page = await client.area_codes(num_of_rows=3)

        assert page.context.endpoint == "areaCode2"
        assert page.items
        assert page.total_count >= len(page.items)


async def test_live_code_cache_returns_same_page_instance():
    cache: dict = {}
    async with _kor_client(code_cache=cache) as client:
        first = await client.area_codes(num_of_rows=3)
        second = await client.area_codes(num_of_rows=3)

        assert second is first
        assert first.items
        assert len(cache) == 1


async def test_live_typed_hub_view_or_auth_error():
    async with TourApiHubClient(
        _service_key(), mobile_app="visitkorea-live-test", timeout=20
    ) as hub:
        try:
            page = await hub.gocamping.typed.based_list(num_of_rows=3)
        except TourApiAuthError as exc:
            pytest.skip(
                f"GoCamping/basedList HTTP {exc.status_code}, result_code={exc.result_code}"
            )

        assert page.items
        assert page.context.service_name == "GoCamping"
        for item in page.items:
            assert isinstance(item, GoCampingItem)
            assert item.raw


async def test_live_hub_debug_area_codes():
    async with TourApiHubClient(
        _service_key(), mobile_app="visitkorea-live-test", timeout=20
    ) as hub:
        run = await hub.debug_fetch("kor", "areaCode2", num_of_rows=1)
        assert run.error is None, run.error
        assert run.parsed is not None
        assert run.parsed.items
        assert run.parsed.context.service_name == "KorService2"
        assert run.parsed.context.endpoint == "areaCode2"
        assert _service_key() not in repr(run)
