# Agent Notes

이 저장소는 작은 typed Python package다. 변경은 좁게 유지하고, test와 문서를 함께 갱신한다.

## 문서 언어 정책

이 저장소의 모든 Markdown/RST 문서는 한글로 작성한다. 공식 API field, code identifier, 명령어, URL, provider 원문은 필요한 경우 원문을 유지한다.

## Direct public API rule

- 외부 API 작업을 시작하기 전 provider-specific wrapper, adapter, gateway layer를 만들지 않는다는 규칙을 먼저 적용한다.
- Downstream 사용자가 직접 호출할 수 있는 안정 public client, typed model, enum, helper를 제공한다.
- TripMate나 `python-krtour-map`에 endpoint, pagination, cursor, exception, raw payload 계약이 부족하면 downstream facade가 아니라 이 package에서 안정화한다.
- 호출 code를 stable public API로 갱신할 수 있으면 long-lived compatibility alias나 pass-through wrapper를 유지하지 않는다.
- 다른 library의 검증된 구현을 재사용할 때는 license/source를 확인하고, 감싸지 말고 이 package에 통합한다.

## 공개 동작 수정 전

1. `README.md`를 읽는다.
2. `krtourapi-api.md`를 읽는다.
3. `docs/repeated-mistakes.md`를 확인한다.
4. Fixture화가 쉬운 동작은 offline test를 먼저 추가/갱신한다.

## Module ownership

```text
src/visitkorea/
├── client.py       # 공개 client method와 response parsing
├── hub.py          # 모든 공식 TourAPI service를 위한 catalog-aware generic client
├── services.py     # official manual catalog를 service definition으로 정리
├── _http.py        # httpx client, TourAPI envelope, error mapping
├── _convert.py     # 작은 변환 helper
├── _time.py        # KST timestamp parsing
├── enums.py        # 공개 constant와 enum value
├── models.py       # 공개 Pydantic response model
├── types.py        # downstream integration용 공개 type alias
├── exceptions.py   # 공개 exception hierarchy
└── cli.py          # command-line entrypoint
```

## Test policy

- 일반 test는 offline이어야 한다.
- HTTP 동작에는 fake session, fake async session, `httpx.MockTransport`를 사용한다.
- Live test에는 `@pytest.mark.live`와 `DATA_GO_KR_SERVICE_KEY`가 필요하다.
- 불안정한 실제 관광 데이터 값을 assert하지 말고 shape과 type만 assert한다.
- `TourApiHubClient` test는 catalog-driven으로 유지하고 기본 test에서 실제 27개 service를 호출하지 않는다.
- Official manual ZIP/DOCX download는 `.manuals/`에 두고 git에 넣지 않는다.
- Coordinate test는 `PlaceCoordinate` WGS84 `lon`/`lat`와 TourAPI `mapX`/`mapY` 차이를 명시한다.

## Verification command

```bash
python -m compileall src/visitkorea tests
python -m pytest
python -m pytest --cov=visitkorea --cov-fail-under=90
ruff check .
mypy src/visitkorea
```

## Documentation policy

실수를 고쳤다면 `docs/repeated-mistakes.md`에 symptom, cause, rule, guardrail test를 추가한다.
