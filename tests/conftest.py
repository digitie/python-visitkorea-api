from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from visitkorea.client import AsyncKrTourApiClient, KrTourApiClient


class FakeResponse:
    def __init__(
        self,
        payload: Any = None,
        *,
        status_code: int = 200,
        text: str | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._json_error = json_error
        self.status_code = status_code
        self.text = text if text is not None else json.dumps(payload)

    def json(self) -> Any:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "params": dict(params), "timeout": timeout})
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)


class FakeAsyncSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    async def get(self, url: str, *, params: Mapping[str, Any], timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "params": dict(params), "timeout": timeout})
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)

    async def aclose(self) -> None:
        self.closed = True


def tour_payload(
    item: Any,
    *,
    result_code: str = "00",
    result_msg: str = "OK",
    page_no: int = 1,
    num_of_rows: int = 10,
    total_count: int | None = None,
) -> dict[str, Any]:
    items = "" if item is None else {"item": item}
    if total_count is None:
        if isinstance(item, list):
            total_count = len(item)
        elif item is None:
            total_count = 0
        else:
            total_count = 1
    return {
        "response": {
            "header": {"resultCode": result_code, "resultMsg": result_msg},
            "body": {
                "items": items,
                "numOfRows": num_of_rows,
                "pageNo": page_no,
                "totalCount": total_count,
            },
        }
    }


@pytest.fixture
def fake_client_factory() -> Any:
    def factory(*responses: FakeResponse, **kwargs: Any) -> tuple[KrTourApiClient, FakeSession]:
        session = FakeSession(list(responses))
        client = KrTourApiClient("TEST_KEY", session=session, **kwargs)
        return client, session

    return factory


@pytest.fixture
def fake_async_client_factory() -> Any:
    def factory(
        *responses: FakeResponse,
        **kwargs: Any,
    ) -> tuple[AsyncKrTourApiClient, FakeAsyncSession]:
        session = FakeAsyncSession(list(responses))
        client = AsyncKrTourApiClient("TEST_KEY", session=session, **kwargs)
        return client, session

    return factory
