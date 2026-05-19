# Repeated Mistakes To Avoid

이 문서는 `visitkorea`를 만들면서 반복하기 쉬운 실수를 고정해 두는 로그입니다. 같은 문제가 다시 나오면 반드시 테스트와 함께 갱신합니다.

## 서비스키 인코딩

**실수:** URL-encoded 인증키를 HTTP 클라이언트의 `params=`에 넣어 다시 인코딩한다.

**증상:** 정상 키인데도 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`가 나온다.

**규칙:** 라이브러리 사용 예시는 Decoding 키를 기준으로 한다. 직접 URL 문자열을 만들 때만 Encoding 키를 고려한다.

**가드레일:** HTTP 테스트가 `serviceKey`를 query param으로 그대로 넘기는지 확인한다.

## asyncio 앱에서 별도 비동기 wrapper 만들기

**실수:** TripMate나 `python-krtour-map` 같은 소비자 앱에서 동기 `visitkorea` client를 `asyncio.to_thread()`나 자체 adapter로 감싼다.

**증상:** HTTP 세션 수명, 예외 매핑, pagination, provenance redaction 규칙이 앱마다 갈라지고, 같은 비동기 버그를 여러 저장소에서 고쳐야 한다.

**원인:** 라이브러리 public API에 `httpx.AsyncClient` 기반 client가 없는데도, 부족한 endpoint/helper를 downstream facade로 우회한다.

**규칙:** 동기 client와 같은 메서드 이름을 제공하는 `AsyncKrTourApiClient`와 `AsyncTourApiHubClient`를 직접 사용한다. 응답 모델, 예외 hierarchy, `Page` pagination 규칙은 동기/비동기에서 같아야 하며, 새 async 동작은 이 패키지의 public API로 안정화한다.

**가드레일:** `test_async_typed_client_sends_request_and_parses_page`, `test_async_typed_client_iter_pages`, `test_async_hub_generic_and_related_tour_helpers`.

## 서비스키 복사/붙여넣기 공백을 그대로 보내기

**실수:** 포털 화면이나 메모장에서 복사한 서비스키 앞뒤 공백, 줄바꿈, 탭을 그대로 `serviceKey`에 넣는다.

**증상:** 키 자체는 맞는데도 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` 또는 인증 실패가 난다.

**규칙:** 라이브러리 경계에서 `normalize_service_key()`로 모든 공백 문자를 제거한 뒤 요청한다. 명시 인자, 환경변수, `.env` 파일 값, 직접 전달된 `serviceKey` 파라미터 모두 같은 규칙을 적용한다.

**가드레일:** `test_service_key_whitespace_is_removed_before_request`.

## 데이터소스별 서비스키를 같은 환경변수로만 처리하기

**실수:** `data.go.kr` 호출 키와 `api.visitkorea.or.kr` 쪽 도구 키를 같은 값으로 가정한다.

**증상:** 디버그 UI나 보조 도구에서 다른 데이터소스 키가 필요한데 기존 `KTO_SERVICE_KEY`만 읽어 잘못된 키를 보낸다.

**규칙:** 기본 TourAPI 호출은 `data.go.kr` 키 소스를 쓰고, 도구에서 별도 키가 필요하면 `api.visitkorea` 키 소스를 명시한다. 환경변수가 없으면 로컬 `.env`에서 같은 이름을 읽는다.

**가드레일:** `test_dotenv_service_key_lookup_is_source_specific`, `test_api_catalog_rows_include_dataset_name_and_key_links`.

## JSON 요청이어도 XML 오류가 올 수 있음

**실수:** `_type=json`이면 모든 응답이 JSON이라고 가정한다.

**증상:** 인증키 오류에서 JSON 파싱 실패만 보이고 실제 원인을 잃는다.

**규칙:** JSON 파싱 실패 시 XML error envelope를 먼저 파싱하고 typed exception으로 매핑한다.

**가드레일:** `test_non_json_xml_service_key_error_maps_to_auth`.

## `items.item`은 항상 list가 아님

**실수:** 응답을 무조건 `for row in body["items"]["item"]`로 순회한다.

**증상:** 결과가 1건일 때 dict key를 순회하거나 타입 오류가 난다.

**규칙:** missing/blank/single object/list를 모두 정규화한 뒤 모델로 변환한다.

**가드레일:** 클라이언트 테스트가 단일 dict와 빈 응답을 모두 검증한다.

## 하위 코드만 단독으로 보내기

**실수:** `sigunguCode`, `cat2`, `cat3`, `lDongSignguCd`, `lclsSystm2`, `lclsSystm3`를 상위 코드 없이 보낸다.

**증상:** 공공데이터포털 쪽에서 빈 결과 또는 모호한 요청 오류가 난다.

**규칙:** public client에서 의존성 검증을 먼저 수행한다.

**가드레일:** `test_dependent_filter_validation`.

## `detailCommon2`에 구버전 조회 플래그를 계속 보내기

**실수:** `defaultYN`, `firstImageYN`, `overviewYN` 같은 구버전 플래그를 계속 유지한다.

**증상:** 서비스 버전이 바뀐 뒤 문서와 요청 모양이 어긋난다.

**규칙:** `detail_common()`은 `contentId`, pagination만 보낸다. 추가 필드는 공식 문서 또는 실제 응답으로 확인 후 추가한다.

**가드레일:** detail request shape 테스트를 추가할 때 구버전 플래그가 없는지 확인한다.

## 날짜 형식에 하이픈 넣기

**실수:** `2026-04-30` 같은 ISO 날짜 문자열을 그대로 넘긴다.

**증상:** TourAPI가 날짜 파라미터를 인식하지 못한다.

**규칙:** 요청 날짜는 `YYYYMMDD`만 허용한다. Python `date`/`datetime`은 내부에서 변환한다.

**가드레일:** `test_festival_dates_are_normalized`, `test_date_and_yn_conversions`.

## 불안정한 필드를 dataclass에 성급히 고정하기

**실수:** content type별로 달라지는 intro/detail 필드를 모두 public dataclass 필드로 박아 넣는다.

**증상:** 한 content type에서는 맞지만 다른 content type에서 누락/오해가 생긴다.

**규칙:** 공통 필드만 모델에 올리고, 변동 필드는 `raw`로 보존한다.

**가드레일:** `IntroInfo.raw`, `RepeatInfo.raw`를 유지한다.

## Pydantic 모델에서 `raw`를 버리기

**실수:** `model_dump()` 결과만 보고 TourAPI 원문 필드를 줄여도 된다고 판단한다.

**증상:** 문서에 없거나 content type별로 다른 필드가 사라져 외부 앱에서 후처리할 수 없다.

**규칙:** Pydantic 모델은 안정 필드만 typed field로 올리고, 원문 응답은 항상 `raw`에 보존한다.

**가드레일:** parser 테스트는 typed field와 `raw` 보존을 함께 확인한다.

## 국문 `KorService2`만 구현하고 전체 OpenAPI라고 말하기

**실수:** `api.visitkorea.or.kr/#/useUtilExercises`에는 27개 서비스가 있는데, 자주 쓰는 국문 관광정보서비스만 보고 “전체 구현”으로 착각한다.

**증상:** 고캠핑, 관광사진, 오디, 데이터랩, 반려동물, 의료/웰니스, 지역 수요 계열 서비스를 호출할 방법이 없다.

**규칙:** typed wrapper는 `KorService2`에 집중하되, 전체 OpenAPI 지원은 `SERVICE_DEFINITIONS`와 `TourApiHubClient`가 책임진다. 메뉴얼 목록이 바뀌면 카탈로그 테스트를 먼저 갱신한다.

**가드레일:** `test_catalog_contains_all_manual_services`, `test_hub_call_by_service_key_and_operation_alias`.

## 메뉴얼 ZIP 원본을 저장소에 커밋하기

**실수:** 공식 메뉴얼 ZIP/DOCX를 분석용으로 내려받은 뒤 그대로 git에 올린다.

**증상:** 저장소가 불필요하게 커지고, 외부 원문 파일의 라이선스/갱신 이력을 패키지 릴리스와 섞어 버린다.

**규칙:** 원본은 `.manuals/`에만 내려받고 `.gitignore`로 제외한다. 재현이 필요하면 `scripts/download_visitkorea_manuals.ps1`를 사용한다.

**가드레일:** `.manuals/`는 gitignore에 유지하고, 문서에는 원본 URL과 다운로드 절차만 남긴다.

## 인증키를 테스트 코드나 커밋에 남기기

**실수:** 실 서버 테스트를 빠르게 돌리려고 인증키를 테스트 파일, README 예시, shell script 기본값에 직접 넣는다.

**증상:** 키가 git history에 남고, 원격 저장소나 패키지 배포본에 노출된다.

**규칙:** 인증키는 `.env.local` 또는 현재 shell 환경변수에만 둔다. `.env*`는 gitignore에 유지하고, 커밋 전 `git status --ignored .env.local`로 추적되지 않는지 확인한다.

**가드레일:** `scripts/run_live_tests.ps1`는 `.env.local`을 읽기만 하며, live test는 `KTO_SERVICE_KEY`가 없으면 skip한다.

## 실 서버 응답 코드를 문서 예시 `00`만 정상으로 보기

**실수:** 정상 응답을 `resultCode=00`만 허용한다.

**증상:** 실제 국문 `areaCode2` 응답처럼 `resultCode=0000`이 오면 성공인데도 오류로 처리한다.

**규칙:** `00`, `0000`, `0`, `NORMAL_CODE`는 모두 정상 코드로 본다.

**가드레일:** `test_result_code_0000_is_treated_as_success`, `test_live_korean_area_codes_returns_tourapi_shape`.

## 위도/경도 순서를 섞어서 위치 검색하기

**실수:** TourAPI의 `mapX`, `mapY` 이름만 보고 외부 지도 라이브러리의 `(lat, lon)` 순서와 섞어 보낸다.

**증상:** 위치 기반 검색 결과가 엉뚱한 지역으로 나오거나 반경 검색이 비어 있다.

**규칙:** public API에서는 `kraddr.base.PlaceCoordinate(lat=..., lon=...)`를 직접 사용한다. `Wgs84Coordinate`는 같은 클래스 alias로만 둔다. 튜플 좌표는 `(latitude, longitude)` 또는 `(lat, lon)` 순서로만 해석하고, TourAPI 요청 직전에만 `mapX=lon`, `mapY=lat`로 변환한다.

**가드레일:** `test_place_coordinate_is_public_coordinate_type`, `test_location_accepts_standard_coordinate_inputs`.

## 문서 링크만 추가하고 파일을 만들지 않기

**실수:** README 문서 목록에 새 `.md` 링크를 추가한 뒤 실제 파일을 만들지 않거나 이름을 바꾼다.

**증상:** 사용자가 README에서 바로 따라가야 할 가이드가 404가 되고, 새 public 기능을 어디서 봐야 하는지 흐름이 끊긴다.

**규칙:** README의 로컬 markdown 링크는 실제 파일을 가리켜야 한다. 새 문서를 추가하면 README 문서 목록, 관련 가이드, 테스트 문서의 guardrail도 함께 갱신한다.

**가드레일:** `test_readme_local_markdown_links_exist`.

## 배포 이름과 import 이름을 같은 값으로 가정하기

**실수:** 저장소/배포 이름과 Python import 이름을 모두 같은 문자열로 맞추려고 한다.

**증상:** `python-visitkorea-api`처럼 하이픈이 들어간 배포 이름을 import 경로로 착각하거나, `src` layout에서 루트 패키지를 잘못 발견해 설치 후 `import visitkorea`가 실패한다.

**원인:** PyPI/저장소 이름과 Python 패키지 디렉터리 이름의 역할을 분리하지 않고, 프로젝트 구조 변경 뒤 패키징 설정과 테스트 import 경로를 함께 갱신하지 않는다.

**규칙:** 배포/저장소 이름은 `python-visitkorea-api`로 두고, import 가능한 패키지는 `src/visitkorea` 하나로 둔다. `pyproject.toml`의 setuptools package discovery는 `where = ["src"]`, `include = ["visitkorea*"]`를 유지한다.

**가드레일:** `test_distribution_uses_visitkorea_import_name`, `test_source_layout_is_configured_for_visitkorea_package`.

## Pydantic 모델을 mutable dataclass처럼 문서화하기

**실수:** 응답 모델이 Pydantic frozen model인데 `dataclasses.asdict()`나 직접 필드 대입 예시를 문서에 남긴다.

**증상:** 외부 프로그램 사용자가 예시를 따라 하다가 `ValidationError` 또는 타입 오류를 만난다.

**규칙:** dict 변환은 `model_dump()`, JSON 변환은 `model_dump_json()`, 수정 사본은 `model_copy(update=...)`로 설명한다. 원문 TourAPI 필드는 `raw` 보존 규칙을 함께 적는다.

**가드레일:** `test_user_docs_cover_public_model_usage`.

## 호출 provenance에 인증키를 남기기

**실수:** 외부 앱이 raw/serving 저장을 쉽게 하도록 요청 context를 남기면서 TourAPI `serviceKey`까지 함께 저장한다.

**증상:** 응답 payload, 로그, 캐시, downstream 저장소에 인증키 원문이 노출된다.

**규칙:** `Page.context.request_params`에는 `MobileOS`, `MobileApp`, `_type`과 endpoint별 파라미터만 남긴다. `serviceKey` 또는 `service_key` 계열 키는 사용자가 직접 params에 넣어도 context에서 제거한다.

**가드레일:** `test_search_keyword_sends_filters_and_parses_item`, `test_raw_endpoint_preserves_raw_records`, `test_hub_call_by_service_key_and_operation_alias`.

## TarRlteTarService1 지역 코드를 법정동코드로 설명하기

**실수:** 관광지별 연관 관광지 서비스의 `areaCd`/`signguCd`를 `lDongRegnCd`/`lDongSignguCd` 같은 법정동코드와 같은 것으로 문서화한다.

**증상:** TripMate 같은 소비자가 다른 코드 체계를 섞어 저장하거나, 법정동 필터 UI의 값을 관련 관광지 API에 그대로 넘긴다.

**규칙:** `RelatedTourItem`과 `RelatedTourServiceClient` docstring에는 `areaCd`/`signguCd`가 TarRlteTarService1의 TourAPI 지역 코드이며 법정동코드가 아니라고 명시한다.

**가드레일:** `test_related_tour_area_based_list_returns_typed_single_item`, `test_related_tour_search_keyword_returns_typed_list_items`.

## 페이지 반복을 각 소비자 앱에서 따로 구현하기

**실수:** `totalCount`, `pageNo`, `numOfRows` 계산을 TripMate 같은 소비자 앱마다 다시 작성한다.

**증상:** 마지막 페이지를 누락하거나, `NO_DATA` 응답을 오류로 다루거나, 비정상 pagination metadata에서 긴 반복이 생긴다.

**규칙:** `Page.has_next_page`/`next_page_no`와 client `iter_pages()` 계열 helper를 사용한다. 긴 반복을 막아야 하는 배치 작업에는 `max_pages` 또는 `max_items` guard를 둔다.

**가드레일:** `test_client_iter_pages_increments_page_no`, `test_client_iter_pages_no_data_is_empty_iterator`, `test_hub_iter_pages_increments_page_no_for_generic_call`.

## 검증된 외부 구현을 얇은 wrapper로 감추기

**실수:** 다른 라이브러리나 소비자 앱에서 이미 검증된 구현이 있는데, 최소 수정 원칙에만 매여 `visitkorea`에는 얇은 wrapper나 호출 우회층만 추가한다.

**증상:** 실제 로직은 계속 외부 코드에 남아 같은 버그와 정책을 여러 곳에서 고쳐야 하고, `visitkorea` 사용자는 이 패키지만으로 문제를 해결하지 못한다.

**원인:** 변경량을 줄이는 것을 동작 소유권을 가져오는 것보다 우선해서, 이 패키지가 책임져야 할 구현을 중간 계층 뒤에 남겨 둔다.

**규칙:** 공통 POI/좌표 값 객체처럼 `kraddr.base`가 소유한 개념은 `visitkorea`에 mirror class나 변환 wrapper를 만들지 말고 `kraddr.base` 타입을 파라미터와 반환값에 직접 사용한다. 필요한 alias나 provider key 지원은 `python-kraddr-base`에 보강하고, TourAPI 요청명으로 바꾸는 마지막 단계만 `visitkorea`에 둔다.

**가드레일:** 공통 구현을 가져올 때는 원 구현이 해결하던 edge case를 offline test fixture로 먼저 옮긴다. 출처나 근거가 필요한 경우 문서 또는 짧은 코드 주석에 남기고, 별도 wrapper만 추가된 변경은 실제 public 타입이 `kraddr.base` 타입인지 리뷰한다.

## 예외 메시지만 보고 사용자 오류를 분기하기

**실수:** 외부 앱이 `str(exc)`를 파싱하거나 자체 exception mapping wrapper를 만들어 인증, 쿼터, 요청 오류, 서버 오류, 파싱 오류를 다시 분류한다.

**증상:** 관리자 로그와 사용자 메시지가 섞이고, TourAPI `resultCode`/HTTP status/endpoint 정보가 사라지거나 인증키 원문이 로그에 남을 위험이 생긴다.

**규칙:** 기존 `TourApiAuthError` 같은 subclass catch는 유지하되, 모든 `TourApiError`에는 `result_code`, `status_code`, `endpoint`, `service_name`, `failure_kind` metadata를 채운다. 사용자 메시지는 `failure_kind`로 분기하고, 관리자 로그에는 `exc.metadata`만 남긴다. 예외 문자열, `repr`, metadata에는 `serviceKey` 원문을 남기지 않는다.

**가드레일:** `test_more_http_error_branches`, `test_non_json_xml_service_key_error_maps_to_auth`, `test_json_openapi_service_response_errors`, `test_json_result_code_request_error_metadata`, `test_detail_no_data_error_metadata`.

## KTO 표시 정책 문자열을 앱마다 하드코딩하기

**실수:** `cpyrhtDivCd` 표시 문구와 `homepage`/`overview`/`infotext` HTML 정리를 TripMate 같은 소비자 앱마다 별도 매핑과 정규식으로 구현한다.

**증상:** KTO 저작권 코드 원문을 잃거나, 알 수 없는 코드가 빈 문구로 표시되거나, TourAPI HTML 조각이 앱별로 다르게 정리된다.

**규칙:** parsing 결과와 `raw`는 그대로 보존하고, 표시가 필요한 시점에만 `copyright_display_info()`와 `clean_tourapi_html()` helper를 명시적으로 호출한다. `clean_tourapi_html()`은 보안 sanitizer가 아니므로 HTML 렌더링 전 앱 sanitizer는 계속 별도로 둔다.

**가드레일:** `test_copyright_display_info_preserves_known_and_unknown_codes`, `test_clean_tourapi_html_returns_plain_display_text`, `test_display_helpers_are_opt_in_and_keep_raw_fields`.

## Windows PowerShell에서 파일 검색과 UTF-8 문서 읽기를 기본값에 맡기기

**실수:** 이 환경에서 `rg` 실행 권한이 막혀 있는데도 반복해서 `rg`를 시도하거나, UTF-8 문서를 PowerShell 기본 출력 인코딩으로 읽는다.

**증상:** 파일 목록/검색 단계에서 불필요하게 막히고, 한국어 문서가 깨져 보여 실제 내용과 다른 문제처럼 오해한다.

**원인:** Windows PowerShell의 실행 정책/권한과 기본 콘솔 인코딩을 확인하지 않고, 평소 쓰는 검색/출력 명령을 그대로 적용한다.

**규칙:** `rg`가 권한 문제로 막힌 환경에서는 PowerShell 파일 목록과 검색으로 우회한다. 문서 파일은 항상 `Get-Content -Encoding UTF8` 또는 UTF-8을 명시하는 동등한 명령으로 읽는다.

**가드레일:** 문서/파일 조사 단계에서 `rg` 실패가 보이면 즉시 `Get-ChildItem -Recurse`와 `Select-String` 계열로 전환하고, 한국어 문서는 `Get-Content -Raw -Encoding UTF8`로 재확인한다.

## 문서에 로컬 절대 경로를 남기기

**실수:** README, 개발 문서, 변경 요약에 `F:\dev\visitkorea\...` 같은 개인 환경의 절대 경로를 남긴다.

**증상:** 다른 개발자나 CI 환경에서 그대로 따라갈 수 없는 위치 정보가 생기고, 문서가 특정 작업 PC에 묶여 보인다.

**규칙:** 저장소 안의 파일 위치는 프로젝트 루트 기준 상대 경로로 쓴다. 예: `docs/repeated-mistakes.md`, `src/visitkorea/client.py`.

**가드레일:** 문서와 커밋/PR 설명을 마무리하기 전에 로컬 드라이브 경로, 사용자 홈 경로, OS별 임시 절대 경로가 남아 있지 않은지 확인한다.

## Python 내부 문서를 영어 기본값으로 쓰기

**실수:** public docstring, 내부 helper 설명, 주석을 습관적으로 영어로 작성해 한국어 중심 문서와 톤이 어긋나게 만든다.

**증상:** README와 사용자 문서는 한국어인데 코드 안의 설명은 영어라 유지보수자가 같은 개념을 두 언어로 오가며 읽어야 한다.

**규칙:** 이 저장소의 Python 내부 문서(docstring, 필요한 코드 주석, 예외 설명용 내부 문자열)는 특별한 외부 API 호환 이유가 없으면 한국어로 작성한다. 코드 식별자와 TourAPI 원문 필드명은 그대로 둔다.

**가드레일:** Python 파일을 수정할 때 새로 추가한 docstring/주석이 한국어인지 확인하고, 영어가 필요한 경우에는 공식 명칭, 프로토콜 값, 외부 라이브러리 용어처럼 이유가 있는지 점검한다.
