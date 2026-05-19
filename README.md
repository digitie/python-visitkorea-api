# python-visitkorea-api

`visitkorea`는 한국관광공사(KTO) TourAPI를 Python 애플리케이션에서 다루기 쉽게 감싼 비공식 클라이언트입니다.

기본 typed 클라이언트는 공공데이터포털의 **한국관광공사_국문 관광정보서비스_GW** (`KorService2`)를 대상으로 합니다. 한국관광콘텐츠랩 OpenAPI 활용신청 목록에 있는 전체 27개 서비스, 211개 operation은 `TourApiHubClient`로 호출할 수 있습니다.

> 확인 기준일: 2026-04-30  
> 공식 근거: [공공데이터포털 국문 관광정보서비스_GW](https://www.data.go.kr/en/data/15101578/openapi.do), [한국관광콘텐츠랩 OpenAPI 활용신청 목록](https://api.visitkorea.or.kr/#/useUtilExercises), [2026-01-09 TourAPI URL/입출력 변경 공지](https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004471)

## 특징

- `KorService2` typed wrapper: 지역/위치/키워드/행사/숙박/상세/이미지/동기화/코드 조회
- `TourApiHubClient`: 공식 활용신청 목록 27개 서비스 전체 operation generic 호출
- Pydantic v2 기반 frozen 응답 모델: `model_dump()`, `model_dump_json()`, `model_json_schema()` 지원
- `kraddr.base.PlaceCoordinate`로 위경도 표준화: `lat`/`lon` public DTO를 TourAPI `mapY`/`mapX`로 변환
- `items.item`이 빈 값, 단일 object, list로 오는 차이를 내부에서 정규화
- HTTP status, TourAPI `resultCode`, XML 인증 오류를 typed exception으로 매핑
- 예외 metadata로 관리자 로그와 사용자 메시지 분리 지원
- KTO 이미지 저작권 코드와 HTML형 설명 필드를 앱에서 표시하기 위한 opt-in helper 제공
- 기본 테스트는 실제 API를 호출하지 않는 offline mock 방식

## 설치

개발 중인 로컬 저장소에서는:

```bash
pip install -e ".[dev]"
```

패키지 런타임 의존성은 `httpx`, `pydantic>=2.7`, 로컬 `python-kraddr-base @ file:../python-kraddr-base`, Windows용 `tzdata`입니다.

## 인증키

공공데이터포털에서 API 활용신청 후 **Decoding 인증키**를 환경변수에 넣는 방식을 권장합니다. 이 라이브러리는 `httpx`의 `params=`로 query string을 만들기 때문에 이미 encoding된 키를 다시 encoding하지 않도록 주의하세요.

```bash
export KTO_SERVICE_KEY="발급받은_decoding_인증키"
```

PowerShell:

```powershell
$env:KTO_SERVICE_KEY="발급받은_decoding_인증키"
```

대체 환경변수로 `KTO_DATA_GO_KR_SERVICE_KEY`, `DATA_GO_KR_SERVICE_KEY`, `DATA_GOKR_SERVICE_KEY`, `KRTOURAPI_SERVICE_KEY`, `TOURAPI_SERVICE_KEY`도 읽습니다. 복사/붙여넣기 중 들어간 공백, 줄바꿈, 탭은 요청 전에 자동 제거합니다.

환경변수가 없으면 현재 작업 디렉터리나 상위 디렉터리의 `.env`에서 같은 이름을 읽습니다.

```bash
KTO_DATA_GO_KR_SERVICE_KEY=발급받은_decoding_인증키
```

`api.visitkorea.or.kr` 쪽 키가 별도로 필요한 도구에서는 `VISITKOREA_API_SERVICE_KEY`, `API_VISITKOREA_SERVICE_KEY`, `KTO_VISITKOREA_SERVICE_KEY`를 사용할 수 있습니다.

로컬 live test를 돌릴 때는 저장소에 커밋되지 않는 `.env.local`을 사용할 수 있습니다.

```powershell
Set-Content .env.local 'KTO_SERVICE_KEY=발급받은_decoding_인증키'
.\scripts\run_live_tests.ps1
```

`.env*`는 gitignore 대상입니다. 인증키는 테스트 코드, 문서 예시, shell script 기본값에 직접 쓰지 않습니다.

## 빠른 시작

```python
from visitkorea import ContentType, KrTourApiClient

client = KrTourApiClient.from_env(mobile_app="my-travel-app")

page = client.search_keyword(
    "경복궁",
    content_type_id=ContentType.TOURIST_ATTRACTION,
    l_dong_regn_cd="11",
)

for item in page.items:
    print(item.content_id, item.title, item.addr1, item.coordinate)

detail = client.detail_common(page.items[0].content_id)
print(detail.overview)
```

asyncio 애플리케이션에서는 같은 public method 이름을 제공하는 async 클라이언트를 사용합니다.

```python
from visitkorea import AsyncKrTourApiClient, ContentType

async with AsyncKrTourApiClient.from_env(mobile_app="my-travel-app") as client:
    page = await client.search_keyword(
        "경복궁",
        content_type_id=ContentType.TOURIST_ATTRACTION,
    )
```

## Typed Client

`KrTourApiClient`는 자주 쓰는 국문 관광정보서비스를 typed method로 제공합니다.
`AsyncKrTourApiClient`는 같은 메서드를 `await` 가능한 형태로 제공합니다.

| 메서드 | TourAPI endpoint | 반환 |
|---|---|---|
| `area_based_list()` | `areaBasedList2` | `Page[TourItem]` |
| `location_based_list()` | `locationBasedList2` | `Page[TourItem]` |
| `search_keyword()` | `searchKeyword2` | `Page[TourItem]` |
| `search_festival()` | `searchFestival2` | `Page[TourItem]` |
| `search_stay()` | `searchStay2` | `Page[TourItem]` |
| `detail_common()` | `detailCommon2` | `TourDetail` |
| `detail_intro()` | `detailIntro2` | `Page[IntroInfo]` |
| `detail_info()` | `detailInfo2` | `Page[RepeatInfo]` |
| `detail_images()` | `detailImage2` | `Page[ImageInfo]` |
| `area_based_sync_list()` | `areaBasedSyncList2` | `Page[TourItem]` |
| `area_codes()` | `areaCode2` | `Page[CodeItem]` |
| `category_codes()` | `categoryCode2` | `Page[CodeItem]` |
| `legal_dong_codes()` | `ldongCode2` | `Page[CodeItem]` |
| `classification_system_codes()` | `lclsSystmCode2` | `Page[CodeItem]` |
| `raw_endpoint()` | 임의 endpoint | `Page[Mapping]` |

## 전체 OpenAPI Hub

`TourApiHubClient`는 `api.visitkorea.or.kr/#/useUtilExercises`의 메뉴얼 27개 기준 전체 서비스를 generic 방식으로 호출합니다. 서비스별 파라미터는 메뉴얼 원문 이름을 그대로 전달하고, 결과는 공통 `Page[Mapping]`으로 받습니다.
`AsyncTourApiHubClient`도 같은 카탈로그와 operation alias를 사용합니다.

```python
from visitkorea import PlaceCoordinate, TourApiHubClient

hub = TourApiHubClient.from_env(mobile_app="my-travel-app")

camping = hub.gocamping.based_list(facltNm="숲")

photos = hub.photo_gallery.gallery_search_list(galSearchKeyword="서울")

nearby_pet = hub.pet.location_based_list(
    coordinate=PlaceCoordinate(lat=37.5796, lon=126.9769),
    radius=1000,
)

related = hub.related_tour.area_based_list(
    base_ym="202504",
    area_cd="51",
    signgu_cd="51130",
)
```

`page_no`, `num_of_rows`, `content_id`, `content_type_id`, `coordinate`는 Python식 이름으로 넘길 수 있고, 내부에서 TourAPI 원문 파라미터로 변환됩니다. 전체 서비스 key와 operation 목록은 [docs/openapi-catalog.md](docs/openapi-catalog.md)에 정리되어 있습니다.

디버그 UI나 내부 도구에서 전체 API 목록이 필요하면 `get_api_catalog()`를 사용합니다. 각 행에는 사람이 읽을 수 있는 `dataset_name`, `operation`, `service_key_apply_url`, `manual_url`, `data_source`, `service_key_env_names`가 들어 있습니다.

```python
from visitkorea import get_api_catalog

for row in get_api_catalog():
    print(row["dataset_name"], row["operation"], row["service_key_apply_url"])
```

`related_tour`의 `area_based_list()`와 `search_keyword()`는 `Page[RelatedTourItem]`을 반환하는 typed helper입니다. 기존 generic `hub.call("related_tour", ...)` 경로는 원래처럼 `Page[Mapping]`을 반환합니다.

페이지 반복은 client가 대신 처리할 수 있습니다. `Page.has_next_page`/`next_page_no`는 `total_count`, `page_no`, `num_of_rows` 기준으로 계산되며, iterator에는 `max_pages` 또는 `max_items` guard를 둘 수 있습니다.

```python
for page in client.iter_pages(client.area_codes, num_of_rows=100, max_pages=20):
    cache_codes(page.items)

for page in hub.iter_pages("kor", "areaCode2", num_of_rows=100, max_pages=20):
    cache_raw_codes(page.items)

for page in hub.related_tour.iter_area_based_list(
    base_ym="202504",
    area_cd="51",
    signgu_cd="51130",
    num_of_rows=50,
    max_pages=10,
):
    store_related(page.items)
```

async 클라이언트의 페이지 반복은 async iterator입니다.

```python
async for page in client.iter_pages(client.area_codes, num_of_rows=100, max_pages=20):
    cache_codes(page.items)

async for page in hub.iter_pages("kor", "areaCode2", num_of_rows=100, max_pages=20):
    cache_raw_codes(page.items)
```

## Pydantic 모델

응답 모델은 Pydantic v2 `BaseModel` 기반이며 frozen 설정을 사용합니다. 기존처럼 속성 접근을 쓰면서도, 외부 앱에서는 Pydantic 직렬화와 JSON schema를 사용할 수 있습니다.

```python
item = page.items[0]

print(item.title)
payload = item.model_dump()
json_text = item.model_dump_json()
schema = type(item).model_json_schema()
```

TourAPI 원문 응답은 각 모델의 `raw` 필드에 보존합니다. 아직 안정적으로 모델링하지 않은 content-type별 필드는 `raw`에서 확인하세요.

목록 응답의 호출 provenance는 `Page.context`에 보존합니다. `service_name`, `endpoint`, `request_params`, `collected_at`을 제공하며, `request_params`에는 `MobileOS`, `MobileApp`, `_type`과 endpoint별 파라미터만 남기고 `serviceKey` 원문은 저장하지 않습니다.

모델 직렬화, JSON schema, frozen 모델 사용법은 [docs/pydantic-models.md](docs/pydantic-models.md)에 더 자세히 정리했습니다.

## 표시 helper

`cpyrhtDivCd`는 `TourItem`, `TourDetail`, `ImageInfo`의 `copyright_division_code`에 원문 코드로 보존됩니다. 앱에서 별도 문자열 매핑을 만들지 않도록 `copyright_display_info()`가 표시 label과 주의사항을 반환합니다. 알 수 없는 코드는 `raw_code`와 `code`에 그대로 남겨 후속 확인이 가능하게 합니다.

```python
from visitkorea import clean_tourapi_html, copyright_display_info

image = client.detail_images("126508").items[0]
copyright_info = copyright_display_info(image.copyright_division_code)
print(copyright_info.label, copyright_info.notice)

detail = client.detail_common("126508")
overview_text = clean_tourapi_html(detail.overview)
homepage_text = clean_tourapi_html(detail.homepage)

repeat = client.detail_info("126508", "25").items[0]
info_text = clean_tourapi_html(repeat.info_text)
```

`clean_tourapi_html()`은 `detailCommon2`의 `homepage`/`overview`, `detailInfo2`의 `infotext`처럼 HTML 조각이 섞일 수 있는 문자열을 plain text로 정리하는 opt-in helper입니다. 보안 sanitizer가 아니므로 HTML을 그대로 렌더링하는 앱은 자체 sanitizer를 계속 적용하세요. 기본 parsing 결과와 각 모델의 `raw`는 바뀌지 않습니다.

## 좌표 규칙

TourAPI 원문은 `mapX=경도`, `mapY=위도`를 사용합니다. `visitkorea`의 public API는 `kraddr.base.PlaceCoordinate`를 직접 사용하며, 공개 DTO 축 순서는 `(lat, lon)`입니다.

```python
from visitkorea import PlaceCoordinate

coord = PlaceCoordinate(lat=37.5796, lon=126.9769)

client.location_based_list(coordinate=coord, radius=1000)
client.location_based_list(coordinate=(37.5796, 126.9769), radius=1000)
client.location_based_list(map_x=126.9769, map_y=37.5796, radius=1000)  # 기존 호환
```

튜플 좌표는 `(latitude, longitude)` 또는 `(lat, lon)` 순서입니다. GeoJSON이나 TourAPI 원문 `(lon, lat)` 순서와 섞지 않도록 주의하세요. 기존 `Wgs84Coordinate` 이름은 `PlaceCoordinate`와 같은 클래스 alias로 남겨 둡니다.

## Enum과 타입

외부 프로그램에서 문자열 상수를 직접 흩뿌리지 않도록 주요 enum과 타입 alias를 공개합니다.

```python
from visitkorea import AreaCode, ContentType, Language

client = KrTourApiClient.from_env(language=Language.KOREAN)
page = client.area_based_list(
    area_code=AreaCode.SEOUL,
    content_type_id=ContentType.TOURIST_ATTRACTION,
)
```

주요 공개 타입:

- `Language`, `MobileOS`, `Arrange`
- `AreaCode`, `ContentType`
- `PlaceCoordinate`, `Wgs84Coordinate` (`PlaceCoordinate` alias)
- `RelatedTourItem`
- `CopyrightDisplayInfo`, `copyright_display_info`, `clean_tourapi_html`
- `ServiceKey`, `ContentId`, `DateInput`, `CoordinateInput`, `AreaCodeInput`

## 다른 언어 서비스

동일한 endpoint 이름을 따르는 다국어 서비스는 `language=`로 선택할 수 있습니다. 단, 공공데이터포털에서 해당 서비스를 활용신청하지 않은 인증키로 호출하면 HTTP 403 또는 인증 오류가 날 수 있습니다.

```python
client = KrTourApiClient.from_env(language="en")  # EngService2
```

지원 값: `ko`, `en`, `ja`/`jp`, `zh-cn`/`zh`, `zh-tw`, `de`, `fr`, `es`, `ru`

## 예외 metadata

모든 `TourApiError` 계열 예외는 기존 `except TourApiAuthError` 같은 catch 동작을 유지하면서 `result_code`, `status_code`, `endpoint`, `service_name`, `failure_kind` metadata를 제공합니다. 관리자 로그에는 `exc.metadata`를 남기고, 사용자 메시지는 `failure_kind`로 분기할 수 있습니다. `serviceKey` 원문은 예외 문자열, `repr`, metadata에 포함하지 않습니다.

## CLI

```bash
visitkorea keyword 경복궁 --content-type-id 12
visitkorea location --map-x 126.9769 --map-y 37.5796 --radius 1000
visitkorea detail 126508
visitkorea area-codes
```

## 개발과 테스트

```bash
python -m compileall src/visitkorea tests
python -m pytest
python -m pytest --cov=visitkorea --cov-fail-under=90
ruff check .
mypy src/visitkorea
```

기본 테스트는 실제 TourAPI를 호출하지 않습니다. live test는 `@pytest.mark.live`로 분리하고, `KTO_SERVICE_KEY`가 없으면 skip합니다.

Streamlit 디버그 UI는 선택 기능입니다.

```bash
pip install -e ".[debug-ui]"
streamlit run debug_ui/app.py
```

## 문서

- [docs/user-guide.md](docs/user-guide.md): 설치부터 typed client, Hub, Pydantic, 좌표, 테스트까지 한 번에 보는 사용자 가이드
- [docs/pydantic-models.md](docs/pydantic-models.md): Pydantic v2 응답 모델, 직렬화, JSON schema, `raw` 보존 규칙
- [krtourapi-api.md](krtourapi-api.md): 구현 원칙과 응답/예외 매핑 메모
- [docs/openapi-catalog.md](docs/openapi-catalog.md): 27개 서비스와 operation 카탈로그
- [docs/testing.md](docs/testing.md): 테스트 정책
- [docs/troubleshooting.md](docs/troubleshooting.md): 문제 해결
- [docs/repeated-mistakes.md](docs/repeated-mistakes.md): 반복 실수 방지 규칙

## 라이선스

GPL-3.0-or-later.
