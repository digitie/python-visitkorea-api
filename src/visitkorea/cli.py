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
from .services import get_api_catalog


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

    pet = subparsers.add_parser("pet-detail")
    pet.add_argument("content_id")

    festival = subparsers.add_parser("festival")
    festival.add_argument("event_start_date", help="YYYYMMDD")
    festival.add_argument("--event-end-date")
    festival.add_argument("--area-code")
    festival.add_argument("--sigungu-code")

    stay = subparsers.add_parser("stay")
    stay.add_argument("--area-code")
    stay.add_argument("--sigungu-code")

    area_based = subparsers.add_parser("area-based")
    area_based.add_argument("--content-type-id")
    area_based.add_argument("--area-code")
    area_based.add_argument("--sigungu-code")

    areas = subparsers.add_parser("area-codes")
    areas.add_argument("--area-code")

    subparsers.add_parser("catalog", help="List bundled TourAPI services and operations.")

    args = parser.parse_args(argv)

    if args.command == "catalog":
        print(json.dumps(_jsonable(list(get_api_catalog())), ensure_ascii=False, indent=2))
        return 0

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
    elif args.command == "pet-detail":
        result = client.detail_pet_tour(args.content_id)
    elif args.command == "festival":
        result = client.search_festival(
            args.event_start_date,
            event_end_date=args.event_end_date,
            area_code=args.area_code,
            sigungu_code=args.sigungu_code,
        )
    elif args.command == "stay":
        result = client.search_stay(
            area_code=args.area_code,
            sigungu_code=args.sigungu_code,
        )
    elif args.command == "area-based":
        result = client.area_based_list(
            content_type_id=args.content_type_id,
            area_code=args.area_code,
            sigungu_code=args.sigungu_code,
        )
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
