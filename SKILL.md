---
name: visitkorea-python-builder
description: Use this skill when building, extending, debugging, or documenting visitkorea, a Python client for Korea Tourism Organization TourAPI on data.go.kr.
---

# VisitKorea Python Library Builder

You are helping build and maintain `visitkorea`, a Python client for Korea Tourism Organization TourAPI.

Read `README.md`, `krtourapi-api.md`, and `AGENTS.md` before changing public behavior.

## Project invariants

1. Default service is `KorService2`.
2. Default base URL is `http://apis.data.go.kr/B551011`.
3. Auth parameter is `serviceKey`.
4. Public examples assume a Decoding service key because requests are made with `params=`.
5. Always request `_type=json`.
6. Always include `MobileOS` and `MobileApp`.
7. Default tests must not call the real API.
8. Preserve unknown API fields in model `raw`.
9. Normalize `items.item` whether it is missing, a single object, or a list.
10. Service-key errors can arrive as XML even when `_type=json`.
11. `TourApiHubClient` covers every service listed in `api.visitkorea.or.kr/#/useUtilExercises`.
12. Downloaded official manual ZIP/DOCX files stay in `.manuals/` and are never committed.
13. Secrets stay in local `.env.local` or shell environment only; never commit API keys.
14. Treat `resultCode=0000` as success, and keep a browser-compatible User-Agent for live TourAPI calls.
15. Public coordinate APIs use `kraddr.base.PlaceCoordinate(lat, lon)`; convert to TourAPI `mapX`/`mapY` only at the request boundary.
16. Keep enum/type exports stable for downstream applications and type checkers.
17. Public response models inherit from `TourApiModel`/Pydantic v2 `BaseModel` and remain frozen.
18. Keep unstable TourAPI fields in `raw`; do not over-model content-type-specific fields.

## Supported endpoints

`KrTourApiClient` exposes typed wrappers for the common `KorService2` endpoints below.

| Public method | Endpoint |
|---|---|
| `area_based_list()` | `areaBasedList2` |
| `location_based_list()` | `locationBasedList2` |
| `search_keyword()` | `searchKeyword2` |
| `search_festival()` | `searchFestival2` |
| `search_stay()` | `searchStay2` |
| `detail_common()` | `detailCommon2` |
| `detail_intro()` | `detailIntro2` |
| `detail_info()` | `detailInfo2` |
| `detail_images()` | `detailImage2` |
| `area_based_sync_list()` | `areaBasedSyncList2` |
| `area_codes()` | `areaCode2` |
| `category_codes()` | `categoryCode2` |
| `legal_dong_codes()` | `ldongCode2` |
| `classification_system_codes()` | `lclsSystmCode2` |

All other official services are exposed through `TourApiHubClient` and `SERVICE_DEFINITIONS`.
Operations can be called by the manual's camelCase name or a unique snake_case alias:

```python
hub = TourApiHubClient.from_env()
hub.gocamping.based_list(facltNm="숲")
hub.call("photo_gallery", "gallerySearchList1", galSearchKeyword="서울")
```

## Required deliverables for behavior changes

- Update `README.md` for user-facing API changes.
- Update `krtourapi-api.md` for endpoint, parameter, response, or official-doc changes.
- Update `docs/testing.md` when test policy changes.
- Update `docs/troubleshooting.md` when adding a known fix.
- Update `docs/repeated-mistakes.md` when preventing a recurring mistake.
- Add offline tests before live tests.
- Keep `CHANGELOG.md` current.

## Guardrails

- Do not pass `sigunguCode` without `areaCode`.
- Do not pass `cat2` without `cat1`, or `cat3` without `cat1` and `cat2`.
- Do not pass `lDongSignguCd` without `lDongRegnCd`.
- Do not pass `lclsSystm2` without `lclsSystm1`, or `lclsSystm3` without `lclsSystm1` and `lclsSystm2`.
- Do not assume response timestamps are timezone-free; parse TourAPI timestamps as KST.
- Do not crash on optional numeric fields. Use `None` when conversion is unsafe.
- Do not expose raw `KeyError` or `TypeError`; convert response-shape issues into `TourApiParseError`.

## Testing requirements

Default tests should cover:

- request parameter shape
- common params (`serviceKey`, `MobileOS`, `MobileApp`, `_type=json`)
- result-code exception mapping
- XML service-key error mapping
- `items.item` as single object and list
- empty results
- dependent parameter validation
- Pydantic model conversion and serialization
- CLI output serialization
- service catalog count/aliases
- generic Hub client routing
- Pythonic parameter alias conversion
- public enum/type exports
- WGS84 coordinate normalization

Live tests, if added, must be marked `live` and skip when `DATA_GO_KR_SERVICE_KEY` is absent.
Use `scripts/run_live_tests.ps1` to load `.env.local`; do not hard-code keys in tests.
