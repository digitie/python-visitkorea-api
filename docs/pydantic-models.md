# Pydantic 모델 가이드

`visitkorea`의 공개 응답 모델은 Pydantic v2 `BaseModel`을 상속한 `TourApiModel` 기반입니다. 목표는 기존 dataclass처럼 가볍게 속성 접근을 유지하면서도 외부 프로그램이 검증, 직렬화, JSON schema를 바로 활용할 수 있게 하는 것입니다.

## 모델 원칙

- 모델은 `ConfigDict(frozen=True)`로 frozen 처리합니다.
- TourAPI 원문 record는 `raw` 필드에 보존합니다.
- 목록 응답의 호출 출처는 `Page.context`에 보존합니다.
- 안정적으로 공통화할 수 있는 필드만 typed field로 승격합니다.
- content type 또는 서비스마다 달라지는 필드는 무리하게 모델 필드로 고정하지 않습니다.
- 목록 응답은 `Page[T]`로 감싸고, `items`는 항상 tuple입니다.

## 기본 사용

```python
from visitkorea import ContentType, KrTourApiClient

client = KrTourApiClient.from_env()
page = client.search_keyword("경복궁", content_type_id=ContentType.TOURIST_ATTRACTION)
item = page.items[0]

print(item.title)
print(item.model_dump())
print(item.model_dump_json())
```

`Page`도 Pydantic 모델입니다.

```python
payload = page.model_dump()
assert isinstance(payload["items"], tuple)
assert page.has_next_page is False
```

JSON으로 외부 API 응답을 만들 때는 Pydantic의 JSON mode를 쓰는 편이 날짜 처리에 안전합니다.

```python
payload = page.model_dump(mode="json")
json_text = page.model_dump_json()
```

## Page context

`Page.context`에는 호출 provenance가 들어갑니다. `service_name`, `endpoint`, `request_params`, `collected_at`을 확인할 수 있고, `request_params`에는 `MobileOS`, `MobileApp`, `_type`과 endpoint별 파라미터만 남깁니다. 인증키 원문인 `serviceKey`는 저장하지 않습니다.

```python
page = client.search_keyword("경복궁", content_type_id=ContentType.TOURIST_ATTRACTION)

print(page.context.service_name)     # KorService2
print(page.context.endpoint)         # searchKeyword2
print(page.context.request_params)   # serviceKey 없음
print(page.context.collected_at)
```

자주 쓰는 값은 `page.endpoint`, `page.request_params`처럼 `Page` 속성으로도 바로 읽을 수 있습니다.

## JSON schema

외부 프로그램에서 응답 계약을 문서화하거나 검증할 때 JSON schema를 사용할 수 있습니다.

```python
from visitkorea import TourItem

schema = TourItem.model_json_schema()
```

`Page[TourItem]`처럼 generic page의 schema가 필요하면 Pydantic generic model을 그대로 사용합니다.

```python
from visitkorea import Page, TourItem

schema = Page[TourItem].model_json_schema()
```

## raw 필드

TourAPI는 endpoint, content type, 실제 데이터 상태에 따라 필드가 자주 달라집니다. 라이브러리는 공통 필드를 typed field로 제공하되 원문 전체를 `raw`에 남깁니다.

```python
detail = client.detail_common("126508")

print(detail.title)
print(detail.raw.get("homepage"))
```

content type별 소개정보인 `IntroInfo`, 반복 상세정보인 `RepeatInfo`는 특히 `raw`가 중요합니다. 문서에 보이는 필드를 모두 public field로 고정하면 다른 content type에서 누락이나 오해가 생기기 쉽기 때문입니다.

## Frozen 모델

모델은 불변 객체처럼 다룹니다.

```python
item = page.items[0]
updated = item.model_copy(update={"title": "새 제목"})
```

직접 대입은 허용하지 않습니다.

```python
# item.title = "새 제목"  # ValidationError
```

외부 앱에서 캐시 키, 이벤트 payload, API response DTO로 재사용할 때 accidental mutation을 줄이기 위한 선택입니다.

## 좌표 모델

좌표 값은 `kraddr.base.PlaceCoordinate`를 직접 사용합니다. `visitkorea`는 같은 클래스를 `PlaceCoordinate`로 re-export하고, 기존 `Wgs84Coordinate` 이름도 같은 클래스 alias로 남겨 둡니다.

```python
from visitkorea import PlaceCoordinate, Wgs84Coordinate

coord = PlaceCoordinate(lat=37.5796, lon=126.9769)

assert Wgs84Coordinate is PlaceCoordinate
assert coord.map_x == coord.lon
assert coord.map_y == coord.lat
assert coord.lonlat == (126.9769, 37.5796)
assert coord.latlon == (37.5796, 126.9769)
```

TourAPI 요청 직전에는 client가 `PlaceCoordinate.lon`/`lat`를 `mapX`/`mapY`로 직접 옮깁니다.

```python
assert {"mapX": coord.lon, "mapY": coord.lat} == {"mapX": 126.9769, "mapY": 37.5796}
```

## 모델 목록

| 모델 | 용도 |
|---|---|
| `TourApiModel` | 모든 공개 Pydantic 모델의 base class |
| `TourApiCallContext` | 응답을 만든 TourAPI 호출 provenance |
| `Page[T]` | 목록, 검색, 이미지, 코드 조회의 공통 pagination wrapper |
| `TourItem` | 목록/검색 item 공통 필드 |
| `RelatedTourItem` | TarRlteTarService1 관광지별 연관 관광지 record |
| `TourDetail` | `detailCommon2` 공통 상세 |
| `CodeItem` | 지역, 카테고리, 법정동, 분류체계 코드 |
| `IntroInfo` | content type별 소개정보 |
| `RepeatInfo` | 반복 상세정보 |
| `ImageInfo` | 이미지 메타데이터 |
| `PlaceCoordinate` | `kraddr.base`의 WGS84 경도/위도 값 객체 |
| `Wgs84Coordinate` | `PlaceCoordinate`와 같은 클래스 alias |

## 직렬화 예시

FastAPI 같은 웹 프레임워크에 넘길 때는 dict로 변환합니다.

```python
def as_response(page):
    return page.model_dump(mode="json")
```

로그나 메시지 큐에는 JSON string을 직접 사용할 수 있습니다.

```python
event_body = page.model_dump_json()
```

원문 응답을 제외하고 싶다면 `exclude`를 사용합니다.

```python
public_payload = item.model_dump(exclude={"raw"}, mode="json")
```

## 마이그레이션 메모

이전 dataclass 스타일에서 넘어올 때 주의할 점:

- `dataclasses.asdict()` 대신 `model_dump()`를 사용합니다.
- 객체 수정은 직접 대입 대신 `model_copy(update=...)`를 사용합니다.
- 원문 필드 확인은 여전히 `raw`를 사용합니다.
- `Page.items`는 list가 아니라 tuple입니다. 필요한 경우 `list(page.items)`로 바꿉니다.

## 테스트 가드레일

Pydantic 모델 관련 변경은 아래 항목을 깨지 않아야 합니다.

- typed field와 `raw`가 함께 보존되는지
- `model_dump()`와 CLI JSON 출력이 정상인지
- `PlaceCoordinate` 범위 검증과 `mapX`/`mapY` 변환이 유지되는지
- frozen model 특성이 문서와 일치하는지
