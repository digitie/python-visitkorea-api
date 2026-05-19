# TourAPI 구현 메모

확인 기준일: 2026-04-30

## 공식 근거

- [공공데이터포털 한국관광공사_국문 관광정보서비스_GW](https://www.data.go.kr/en/data/15101578/openapi.do)
- [공공데이터포털 2026-01-09 TourAPI 오퍼레이션 URL/입출력 변경 공지](https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004471)
- [TourAPI 관광데이터 Hub](https://api.visitkorea.or.kr)
- [한국관광콘텐츠랩 OpenAPI 활용신청 목록](https://api.visitkorea.or.kr/#/useUtilExercises)

공공데이터포털 문서에는 국문 관광정보서비스가 JSON+XML REST API이며, 약 26만 건의 국내 관광정보를 15종 범주로 제공한다고 안내되어 있다. 기본 요청 링크는 `http://apis.data.go.kr/B551011/KorService2/{operation}` 형식이다.

`api.visitkorea.or.kr/#/useUtilExercises`의 전체 활용신청 목록은 27개 서비스 ZIP 메뉴얼을 기준으로 `visitkorea.services.SERVICE_DEFINITIONS`에 반영한다. `KrTourApiClient`는 자주 쓰는 `KorService2`용 typed wrapper이고, 나머지 서비스와 모든 operation은 `TourApiHubClient`가 카탈로그 기반 generic wrapper로 제공한다.

## 공통 요청

| 파라미터 | 규칙 |
|---|---|
| `serviceKey` | 공공데이터포털 인증키. `params=`를 쓰므로 Decoding 키 권장 |
| `MobileOS` | `IOS`, `AND`, `WEB`, `WIN`, `ETC`; 기본 `ETC` |
| `MobileApp` | 서비스/앱 이름; 기본 `visitkorea` |
| `_type` | 항상 `json` |
| `pageNo` | 1 이상 |
| `numOfRows` | 1~1000 |

실 서버 확인 결과 TourAPI 게이트웨이는 기본 Python HTTP 클라이언트 User-Agent에 HTTP 403을 반환할 수 있다. 기본 `build_session()`과 `build_async_session()`은 브라우저 호환 User-Agent를 넣는다. 커스텀 session을 주입할 때도 User-Agent를 유지한다.

HTTP 계층은 `httpx` 기반이다. `KrTourApiClient`와 `TourApiHubClient`는 동기 `httpx.Client` 경로를 사용하고, `AsyncKrTourApiClient`와 `AsyncTourApiHubClient`는 `httpx.AsyncClient` 경로를 사용한다. 응답 envelope 파싱, XML 오류 매핑, 서비스키 redaction, provenance 생성 규칙은 동기/비동기에서 동일해야 한다.

## 구현 endpoint

### Typed KorService2 wrapper

| 메서드 | endpoint | 핵심 요청 |
|---|---|---|
| `area_based_list` | `areaBasedList2` | `contentTypeId`, 지역/법정동/분류체계 필터 |
| `location_based_list` | `locationBasedList2` | `mapX`, `mapY`, `radius` 필수. `radius <= 20000` |
| `search_keyword` | `searchKeyword2` | `keyword` 필수 |
| `search_festival` | `searchFestival2` | `eventStartDate` 필수, `eventEndDate` 선택 |
| `search_stay` | `searchStay2` | 숙박 정보 목록 |
| `detail_common` | `detailCommon2` | `contentId` |
| `detail_intro` | `detailIntro2` | `contentId`, `contentTypeId` |
| `detail_info` | `detailInfo2` | `contentId`, `contentTypeId` |
| `detail_images` | `detailImage2` | `contentId`, `imageYN`, `subImageYN` |
| `area_based_sync_list` | `areaBasedSyncList2` | 동기화 목록, `showFlag` 선택 |
| `area_codes` | `areaCode2` | `areaCode` 선택 |
| `category_codes` | `categoryCode2` | `contentTypeId`, `cat1`, `cat2`, `cat3` |
| `legal_dong_codes` | `ldongCode2` | `lDongRegnCd`, `lDongListYn` |
| `classification_system_codes` | `lclsSystmCode2` | `lclsSystm1/2/3`, `lclsSystmListYn` |

### 전체 OpenAPI generic wrapper

`TourApiHubClient`는 메뉴얼 목록의 서비스명과 operation명을 그대로 사용한다. Python에서는 camelCase operation을 snake_case alias로도 호출할 수 있다.

```python
from visitkorea import TourApiHubClient

hub = TourApiHubClient.from_env()

hub.gocamping.based_list(facltNm="숲")
hub.photo_gallery.gallery_search_list(galSearchKeyword="서울")
hub.call("area_resource_demand", "areaTarSvcDemList", baseYm="202509", areaCd="11")
hub.related_tour.area_based_list(base_ym="202504", area_cd="51", signgu_cd="51130")
```

서비스 key, service name, alias, operation 목록은 `docs/openapi-catalog.md`와 `SERVICE_DEFINITIONS`가 단일 기준이다. 메뉴얼 ZIP 원본은 `.manuals/`에 다운로드해 분석하되 저장소에는 커밋하지 않는다.

`related_tour` 서비스는 `area_based_list()`와 `search_keyword()` typed helper를 제공해 `Page[RelatedTourItem]`을 반환한다. 기존 generic `call()`은 계속 `Page[Mapping]` raw record를 반환한다. TarRlteTarService1의 `areaCd`와 `signguCd`는 해당 서비스의 TourAPI 지역 코드이며 법정동코드가 아니다.

typed client와 Hub는 모두 pagination iterator를 제공한다. `Page.has_next_page`는 `total_count`, `page_no`, `num_of_rows`를 기준으로 계산하고, `iter_pages()`는 다음 `pageNo`를 증가시키며 호출한다. `max_pages` 또는 `max_items`는 비정상 응답에 대한 guard로 사용한다. 목록 API의 `NO_DATA`는 빈 iterator이고, 인증/쿼터/서버 오류는 기존 exception mapping을 그대로 따른다.
async client와 async Hub는 같은 규칙의 async iterator를 제공한다.

## 코드 체계

### 공개 enum/type

외부 프로그램에서 문자열 상수를 직접 흩뿌리지 않도록 아래 값을 public API로 노출한다.

- `Language`: `ko`, `en`, `ja`, `zh-cn`, `zh-tw`, `de`, `fr`, `es`, `ru`
- `AreaCode`: 국문 서비스 지역 코드
- `ContentType`: 국문 서비스 content type 코드
- `Arrange`, `MobileOS`
- `PlaceCoordinate`: `kraddr.base`의 WGS84 경도/위도 객체
- `Wgs84Coordinate`: 기존 호환용 `PlaceCoordinate` alias
- `ServiceKey`, `ContentId`, `DateInput`, `CoordinateInput`, `AreaCodeInput` 등 타입 alias

위치 검색은 `kraddr.base.PlaceCoordinate(lat=..., lon=...)`를 직접 사용한다. TourAPI 원문 이름은 `mapX=lon`, `mapY=lat`로만 변환한다. 튜플 좌표는 `(latitude, longitude)` 또는 `(lat, lon)` 순서로 해석한다.

### 국문 contentTypeId

| 값 | 의미 |
|---|---|
| `12` | 관광지 |
| `14` | 문화시설 |
| `15` | 축제/공연/행사 |
| `25` | 여행코스 |
| `28` | 레포츠 |
| `32` | 숙박 |
| `38` | 쇼핑 |
| `39` | 음식점 |

### 정렬 arrange

| 값 | 의미 |
|---|---|
| `A` | 제목순 |
| `C` | 수정일순 |
| `D` | 생성일순 |
| `E` | 거리순 |
| `O` | 대표 이미지 있는 항목 제목순 |
| `Q` | 대표 이미지 있는 항목 수정일순 |
| `R` | 대표 이미지 있는 항목 생성일순 |
| `S` | 대표 이미지 있는 항목 거리순 |

## 의존성 검증

기존 `areaCode`, `sigunguCode`, `cat1/2/3`는 공식 문서에서 삭제 예정 또는 대체 예정으로 표시되는 항목이 있다. 하지만 운영 호환성을 위해 여전히 전달할 수 있게 두되, 하위 코드만 단독으로 들어가는 실수는 막는다.

- `sigunguCode`는 `areaCode` 필요
- `cat2`는 `cat1` 필요
- `cat3`는 `cat1`, `cat2` 필요
- `lDongSignguCd`는 `lDongRegnCd` 필요
- `lclsSystm2`는 `lclsSystm1` 필요
- `lclsSystm3`는 `lclsSystm1`, `lclsSystm2` 필요

## 응답 정규화

TourAPI 응답은 보통 아래 형태다.

```json
{
  "response": {
    "header": {"resultCode": "00", "resultMsg": "OK"},
    "body": {
      "items": {"item": []},
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 0
    }
  }
}
```

주의할 점:

- `items`가 빈 문자열일 수 있다.
- `items.item`이 단일 object일 수 있다.
- `items.item`이 list일 수 있다.
- 서비스키 오류는 `_type=json` 요청이어도 XML로 돌아올 수 있다.
- 정상 resultCode는 `00`, `0000`, `0`, `NORMAL_CODE`를 허용한다.
- `resultCode=03`은 목록에서는 빈 `Page`로 처리하고, 단건 상세에서는 `TourApiNoDataError`로 올린다.
- 신청하지 않은 서비스는 JSON/XML envelope 없이 HTTP 403만 반환할 수 있으며, 이 경우 `TourApiAuthError`로 매핑한다.

## Pydantic 모델

공개 응답 모델은 Pydantic v2 `BaseModel`을 상속한 `TourApiModel` 기반이다. 모델은 `ConfigDict(frozen=True)`로 frozen 처리해 기존 불변 모델 사용감을 유지한다.

- 속성 접근: `item.title`, `page.items`
- dict 직렬화: `model_dump()`
- JSON 직렬화: `model_dump_json()`
- JSON schema: `model_json_schema()`

TourAPI 원문 전체는 각 모델의 `raw` 필드에 보존한다.

목록 응답 `Page.context`에는 호출 provenance를 보존한다. `service_name`, `endpoint`, `request_params`, `collected_at`을 담고, `request_params`에는 `MobileOS`, `MobileApp`, `_type`과 endpoint별 파라미터만 남긴다. 인증키 원문인 `serviceKey`는 포함하지 않는다. 단건 `detailCommon2`는 기존 반환형을 유지하면서 `TourDetail.context`에 같은 정보를 담는다.

`RelatedTourItem`은 TarRlteTarService1 응답의 `baseYm`, `tAtsCd`, `rlteTatsNm`, `rlteRank` 같은 원문 필드명을 typed 속성으로 노출하고, 전체 record는 `raw`에 보존한다.

표시용 helper는 기본 parsing 결과를 바꾸지 않는다. `cpyrhtDivCd` 원문은 모델의 `copyright_division_code`와 `raw`에 보존하고, 소비자가 명시적으로 `copyright_display_info()`를 호출할 때만 label/주의사항을 계산한다. `detailCommon2`의 `homepage`/`overview`, `detailInfo2`의 `infotext` 같은 HTML 조각은 `clean_tourapi_html()`로 plain text 정리를 opt-in 제공하되, 보안 sanitizer 역할은 앱에 남긴다.

## 예외 매핑

```text
TourApiError
├── TourApiAuthError       # 인증키/활용신청/권한 문제
├── TourApiRateLimitError  # 호출 한도/트래픽 제한
├── TourApiRequestError    # 잘못된 파라미터 또는 4xx 계열
├── TourApiNoDataError     # 단건 상세에서 결과 없음
├── TourApiServerError     # 5xx, resultCode 99/04 계열
└── TourApiParseError      # JSON/XML 구조 또는 타입 변환 실패
```

각 `TourApiError`는 `result_code`, `status_code`, `endpoint`, `service_name`, `failure_kind`를 optional metadata로 가진다. `failure_kind`는 `auth`, `rate_limit`, `request`, `no_data`, `server`, `parse` 같은 사용자 메시지 분기용 값을 사용한다. 기존 subclass 계층은 유지하므로 `except TourApiAuthError` catch 동작은 바뀌지 않는다. 예외 문자열, `repr`, metadata에는 `serviceKey` 원문을 남기지 않는다.

## 확장 원칙

1. 공식 문서 또는 실제 응답 fixture로 endpoint와 필드를 확인한다.
2. 공개 메서드는 snake_case, 요청 파라미터는 내부에서 TourAPI 원문 이름으로 변환한다.
3. 새 필드가 불안정하면 Pydantic 필드 추가보다 `raw` 보존을 우선한다.
4. 일반 테스트는 네트워크를 사용하지 않는다.
5. 반복되는 실수를 발견하면 `docs/repeated-mistakes.md`와 guardrail test를 함께 갱신한다.

## 관련 문서

- [README.md](README.md): 빠른 시작과 public API 요약
- [docs/user-guide.md](docs/user-guide.md): 외부 프로그램에서 쓰는 흐름 중심 가이드
- [docs/pydantic-models.md](docs/pydantic-models.md): Pydantic 응답 모델과 직렬화 규칙
- [docs/openapi-catalog.md](docs/openapi-catalog.md): 전체 27개 서비스 카탈로그
- [docs/testing.md](docs/testing.md): offline/live/documentation 테스트 정책
- [docs/troubleshooting.md](docs/troubleshooting.md): 인증, 좌표, Hub, 모델 문제 해결
- [docs/repeated-mistakes.md](docs/repeated-mistakes.md): 반복 실수와 guardrail
