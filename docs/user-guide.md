# visitkorea 사용자 가이드

이 문서는 `visitkorea`를 외부 Python 프로그램에서 안정적으로 쓰기 위한 중심 가이드입니다. 빠른 예시는 `README.md`에 두고, 여기에는 인증키 관리, typed client와 전체 OpenAPI Hub 선택 기준, Pydantic 모델 사용법, 좌표 규칙, 테스트 정책까지 한 번에 모았습니다.

> 확인 기준일: 2026-04-30  
> 공식 근거: [공공데이터포털 국문 관광정보서비스_GW](https://www.data.go.kr/en/data/15101578/openapi.do), [한국관광콘텐츠랩 OpenAPI 활용신청 목록](https://api.visitkorea.or.kr/#/useUtilExercises), [TourAPI URL/입출력 변경 공지](https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004471)

## 설치

로컬 저장소에서 개발하거나 다른 프로젝트에 연결할 때는 editable install을 사용합니다.

```bash
pip install -e ".[dev]"
```

라이브러리 런타임 의존성은 `httpx`, `pydantic>=2.7`, 로컬 `python-kraddr-base @ file:../python-kraddr-base`, Windows용 `tzdata`입니다. 외부 앱에서 타입 검사를 적극적으로 쓰려면 `src/visitkorea/py.typed`가 포함되어 있으므로 `mypy`나 pyright가 공개 타입을 읽을 수 있습니다.

## 인증키

공공데이터포털에서 TourAPI 활용신청을 완료한 뒤 **Decoding 인증키**를 사용합니다. `visitkorea`는 `httpx`의 `params=`로 query string을 만들기 때문에 이미 encoding된 인증키를 넣으면 다시 encoding되어 인증 오류가 날 수 있습니다.

```bash
export KTO_SERVICE_KEY="발급받은_decoding_인증키"
```

PowerShell:

```powershell
$env:KTO_SERVICE_KEY="발급받은_decoding_인증키"
```

`KrTourApiClient.from_env()`와 `TourApiHubClient.from_env()`는 기본적으로 `KTO_SERVICE_KEY`, `KRTOURAPI_SERVICE_KEY`, `TOURAPI_SERVICE_KEY` 순서로 읽습니다.

로컬 live test에서는 `.env.local`을 사용할 수 있습니다.

```powershell
Set-Content .env.local 'KTO_SERVICE_KEY=발급받은_decoding_인증키'
.\scripts\run_live_tests.ps1
```

`.env*`는 gitignore 대상입니다. 인증키를 README, 테스트 fixture, shell script 기본값, 예시 코드에 직접 쓰지 않습니다.

## 클라이언트 선택

대부분의 국문 관광정보 조회에는 `KrTourApiClient`를 먼저 사용합니다. 이 클라이언트는 `KorService2`의 자주 쓰는 endpoint를 Python method와 Pydantic 모델로 감쌉니다.

`api.visitkorea.or.kr/#/useUtilExercises` 메뉴얼 목록의 모든 서비스를 호출해야 하면 `TourApiHubClient`를 사용합니다. Hub 클라이언트는 27개 서비스와 211개 operation 카탈로그를 알고 있지만, 결과 item은 서비스마다 모양이 달라서 `Page[Mapping]` 형태의 raw record로 반환합니다.

| 상황 | 권장 클라이언트 |
|---|---|
| 국문 관광지/행사/숙박/상세/이미지/코드 조회 | `KrTourApiClient` |
| 지도 좌표 주변 국문 관광정보 조회 | `KrTourApiClient.location_based_list()` |
| 캠핑, 관광사진, 무장애, 의료/웰니스, 지역데이터 등 별도 서비스 호출 | `TourApiHubClient` |
| 새 operation을 빠르게 실험 | `TourApiHubClient.call()` |
| typed wrapper에 없는 국문 endpoint 직접 호출 | `KrTourApiClient.raw_endpoint()` |

asyncio 기반 애플리케이션에서는 같은 메서드 이름을 `await`로 호출하는 `AsyncKrTourApiClient`와 `AsyncTourApiHubClient`를 사용합니다. 동기 클라이언트와 비동기 클라이언트는 모두 내부적으로 `httpx`를 사용합니다.

## Typed Client 기본 흐름

```python
from visitkorea import ContentType, KrTourApiClient

client = KrTourApiClient.from_env(mobile_app="my-travel-app")

page = client.search_keyword(
    "경복궁",
    content_type_id=ContentType.TOURIST_ATTRACTION,
    area_code="1",
    page_no=1,
    num_of_rows=10,
)

for item in page.items:
    print(item.content_id, item.title, item.addr1)
```

목록 endpoint는 `Page[T]`를 반환합니다. `Page.items`는 항상 tuple이고, TourAPI가 `items.item`을 빈 값, 단일 object, list 중 무엇으로 보내도 내부에서 정규화됩니다.

비동기 흐름:

```python
from visitkorea import AsyncKrTourApiClient, ContentType

async with AsyncKrTourApiClient.from_env(mobile_app="my-travel-app") as client:
    page = await client.search_keyword(
        "경복궁",
        content_type_id=ContentType.TOURIST_ATTRACTION,
    )
```

## 국문 typed method 목록

| 메서드 | endpoint | 용도 |
|---|---|---|
| `area_based_list()` | `areaBasedList2` | 지역, content type, 카테고리, 법정동, 분류체계 기반 목록 |
| `location_based_list()` | `locationBasedList2` | WGS84 좌표 주변 검색 |
| `search_keyword()` | `searchKeyword2` | 키워드 검색 |
| `search_festival()` | `searchFestival2` | 행사 시작일 기준 축제/공연/행사 검색 |
| `search_stay()` | `searchStay2` | 숙박 목록 |
| `detail_common()` | `detailCommon2` | 공통 상세 1건 |
| `detail_intro()` | `detailIntro2` | content type별 소개정보 |
| `detail_info()` | `detailInfo2` | 반복 상세정보 |
| `detail_images()` | `detailImage2` | 이미지 목록 |
| `area_based_sync_list()` | `areaBasedSyncList2` | 동기화 목록 |
| `area_codes()` | `areaCode2` | 지역/시군구 코드 |
| `category_codes()` | `categoryCode2` | 대/중/소분류 코드 |
| `legal_dong_codes()` | `ldongCode2` | 법정동 코드 |
| `classification_system_codes()` | `lclsSystmCode2` | 관광 분류체계 코드 |

## 상세 조회 패턴

목록에서 `content_id`와 `content_type_id`를 얻고 상세 endpoint를 이어 호출합니다.

```python
page = client.search_keyword("한옥", content_type_id=ContentType.TOURIST_ATTRACTION)
item = page.items[0]

if item.content_id:
    detail = client.detail_common(item.content_id)
    print(detail.title, detail.overview)

if item.content_id and item.content_type_id:
    intro = client.detail_intro(item.content_id, item.content_type_id)
    repeat = client.detail_info(item.content_id, item.content_type_id)
```

`detail_common()`은 상세 1건이 기대되는 endpoint입니다. TourAPI가 no data를 반환하면 `TourApiNoDataError`를 발생시킵니다. 목록 endpoint의 no data는 빈 `Page`로 다루는 쪽이 외부 앱에서 쓰기 편해서 `page.is_empty`로 확인합니다.

## 코드 조회와 의존성

TourAPI에는 상위 코드가 필요한 하위 코드가 많습니다. 라이브러리는 자주 반복되는 실수를 막기 위해 하위 코드만 단독으로 보낼 때 validation error를 냅니다.

| 하위 값 | 함께 필요한 값 |
|---|---|
| `sigungu_code` | `area_code` |
| `cat2` | `cat1` |
| `cat3` | `cat1`, `cat2` |
| `l_dong_signgu_cd` | `l_dong_regn_cd` |
| `lcls_systm2` | `lcls_systm1` |
| `lcls_systm3` | `lcls_systm1`, `lcls_systm2` |

코드 값은 먼저 조회한 뒤 사용하는 편이 안전합니다.

```python
seoul_sigungu = client.area_codes("1")
categories = client.category_codes(content_type_id=ContentType.TOURIST_ATTRACTION)
legal_dongs = client.legal_dong_codes(l_dong_regn_cd="11", list_yn=True)
classes = client.classification_system_codes(lcls_systm1="AC", list_yn=True)
```

## 좌표 규칙

TourAPI 원문 이름은 `mapX=경도`, `mapY=위도`입니다. 외부 프로그램에서는 `kraddr.base.PlaceCoordinate`를 직접 쓰세요. `visitkorea`도 같은 클래스를 re-export하며, 기존 `Wgs84Coordinate` 이름은 같은 클래스 alias입니다.

```python
from visitkorea import PlaceCoordinate

coord = PlaceCoordinate(lat=37.5796, lon=126.9769)

page = client.location_based_list(
    coordinate=coord,
    radius=1000,
    content_type_id=ContentType.TOURIST_ATTRACTION,
)
```

허용되는 입력:

```python
client.location_based_list(coordinate=PlaceCoordinate(lat=37.5796, lon=126.9769), radius=1000)
client.location_based_list(coordinate=(37.5796, 126.9769), radius=1000)
client.location_based_list(coordinate={"longitude": 126.9769, "latitude": 37.5796}, radius=1000)
client.location_based_list(coordinate={"mapX": 126.9769, "mapY": 37.5796}, radius=1000)
client.location_based_list(map_x=126.9769, map_y=37.5796, radius=1000)
```

튜플은 항상 `(latitude, longitude)` 또는 `(lat, lon)` 순서입니다. GeoJSON, TourAPI 원문, 일부 GIS SDK처럼 `(longitude, latitude)` 순서를 쓰는 도구와 섞을 때는 `coord.latlon`과 `coord.lonlat`을 명시적으로 선택하세요.

## Pydantic 응답 모델

공개 응답 모델은 Pydantic v2 기반의 frozen model입니다.

```python
item = page.items[0]

print(item.title)
payload = item.model_dump()
json_text = item.model_dump_json()
schema = type(item).model_json_schema()
```

모든 모델은 속성 접근을 지원하고, 원문 TourAPI record를 `raw`에 보존합니다. 공식 문서에 없거나 content type마다 달라지는 필드는 먼저 `raw`에서 확인하세요.

목록 응답에는 호출 provenance도 함께 들어갑니다. `page.context.service_name`, `page.context.endpoint`, `page.context.request_params`, `page.context.collected_at`을 raw/serving 저장용 메타데이터로 사용할 수 있습니다. `request_params`에는 `MobileOS`, `MobileApp`, `_type`과 endpoint별 파라미터만 남고 `serviceKey` 원문은 포함되지 않습니다.

자세한 내용은 [docs/pydantic-models.md](pydantic-models.md)를 참고하세요.

## 전체 OpenAPI Hub

`TourApiHubClient`는 공식 활용신청 메뉴얼의 서비스 key와 operation을 카탈로그로 갖고 있습니다.

```python
from visitkorea import TourApiHubClient

hub = TourApiHubClient.from_env(mobile_app="my-travel-app")

camping = hub.gocamping.based_list(facltNm="숲")
photos = hub.photo_gallery.gallery_search_list(galSearchKeyword="서울")
raw = hub.call("area_resource_demand", "areaTarSvcDemList", baseYm="202509", areaCd="11")
related = hub.related_tour.search_keyword(
    "뮤지엄산",
    base_ym="202504",
    area_cd="51",
    signgu_cd="51130",
)
```

operation은 원문 이름과 snake_case alias를 모두 지원합니다.

비동기 Hub도 같은 카탈로그와 alias를 사용합니다.

```python
from visitkorea import AsyncTourApiHubClient

async with AsyncTourApiHubClient.from_env(mobile_app="my-travel-app") as hub:
    camping = await hub.gocamping.based_list(facltNm="숲")
    related = await hub.related_tour.search_keyword(
        "뮤지엄산",
        base_ym="202504",
        area_cd="51",
        signgu_cd="51130",
    )
```

```python
hub.gocamping.based_list()
hub.gocamping.call("basedList")
hub.call("gocamping", "basedList")
```

Python식 파라미터 alias:

| Python 이름 | TourAPI 이름 |
|---|---|
| `page_no` | `pageNo` |
| `num_of_rows` | `numOfRows` |
| `content_id` | `contentId` |
| `content_type_id` | `contentTypeId` |
| `mobile_os` | `MobileOS` |
| `mobile_app` | `MobileApp` |
| `coordinate` | `mapX`, `mapY` |

`related_tour` 서비스는 typed helper도 제공합니다. `hub.related_tour.area_based_list(...)`와 `hub.related_tour.search_keyword(...)`는 `Page[RelatedTourItem]`을 반환합니다. 이때 `area_cd`와 `signgu_cd`는 TarRlteTarService1의 TourAPI 지역 코드(`areaCd`, `signguCd`)이며 법정동코드가 아닙니다. 기존 generic `hub.call("related_tour", ...)`은 계속 raw `Page[Mapping]`을 반환합니다.

서비스 key와 operation 전체 목록은 [docs/openapi-catalog.md](openapi-catalog.md)에 있습니다.

## 페이지 반복

`Page.has_next_page`와 `Page.next_page_no`는 `total_count`, `page_no`, `num_of_rows`를 기준으로 다음 페이지 여부를 계산합니다. 코드 캐시나 후보 조회처럼 여러 페이지를 읽어야 하는 흐름에서는 `iter_pages()`를 사용할 수 있습니다.

```python
for page in client.iter_pages(client.area_codes, num_of_rows=100, max_pages=20):
    for code in page.items:
        ...

for page in hub.iter_pages("kor", "areaCode2", num_of_rows=100, max_pages=20):
    for row in page.items:
        ...
```

async 클라이언트에서는 `async for`를 사용합니다.

```python
async for page in client.iter_pages(client.area_codes, num_of_rows=100, max_pages=20):
    for code in page.items:
        ...

async for page in hub.iter_pages("kor", "areaCode2", num_of_rows=100, max_pages=20):
    for row in page.items:
        ...
```

`max_pages` 또는 `max_items`를 지정하면 비정상 응답으로 인한 긴 반복을 제한할 수 있습니다. 목록 API의 `NO_DATA` 응답은 빈 iterator로 끝나며, 인증/쿼터/서버 오류는 기존 typed exception으로 그대로 올라옵니다.

`related_tour` typed helper는 endpoint별 iterator도 제공합니다.

```python
for page in hub.related_tour.iter_search_keyword(
    "뮤지엄산",
    base_ym="202504",
    area_cd="51",
    signgu_cd="51130",
    max_pages=10,
):
    for item in page.items:
        ...
```

## 다국어 서비스

`KrTourApiClient`는 `language=`로 같은 endpoint 계열의 다국어 서비스를 선택할 수 있습니다.

```python
from visitkorea import Language

client = KrTourApiClient.from_env(language=Language.ENGLISH)
```

지원 값은 `ko`, `en`, `ja`/`jp`, `zh-cn`/`zh`, `zh-tw`, `de`, `fr`, `es`, `ru`입니다. 다만 공공데이터포털에서 해당 언어 서비스를 따로 활용신청하지 않은 인증키는 HTTP 403 또는 인증 오류가 날 수 있습니다. 이 경우 라이브러리는 `TourApiAuthError`로 매핑합니다.

## 예외 처리

```python
from visitkorea import (
    TourApiAuthError,
    TourApiError,
    TourApiNoDataError,
    TourApiRateLimitError,
)

try:
    page = client.search_keyword("경복궁")
except TourApiAuthError:
    raise RuntimeError("TourAPI 인증키 또는 활용신청 상태를 확인하세요.")
except TourApiRateLimitError:
    raise RuntimeError("호출 한도 또는 트래픽 제한에 도달했습니다.")
except TourApiNoDataError:
    page = None
except TourApiError as exc:
    raise RuntimeError(f"TourAPI 호출 실패: {exc}") from exc
```

예외 계층:

```text
TourApiError
├── TourApiAuthError
├── TourApiRateLimitError
├── TourApiRequestError
├── TourApiNoDataError
├── TourApiServerError
└── TourApiParseError
```

모든 `TourApiError` 계열 예외에는 관리자 로그용 metadata가 optional 속성으로 들어갑니다. 기존 subclass catch 동작은 그대로 유지되므로 `except TourApiAuthError` 같은 분기는 바꾸지 않아도 됩니다.

```python
except TourApiError as exc:
    logger.warning("tourapi_failed", extra={"tourapi": exc.metadata})
    user_message = {
        "auth": "TourAPI 인증 설정을 확인하세요.",
        "rate_limit": "TourAPI 호출 한도에 도달했습니다.",
        "no_data": "조회 가능한 관광정보가 없습니다.",
        "server": "TourAPI 서버 응답이 불안정합니다.",
        "request": "검색 조건을 다시 확인하세요.",
        "parse": "TourAPI 응답을 해석하지 못했습니다.",
    }.get(exc.failure_kind, "TourAPI 호출에 실패했습니다.")
```

`exc.metadata`에는 `result_code`, `status_code`, `endpoint`, `service_name`, `failure_kind`가 들어갑니다. `serviceKey` 원문은 예외 문자열, `repr`, metadata 어디에도 남기지 않습니다.

## CLI

간단한 확인에는 CLI를 사용할 수 있습니다.

```bash
visitkorea keyword 경복궁 --content-type-id 12
visitkorea location --map-x 126.9769 --map-y 37.5796 --radius 1000
visitkorea detail 126508
visitkorea area-codes
```

CLI 출력은 Pydantic 모델을 `model_dump()`한 뒤 JSON으로 직렬화합니다.

## 테스트

기본 테스트는 네트워크를 사용하지 않습니다.

```bash
python -m compileall src/visitkorea tests
python -m pytest
python -m pytest --cov=visitkorea --cov-fail-under=90
ruff check .
mypy src/visitkorea
```

live test는 별도로 실행합니다.

```powershell
.\scripts\run_live_tests.ps1
```

live test에서는 실 관광 데이터의 제목, 개수, 정렬 순서 같은 변동값을 고정하지 않습니다. 응답 shape, 타입, 예외 매핑처럼 계약에 가까운 값만 확인합니다.

## 문서 갱신 규칙

API 동작이나 public type을 바꿀 때는 README만 고치지 말고 관련 문서를 함께 확인합니다.

- 새 사용 흐름: `docs/user-guide.md`
- Pydantic 모델/직렬화: `docs/pydantic-models.md`
- 전체 서비스 카탈로그: `docs/openapi-catalog.md`
- 테스트 정책: `docs/testing.md`
- 장애 대응: `docs/troubleshooting.md`
- 반복 실수와 guardrail: `docs/repeated-mistakes.md`

반복 실수를 발견하면 증상, 원인, 규칙, 가드레일 테스트를 `docs/repeated-mistakes.md`에 남깁니다.
