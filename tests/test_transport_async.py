"""VisitKorea 독립 mock 리뷰 재현."""

from __future__ import annotations

import asyncio
import gc
import logging

import httpx
import pytest

from visitkorea import KrTourApiClient, TourApiHubClient, TourApiServiceClient
from visitkorea._http import TourApiHttp
from visitkorea.exceptions import TourApiError, TourApiParseError


def payload(rows=None, total=1):
    return {
        "response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {
                "items": {"item": rows or [{"code": "11", "name": "mock"}]},
                "totalCount": total,
                "pageNo": 1,
                "numOfRows": 10,
            },
        }
    }


@pytest.mark.asyncio
async def test_failed_code_calls_do_not_retain_unbounded_locks():

    async def handler(request):
        return httpx.Response(403)

    cache = {}
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        KrTourApiClient("mock-key", session=session, code_cache=cache, max_rps=100) as client,
    ):
        for index in range(20):
            with pytest.raises(TourApiError):
                await client.area_codes(area_code=str(index))
        gc.collect()
        assert not cache
        assert len(client._code_cache_locks) == 0


@pytest.mark.asyncio
async def test_typed_numeric_parse_precedes_string_redaction():

    async def handler(request):
        return httpx.Response(
            200, json=payload([{"contentid": "11", "mapx": "127.5", "mapy": "37.5"}])
        )

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        KrTourApiClient("127", session=session) as client,
    ):
        page = await client.area_based_list()
        assert page.items[0].map_x == 127.5
        assert "127" not in str(page.raw)


@pytest.mark.asyncio
async def test_redirect_echo_does_not_leak_actual_key_to_httpx_log(caplog):
    secret = "mock-review-secret-key"
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(302, headers={"location": "/echo/" + secret})
        return httpx.Response(200, json=payload())

    with caplog.at_level(logging.INFO, logger="httpx"):
        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=True
            ) as session,
            KrTourApiClient(secret, session=session) as client,
        ):
            await client.area_codes()
    assert calls == 2
    assert secret not in caplog.text


class Budget:
    def __init__(self):
        self.count = 0

    async def acquire(self):
        self.count += 1


class Gate(Budget):
    def __init__(self, block_at):
        super().__init__()
        self.block_at = block_at
        self.entered, self.release = (asyncio.Event(), asyncio.Event())

    async def acquire(self):
        await super().acquire()
        if self.count == self.block_at:
            self.entered.set()
            await self.release.wait()


def low_http(session, **kwargs):
    return TourApiHttp(
        "mock-key",
        base_url="https://mock.test",
        service_name="KorService2",
        mobile_os="ETC",
        mobile_app="mock",
        session=session,
        **kwargs,
    )


async def no_sleep(*args):
    pass


@pytest.mark.asyncio
async def test_typed_and_two_hub_services_share_every_wire_attempt():
    sent = []

    async def handler(request):
        sent.append(request)
        if len(sent) == 1:
            raise httpx.ConnectTimeout("mock", request=request)
        if len(sent) == 2:
            raise httpx.ReadError("mock", request=request)
        if len(sent) == 3:
            return httpx.Response(503)
        if len(sent) == 4:
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(200, json=payload())

    budget = Budget()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as session:
        async with KrTourApiClient(
            "mock-key", session=session, rate_limiter=budget, retries=1, max_retries=2
        ) as typed:
            typed._http._sleep = no_sleep
            assert (await typed.area_codes()).items
        async with TourApiHubClient("mock-key", session=session, rate_limiter=budget) as hub:
            assert (await hub.gocamping.based_list()).items
            assert (
                await hub.related_tour.area_based_list(
                    base_ym="202601", area_cd="11", signgu_cd="11110"
                )
            ).items
        assert not session.is_closed
    assert len(sent) == budget.count == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("connect_retries,max_retries,expected", [(0, 0, 1), (2, 0, 3), (1, 2, 6)])
async def test_connection_and_outer_retry_limits_are_finite_and_metered(
    connect_retries, max_retries, expected
):
    sent = []

    async def handler(request):
        sent.append(request)
        raise httpx.ConnectError("mock", request=request)

    budget = Budget()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session:
        client = low_http(
            session,
            retries=connect_retries,
            max_retries=max_retries,
            rate_limiter=budget,
            sleep=no_sleep,
        )
        with pytest.raises(TourApiError):
            await client.get("areaCode2")
    assert len(sent) == budget.count == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("when", [1, 2])
@pytest.mark.parametrize("action", ["close", "auth", "cancel"])
async def test_hub_child_wait_respects_parent_close_auth_and_cancel(when, action):
    sent, responses = ([], [])

    async def handler(request):
        sent.append(request)
        response = (
            httpx.Response(302, headers={"location": "/final"})
            if len(sent) == 1
            else httpx.Response(200, json=payload())
        )
        responses.append(response)
        return response

    budget = Gate(when)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as session:
        hub = TourApiHubClient("mock-key", session=session, rate_limiter=budget)
        retained_child = hub.gocamping
        task = asyncio.create_task(retained_child.based_list())
        await budget.entered.wait()
        if action == "close":
            await hub.aclose()
            expected = RuntimeError
        elif action == "auth":
            session.auth = httpx.DigestAuth("mock", "mock")
            expected = TypeError
        else:
            task.cancel()
            expected = asyncio.CancelledError
        budget.release.set()
        with pytest.raises(expected):
            await task
        assert len(sent) == when - 1
        assert all(response.is_closed for response in responses)
        await hub.aclose()
        with pytest.raises(RuntimeError):
            await retained_child.based_list()


@pytest.mark.asyncio
async def test_owned_hub_pool_is_lazy_shared_closed_once(monkeypatch):
    import visitkorea.hub as hub_module

    pools = []

    async def handler(request):
        return httpx.Response(200, json=payload())

    class Pool(httpx.AsyncClient):
        closes = 0

        async def aclose(self):
            self.closes += 1
            await super().aclose()

    def build():
        pool = Pool(transport=httpx.MockTransport(handler))
        pools.append(pool)
        return pool

    monkeypatch.setattr(hub_module, "build_session", build)
    async with TourApiHubClient("mock-key", max_rps=100) as hub:
        assert not pools
        go = hub.gocamping
        related = hub.related_tour
        assert go._http.session is related._http.session
        assert len(pools) == 1
        await go.based_list()
        await related.area_based_list(base_ym="202601", area_cd="11", signgu_cd="11110")
    assert pools[0].is_closed and pools[0].closes == 1
    await hub.aclose()
    assert pools[0].closes == 1


@pytest.mark.asyncio
async def test_cache_waiter_survives_owner_cancellation_then_shares_result():
    started = asyncio.Event()
    sent = []

    async def handler(request):
        sent.append(request)
        if len(sent) == 1:
            started.set()
            await asyncio.Event().wait()
        return httpx.Response(200, json=payload())

    cache, budget = ({}, Budget())
    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        KrTourApiClient(
            "mock-key", session=session, code_cache=cache, rate_limiter=budget
        ) as client,
    ):
        first = asyncio.create_task(client.area_codes())
        await started.wait()
        others = [asyncio.create_task(client.area_codes()) for _ in range(5)]
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        pages = await asyncio.gather(*others)
        assert all(page is pages[0] for page in pages)
        assert len(sent) == budget.count == 2
        gc.collect()
        assert not client._code_cache_locks


@pytest.mark.asyncio
async def test_body_cancel_closes_actual_stream():
    started, closed = (asyncio.Event(), asyncio.Event())

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            started.set()
            await asyncio.Event().wait()
            yield b"never"

        async def aclose(self):
            closed.set()

    async def handler(request):
        return httpx.Response(200, stream=Stream())

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        KrTourApiClient("mock-key", session=session) as client,
    ):
        task = asyncio.create_task(client.area_codes())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set()


@pytest.mark.asyncio
async def test_standalone_service_has_public_async_lifecycle(monkeypatch):
    import visitkorea._http as http_module
    from visitkorea.services import SERVICE_BY_KEY

    pools = []

    async def handler(request):
        return httpx.Response(200, json=payload())

    def build():
        pool = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        pools.append(pool)
        return pool

    monkeypatch.setattr(http_module, "build_session", build)
    client = TourApiServiceClient(
        SERVICE_BY_KEY["gocamping"],
        service_key="mock-key",
        mobile_os="ETC",
        mobile_app="mock",
        base_url="https://mock.test",
        timeout=10,
        retries=0,
        session=None,
    )
    try:
        assert (await client.based_list()).items
        assert len(pools) == 1 and (not pools[0].is_closed)
        assert callable(getattr(client, "aclose", None))
        await client.aclose()
        assert pools[0].is_closed
        with pytest.raises(RuntimeError):
            await client.based_list()
    finally:
        await client._http.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", [False, True])
async def test_kwargs_actual_key_is_removed_from_public_context(typed):
    override = "override-mock-key"

    async def handler(request):
        assert request.url.params["serviceKey"] == override
        return httpx.Response(200, json=payload([{"contentId": "12", "facltNm": override}]))

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        TourApiHubClient("configured-mock-key", session=session) as hub,
    ):
        caller = hub.gocamping.typed if typed else hub.gocamping
        page = await caller.call("basedList", serviceKey=override, keyword=override)
        assert override not in str(page.model_dump())


@pytest.mark.asyncio
async def test_concurrent_log_scopes_mask_both_requests_and_reset(caplog):
    secrets = ["mock-review-alpha-secret", "mock-review-beta-secret"]
    entered = 0
    ready = asyncio.Event()

    async def handler(request):
        nonlocal entered
        if request.url.path.startswith("/echo/"):
            return httpx.Response(200, json=payload())
        entered += 1
        if entered == 2:
            ready.set()
        await ready.wait()
        return httpx.Response(
            302, headers={"location": "/echo/" + request.url.params["serviceKey"]}
        )

    with caplog.at_level(logging.INFO, logger="httpx"):
        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(handler), follow_redirects=True
            ) as session,
            KrTourApiClient(secrets[0], session=session) as alpha,
            KrTourApiClient(secrets[1], session=session) as beta,
        ):
            await asyncio.gather(alpha.area_codes(), beta.area_codes())
        assert all(secret not in caplog.text for secret in secrets)
        caplog.clear()
        logging.getLogger("httpx").info("after_scope %s %s", *secrets)
        assert all(secret in caplog.text for secret in secrets)


@pytest.mark.asyncio
async def test_hub_typed_numeric_parse_precedes_redaction():

    async def handler(request):
        return httpx.Response(
            200, json=payload([{"contentId": "11", "mapX": "127.5", "mapY": "37.5"}])
        )

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        TourApiHubClient("127", session=session) as hub,
    ):
        page = await hub.gocamping.typed.based_list()
        assert page.items[0].map_x == 127.5
        assert "127" not in str(page.raw)


@pytest.mark.asyncio
@pytest.mark.parametrize("repeat", [False, True])
async def test_typed_iterator_parses_numeric_and_preserves_pagination(repeat):
    sent = []

    async def handler(request):
        page_no = int(request.url.params["pageNo"])
        sent.append(page_no)
        row = {"contentId": "11" if repeat else str(page_no), "mapX": "127.5", "mapY": "37.5"}
        data = payload([row], total=3)
        data["response"]["body"].update({"pageNo": 1 if repeat else page_no, "numOfRows": 1})
        return httpx.Response(200, json=data)

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        TourApiHubClient("127", session=session) as hub,
    ):
        iterator = hub.gocamping.typed.iter_pages(
            "basedList", params={"pageNo": 99, "numOfRows": 99}, num_of_rows=1, max_pages=2
        )
        first = await anext(iterator)
        assert first.items[0].map_x == 127.5
        assert "127" not in str(first.raw)
        if repeat:
            with pytest.raises(TourApiParseError, match="repeated"):
                await anext(iterator)
        else:
            second = await anext(iterator)
            assert second.items[0].map_x == 127.5
            with pytest.raises(StopAsyncIteration):
                await anext(iterator)
        assert sent == [1, 2]


@pytest.mark.asyncio
async def test_debug_numeric_success_and_concurrent_failure_are_isolated():
    entered = 0
    ready = asyncio.Event()
    override = "mock-override-debug-key"

    async def handler(request):
        nonlocal entered
        entered += 1
        if entered == 2:
            ready.set()
        await ready.wait()
        if request.url.params["facltNm"] == "beta":
            return httpx.Response(403, text=override)
        return httpx.Response(
            200, json=payload([{"contentId": "11", "mapX": "127.5", "mapY": "37.5"}])
        )

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(handler)) as session,
        TourApiHubClient("127", session=session) as hub,
    ):
        alpha, beta = await asyncio.gather(
            hub.debug_fetch(
                "gocamping",
                "basedList",
                {"facltNm": "alpha", "serviceKey": override},
                use_typed=True,
            ),
            hub.debug_fetch(
                "gocamping",
                "basedList",
                {"facltNm": "beta", "serviceKey": override},
                use_typed=True,
            ),
        )
    assert alpha.error is None and alpha.parsed.items[0].map_x == 127.5
    assert beta.error and beta.parsed is None
    assert alpha.input["params"]["facltNm"] == "alpha"
    assert beta.input["params"]["facltNm"] == "beta"
    assert override not in str(alpha) + str(beta)
