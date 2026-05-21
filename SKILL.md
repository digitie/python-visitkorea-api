---
name: visitkorea-python-builder
description: data.go.kr의 Korea Tourism Organization TourAPI용 Python client인 `visitkorea`를 구현, 확장, 디버깅, 문서화할 때 사용한다.
---

# VisitKorea Python Library Builder

`visitkorea`는 한국관광공사 TourAPI용 Python client다. 공개 동작을 바꾸기 전에는 `README.md`, `krtourapi-api.md`, `AGENTS.md`를 읽는다.

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. 공식 API field, code identifier, 명령어, URL, provider 원문은 필요한 경우 원문을 유지한다.

## 프로젝트 불변 조건

1. 기본 service는 `KorService2`다.
2. 기본 base URL은 `http://apis.data.go.kr/B551011`이다.
3. 인증 parameter는 `serviceKey`다.
4. Public example은 `params=`를 사용하므로 decoding service key를 가정한다.
5. 항상 `_type=json`을 요청한다.
6. 항상 `MobileOS`와 `MobileApp`을 포함한다.
7. 기본 test는 실제 API를 호출하지 않는다.
8. Unknown API field는 model `raw`에 보존한다.
9. `items.item`이 없거나 단일 object이거나 list인 경우를 모두 정규화한다.
10. `_type=json`이어도 service-key error는 XML로 올 수 있다.
11. `TourApiHubClient`는 `api.visitkorea.or.kr/#/useUtilExercises`의 모든 service를 cover한다.
12. Downloaded official manual ZIP/DOCX는 `.manuals/`에 두고 commit하지 않는다.
13. Secret은 local `.env.local` 또는 shell environment에만 둔다.
14. `resultCode=0000`을 success로 처리하고 live TourAPI call에는 browser-compatible User-Agent를 유지한다.
15. 공개 coordinate API는 `kraddr.base.PlaceCoordinate(lat, lon)`을 사용하고 TourAPI `mapX`/`mapY` 변환은 request boundary에서만 수행한다.
16. Downstream application과 type checker를 위해 enum/type export를 안정적으로 유지한다.
17. 공개 response model은 `TourApiModel`/Pydantic v2 `BaseModel`을 상속하고 frozen 상태를 유지한다.
18. 불안정한 TourAPI field는 `raw`에 보존하고 content-type별 세부 field를 과도하게 model화하지 않는다.

## 지원 endpoint

`KrTourApiClient`는 일반적인 `KorService2` endpoint에 typed wrapper를 제공한다.

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

그 외 공식 service는 `TourApiHubClient`와 `SERVICE_DEFINITIONS`로 노출한다. Operation은 manual의 camelCase 이름 또는 unique snake_case alias로 호출할 수 있다.

```python
hub = TourApiHubClient.from_env()
hub.gocamping.based_list(facltNm="숲")
hub.call("photo_gallery", "gallerySearchList1", galSearchKeyword="서울")
```

## 동작 변경 시 deliverable

- 사용자-facing API 변경은 `README.md`에 반영한다.
- Endpoint, parameter, response, official-doc 변경은 `krtourapi-api.md`에 반영한다.
- Test 정책 변경은 `docs/testing.md`에 반영한다.
- Known fix는 `docs/troubleshooting.md`에 반영한다.
- 반복 실수 방지는 `docs/repeated-mistakes.md`에 반영한다.
- Live test보다 offline test를 먼저 추가한다.
- `CHANGELOG.md`를 최신 상태로 유지한다.

## Guardrail

- `areaCode` 없이 `sigunguCode`를 전달하지 않는다.
- `cat1` 없이 `cat2`, `cat1`/`cat2` 없이 `cat3`를 전달하지 않는다.
- `lDongRegnCd` 없이 `lDongSignguCd`를 전달하지 않는다.
- `lclsSystm1` 없이 `lclsSystm2`, `lclsSystm1`/`lclsSystm2` 없이 `lclsSystm3`를 전달하지 않는다.
- TourAPI timestamp는 KST로 parsing한다.
- Optional numeric field 변환이 불안전하면 `None`을 사용한다.
- Raw `KeyError`/`TypeError`를 노출하지 말고 `TourApiParseError`로 바꾼다.

## Test 요구사항

기본 test는 request parameter shape, common params(`serviceKey`, `MobileOS`, `MobileApp`, `_type=json`), result-code exception mapping, XML service-key error, `items.item` 단일/list, empty result, dependent parameter validation, Pydantic model conversion/serialization, CLI output, service catalog count/alias, generic Hub routing, Pythonic parameter alias conversion, public enum/type export, WGS84 coordinate normalization을 다룬다.

Live test는 `live` marker를 붙이고 `DATA_GO_KR_SERVICE_KEY`가 없으면 skip한다. `scripts/run_live_tests.ps1`로 `.env.local`을 load하며 key를 test에 hard-code하지 않는다.
