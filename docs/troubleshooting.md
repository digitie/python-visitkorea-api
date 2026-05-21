# Troubleshooting

## `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`

가능한 원인:

- 인증키를 잘못 복사했다.
- Encoding 키를 `params=`에 넣어 이중 인코딩됐다.
- 해당 API 활용 신청이 아직 승인되지 않았다.
- 기존 서비스 URL에서 `KorService2`로 재신청이 필요하다.

해결:

1. 공공데이터포털 마이페이지에서 Decoding 키를 확인한다.
2. `DATA_GO_KR_SERVICE_KEY`에 Decoding 키를 넣는다.
3. 국문 관광정보서비스_GW 활용 신청 상태를 확인한다.

## 결과가 비어 있음

가능한 원인:

- `resultCode=03`인 정상적인 데이터 없음 응답
- `eventStartDate`, `modifiedtime` 날짜 범위가 너무 좁음
- `sigunguCode`만 보내고 `areaCode`를 누락
- `lDongSignguCd`만 보내고 `lDongRegnCd`를 누락
- 분류체계 하위 코드만 단독 전달

해결:

- 필터를 하나씩 줄여가며 확인한다.
- 코드 조회 메서드로 실제 코드 값을 먼저 가져온다.
- 라이브러리 validation 오류가 나면 상위 코드를 함께 전달한다.

## JSON 파싱 실패

TourAPI는 `_type=json` 요청에도 인증키/권한 오류를 XML로 돌려줄 수 있다. `visitkorea`는 알려진 XML 오류 envelope를 파싱해 `TourApiAuthError` 등으로 바꾼다. 그래도 `TourApiParseError`가 난다면 응답 본문 일부를 확인하고 새 envelope 형태를 테스트로 추가한다.

## HTTP 403 Forbidden

가능한 원인:

- 해당 서비스 활용신청이 되어 있지 않다. 예를 들어 국문만 신청한 키로 `EngService2`를 호출하면 403이 날 수 있다.
- TourAPI 게이트웨이가 기본 Python HTTP 클라이언트 User-Agent를 차단한다.
- 인증키가 잘못되었거나 승인 전이다.

해결:

- 신청된 서비스 URL인지 먼저 확인한다.
- `visitkorea` 기본 세션은 브라우저 호환 User-Agent를 설정한다. 커스텀 session을 넘길 때도 User-Agent를 지정한다.
- live test에서는 미신청 서비스의 403을 `TourApiAuthError` 매핑 검증에 사용한다.

## `radius must be between 1 and 20000 meters`

`locationBasedList2`의 반경은 공식 문서 기준 최대 20km다. 더 넓은 검색이 필요하면 행정구역 기반 조회와 후처리를 사용한다.

## 좌표 검색 결과가 예상 지역과 다름

가능한 원인:

- `(latitude, longitude)` 순서의 tuple을 그대로 넘겼다.
- TourAPI 원문 이름 `mapX`, `mapY`를 보고 `mapX=위도`, `mapY=경도`로 착각했다.
- 좌표계가 WGS84가 아닌 TM, UTM-K, EPSG:5179 같은 국내 좌표계다.

해결:

- public API에서는 `PlaceCoordinate(lat=..., lon=...)`를 우선 사용한다. `Wgs84Coordinate`는 같은 클래스 alias다. TourAPI 전송 직전에만 `mapX=lon`, `mapY=lat`로 변환한다.
- tuple을 쓸 때는 `(latitude, longitude)` 순서로만 넘긴다.
- TourAPI 요청 직전 변환은 `coord.lon`이 `mapX`, `coord.lat`이 `mapY`로 들어간다는 기준으로 확인한다.

## `AttributeError` 또는 unknown operation

`TourApiHubClient`의 동적 호출은 공식 메뉴얼 카탈로그에 있는 service key와 operation 이름을 기준으로 한다.

가능한 원인:

- 서비스 key를 잘못 썼다. 예: `photo`가 아니라 `photo_gallery`
- operation alias가 중복되어 자동 snake_case alias가 비활성화됐다.
- 메뉴얼에 보이는 오탈자와 실제 URL 패턴이 다르다.

해결:

- [openapi-catalog.md](openapi-catalog.md)에서 service key와 operation을 확인한다.
- 애매할 때는 동적 method 대신 원문 operation 이름으로 호출한다.

```python
hub.call("gocamping", "basedList")
hub.service("gocamping").call("basedList")
```

## Pydantic 모델을 수정하려다 오류가 남

응답 모델은 frozen model이다. 외부 앱에서 accidental mutation을 줄이기 위해 직접 대입을 막는다.

해결:

```python
updated = item.model_copy(update={"title": "새 제목"})
payload = item.model_dump(mode="json")
```

dict가 필요하면 `dataclasses.asdict()`가 아니라 `model_dump()`를 사용한다. 더 자세한 내용은 [pydantic-models.md](pydantic-models.md)를 참고한다.

## 원문 필드가 typed 모델에 없음

TourAPI는 content type과 서비스마다 item 필드가 조금씩 다르다. 안정적으로 공통화하기 어려운 필드는 public field로 고정하지 않고 `raw`에 보존한다.

```python
value = item.raw.get("문서에만_있는_필드명")
```

새 typed field를 추가하려면 실제 fixture 또는 공식 메뉴얼 근거를 먼저 확인하고, 기존 content type에서 깨지지 않는지 테스트를 추가한다.

## 한글이 터미널에서 깨져 보임

Windows PowerShell의 출력 인코딩 문제일 수 있다. 파일이 깨졌다고 가정하기 전에 Python에서 UTF-8로 읽거나 테스트 문자열 비교로 확인한다.
