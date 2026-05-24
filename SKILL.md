---
name: visitkorea-python-builder
description: data.go.kr의 Korea Tourism Organization TourAPI용 Python client인 `visitkorea`를 구현, 확장, 디버깅, 문서화할 때 사용한다.
---

# SKILL — visitkorea 에이전트 매뉴얼

> 이 파일은 당신(AI 에이전트)이 작업을 시작하기 전 반드시 읽어야 한다.
> 1회만 읽으면 30분 이상의 디버깅을 줄일 수 있다.

## 1. 정체성

이 저장소(GitHub 이름 `python-visitkorea-api`, Python 패키지 `visitkorea`)는 한국관광공사 TourAPI 전체를 커버하는 **Python client library**다. 공개 동작을 바꾸기 전에는 `README.md`, `krtourapi-api.md`, `AGENTS.md`를 읽는다.

### 식별자 매핑

| 항목 | 값 |
|------|----|
| GitHub 저장소 | `python-visitkorea-api` |
| Python import | `from visitkorea import ...` |
| CLI 명령 | `visitkorea` |
| 환경변수 | `DATA_GO_KR_SERVICE_KEY`, `VISITKOREA_API_SERVICE_KEY` |
| 기본 base URL | `http://apis.data.go.kr/B551011` |
| 기본 서비스 | `KorService2` |

## 2. 빠른 시작

```bash
uv venv && uv pip install -e ".[dev]"
python -m pytest -q
```

## 3. 디렉토리 지도

```
src/visitkorea/
  client.py            — KrTourApiClient / AsyncKrTourApiClient (KorService2 typed wrapper)
  hub.py               — TourApiHubClient / AsyncTourApiHubClient (27개 서비스 generic)
  services.py          — SERVICE_DEFINITIONS (api.visitkorea.or.kr 매뉴얼 기반 카탈로그)
  operation_schema.py  — 오퍼레이션 파라미터 스키마
  models.py            — Pydantic v2 response model (frozen, raw 보존)
  types.py             — 공개 type alias
  enums.py             — AreaCode, ContentType, Language, Arrange, MobileOS
  exceptions.py        — TourApiError 예외 계층
  display.py           — HTML 정리, 저작권 표시
  cli.py               — CLI entrypoint
  _http.py             — httpx 기반 HTTP/envelope/error 처리
  _auth.py             — 서비스키 탐색 (env, dotenv, 다중 소스)
  _convert.py          — 변환 helper
  _time.py             — KST timestamp parsing
  _pagination.py       — 페이지네이션 iterator
  _provenance.py       — TourApiCallContext 생성
```

## 4. 절대 하지 말 것 (DO NOT)

1. **동기/비동기 코드 불일치 금지**: sync/async 클래스에서 `_list_params()`, `_page_params()` 등 공유 로직은 항상 동일하게 유지. 한쪽을 수정하면 반드시 다른 쪽도 갱신.
2. **서비스 키 평문 노출 금지**: 예외 메시지, 로그, response에 서비스 키를 포함하지 않는다. `_redact_secret()`을 거친다.
3. **`areaCode` 없이 `sigunguCode` 전달 금지**: TourAPI가 무시하거나 오류를 반환한다.
4. **`cat1` 없이 `cat2`, `cat1`/`cat2` 없이 `cat3` 전달 금지**: 계층적 의존성.
5. **`lDongRegnCd` 없이 `lDongSignguCd` 전달 금지**: 계층적 의존성.
6. **`lclsSystm1` 없이 `lclsSystm2`, `lclsSystm1`/`lclsSystm2` 없이 `lclsSystm3` 전달 금지**: 계층적 의존성.
7. **TourAPI timestamp를 UTC로 해석 금지**: 항상 KST(`Asia/Seoul`).
8. **불안정한 TourAPI 필드를 과도하게 model화 금지**: `raw`에 보존. content-type별 세부 필드는 `IntroInfo.raw`에 위임.
9. **단순 전달용 래퍼/어댑터/게이트웨이 작성 금지**: downstream 사용자에게 안정 public client, typed model, enum, helper를 직접 제공.
10. **좌표 순서 혼동 금지**: 공개 API는 `PlaceCoordinate(lat, lon)`. TourAPI의 `mapX`(경도)/`mapY`(위도) 변환은 request boundary에서만.
11. **외부 API 키 평문 커밋 금지**: `.env`는 gitignore. 테스트에 키를 하드코드하지 않는다.
12. **Raw `KeyError`/`TypeError` 노출 금지**: `TourApiParseError`로 변환한다.

## 5. 프로젝트 불변 조건

1. 기본 서비스는 `KorService2`다.
2. 기본 base URL은 `http://apis.data.go.kr/B551011`이다.
3. 인증 파라미터는 `serviceKey`다.
4. Public example은 `params=`를 사용하므로 decoding 서비스키를 가정한다.
5. 항상 `_type=json`을 요청한다.
6. 항상 `MobileOS`와 `MobileApp`을 포함한다.
7. 기본 테스트는 실제 API를 호출하지 않는다.
8. Unknown API 필드는 model `raw`에 보존한다.
9. `items.item`이 없거나 단일 object이거나 list인 경우를 모두 정규화한다.
10. `_type=json`이어도 service-key error는 XML로 올 수 있다.
11. `TourApiHubClient`는 `api.visitkorea.or.kr/#/useUtilExercises`의 모든 서비스를 커버한다.
12. Downloaded official manual ZIP/DOCX는 `.manuals/`에 두고 commit하지 않는다.
13. Secret은 local `.env` 또는 shell environment에만 둔다.
14. `resultCode=0000`을 success로 처리하고 live TourAPI call에는 browser-compatible User-Agent를 유지한다.
15. 공개 coordinate API는 `kraddr.base.PlaceCoordinate(lat, lon)`을 사용하고 TourAPI `mapX`/`mapY` 변환은 request boundary에서만 수행한다.
16. Downstream application과 type checker를 위해 enum/type export를 안정적으로 유지한다.
17. 공개 response model은 `TourApiModel`/Pydantic v2 `BaseModel`을 상속하고 frozen 상태를 유지한다.
18. 불안정한 TourAPI 필드는 `raw`에 보존하고 content-type별 세부 필드를 과도하게 model화하지 않는다.

## 6. 지원 endpoint

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

그 외 공식 서비스는 `TourApiHubClient`와 `SERVICE_DEFINITIONS`로 노출한다.

```python
hub = TourApiHubClient.from_env()
hub.gocamping.based_list(facltNm="숲")
hub.call("photo_gallery", "gallerySearchList1", galSearchKeyword="서울")
```

## 7. 동작 변경 시 deliverable

- 사용자-facing API 변경은 `README.md`에 반영한다.
- Endpoint, parameter, response, official-doc 변경은 `krtourapi-api.md`에 반영한다.
- Test 정책 변경은 `docs/testing.md`에 반영한다.
- Known fix는 `docs/troubleshooting.md`에 반영한다.
- 반복 실수 방지는 `docs/repeated-mistakes.md`에 반영한다.
- Live test보다 offline test를 먼저 추가한다.
- `CHANGELOG.md`를 최신 상태로 유지한다.

## 8. Test 요구사항

기본 테스트는 request parameter shape, common params(`serviceKey`, `MobileOS`, `MobileApp`, `_type=json`), result-code exception mapping, XML service-key error, `items.item` 단일/list, empty result, dependent parameter validation, Pydantic model conversion/serialization, CLI output, service catalog count/alias, generic Hub routing, Pythonic parameter alias conversion, public enum/type export, WGS84 coordinate normalization을 다룬다.

Live test는 `live` marker를 붙이고 `DATA_GO_KR_SERVICE_KEY`가 없으면 skip한다.

## 9. 작업 후 체크리스트

- [ ] `python -m pytest -q` 통과
- [ ] `ruff check .` / `mypy src/visitkorea` 통과
- [ ] 실수를 고쳤다면 `docs/repeated-mistakes.md`에 기록
- [ ] 사용자 가시 변경이면 `CHANGELOG.md` 갱신
- [ ] 새 endpoint/서비스 추가 시 `krtourapi-api.md` 갱신

## 10. Guardrail

- `areaCode` 없이 `sigunguCode`를 전달하지 않는다.
- `cat1` 없이 `cat2`, `cat1`/`cat2` 없이 `cat3`를 전달하지 않는다.
- `lDongRegnCd` 없이 `lDongSignguCd`를 전달하지 않는다.
- `lclsSystm1` 없이 `lclsSystm2`, `lclsSystm1`/`lclsSystm2` 없이 `lclsSystm3`를 전달하지 않는다.
- TourAPI timestamp는 KST로 parsing한다.
- Optional numeric field 변환이 불안전하면 `None`을 사용한다.
- Raw `KeyError`/`TypeError`를 노출하지 말고 `TourApiParseError`로 바꾼다.
