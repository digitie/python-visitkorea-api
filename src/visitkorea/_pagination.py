"""Pagination helpers shared by typed and hub clients."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import TypeVar

from .models import Page

T = TypeVar("T")


def iter_paginated_pages(
    fetch_page: Callable[[int, int], Page[T]],
    *,
    page_no: int = 1,
    num_of_rows: int = 10,
    max_pages: int | None = None,
    max_items: int | None = None,
) -> Iterator[Page[T]]:
    """Iterate TourAPI pages until metadata says there is no next page."""

    _validate_pagination_input(
        page_no=page_no,
        num_of_rows=num_of_rows,
        max_pages=max_pages,
        max_items=max_items,
    )
    current_page_no = page_no
    pages_seen = 0
    items_seen = 0

    while True:
        if max_pages is not None and pages_seen >= max_pages:
            return
        if max_items is not None and items_seen >= max_items:
            return

        page = fetch_page(current_page_no, num_of_rows)
        if page.is_empty:
            return

        yield page
        pages_seen += 1
        items_seen += len(page.items)

        if not page.has_next_page:
            return
        current_page_no += 1


async def async_iter_paginated_pages(
    fetch_page: Callable[[int, int], Awaitable[Page[T]]],
    *,
    page_no: int = 1,
    num_of_rows: int = 10,
    max_pages: int | None = None,
    max_items: int | None = None,
) -> AsyncIterator[Page[T]]:
    """Asynchronously iterate TourAPI pages until metadata says there is no next page."""

    _validate_pagination_input(
        page_no=page_no,
        num_of_rows=num_of_rows,
        max_pages=max_pages,
        max_items=max_items,
    )
    current_page_no = page_no
    pages_seen = 0
    items_seen = 0

    while True:
        if max_pages is not None and pages_seen >= max_pages:
            return
        if max_items is not None and items_seen >= max_items:
            return

        page = await fetch_page(current_page_no, num_of_rows)
        if page.is_empty:
            return

        yield page
        pages_seen += 1
        items_seen += len(page.items)

        if not page.has_next_page:
            return
        current_page_no += 1


def _validate_pagination_input(
    *,
    page_no: int,
    num_of_rows: int,
    max_pages: int | None,
    max_items: int | None,
) -> None:
    if page_no < 1:
        raise ValueError("page_no must be >= 1")
    if num_of_rows < 1:
        raise ValueError("num_of_rows must be >= 1")
    if max_pages is not None and max_pages < 0:
        raise ValueError("max_pages must be >= 0")
    if max_items is not None and max_items < 0:
        raise ValueError("max_items must be >= 0")
