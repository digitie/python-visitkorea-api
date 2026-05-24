"""Command-line interface for visitkorea."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any, cast

from pydantic import BaseModel

from .client import KrTourApiClient


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="visitkorea")
    parser.add_argument(
        "--service-key",
        help="TourAPI decoded service key. Defaults to DATA_GO_KR_SERVICE_KEY.",
    )
    parser.add_argument("--mobile-app", default="visitkorea")
    parser.add_argument("--language", default="ko")
    subparsers = parser.add_subparsers(dest="command", required=True)

    keyword = subparsers.add_parser("keyword")
    keyword.add_argument("keyword")
    keyword.add_argument("--content-type-id")
    keyword.add_argument("--area-code")
    keyword.add_argument("--sigungu-code")

    location = subparsers.add_parser("location")
    location.add_argument("--map-x", type=float, required=True)
    location.add_argument("--map-y", type=float, required=True)
    location.add_argument("--radius", type=int, default=1000)
    location.add_argument("--content-type-id")

    detail = subparsers.add_parser("detail")
    detail.add_argument("content_id")

    areas = subparsers.add_parser("area-codes")
    areas.add_argument("--area-code")

    args = parser.parse_args(argv)
    client = KrTourApiClient(
        service_key=args.service_key,
        mobile_app=args.mobile_app,
        language=args.language,
    )

    result: Any
    if args.command == "keyword":
        result = client.search_keyword(
            args.keyword,
            content_type_id=args.content_type_id,
            area_code=args.area_code,
            sigungu_code=args.sigungu_code,
        )
    elif args.command == "location":
        result = client.location_based_list(
            map_x=args.map_x,
            map_y=args.map_y,
            radius=args.radius,
            content_type_id=args.content_type_id,
        )
    elif args.command == "detail":
        result = client.detail_common(args.content_id)
    else:
        result = client.area_codes(area_code=args.area_code)

    print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    return 0


def _jsonable(value: Any) -> Any:
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump())
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(cast("Any", value)))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
