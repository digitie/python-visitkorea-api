# TourAPI OpenAPI Catalog

확인 기준일: 2026-04-30

이 카탈로그는 [한국관광콘텐츠랩 OpenAPI 목록](https://api.visitkorea.or.kr/#/useUtilExercises)에서 내려받은 메뉴얼 ZIP 27개를 기준으로 정리했습니다. 원본 목록은 SPA 내부 API `https://api.visitkorea.or.kr/use/useUtilExercises.do`에서 확인했고, 메뉴얼은 `/upload/manual/guide/file/...zip` 경로로 내려받았습니다.

원본 ZIP은 저장소에 커밋하지 않고 `.manuals/`에 내려받아 분석했습니다. 다시 받으려면:

```powershell
.\scripts\download_visitkorea_manuals.ps1
```

## Generic Client

모든 서비스는 `TourApiHubClient`에서 호출할 수 있습니다.

```python
from visitkorea import TourApiHubClient

hub = TourApiHubClient.from_env()  # 또는 TourApiHubClient("service-key")

page = hub.call("gocamping", "basedList", facltNm="숲")
page = hub.photo_gallery.gallery_list(galSearchKeyword="서울")
page = hub.pet.detail_pet_tour2(content_id="123")
page = hub.related_tour.area_based_list(base_ym="202504", area_cd="51", signgu_cd="51130")
```

`page_no`, `num_of_rows`, `content_id`, `content_type_id`는 Python식 이름으로 전달하면 각각 `pageNo`, `numOfRows`, `contentId`, `contentTypeId`로 바뀝니다. 그 외 파라미터는 메뉴얼의 원문 이름을 그대로 전달합니다.

Hub 응답의 `page.context`에는 `service_name`, `endpoint`, `request_params`, `collected_at`이 채워집니다. `request_params`는 raw/serving 저장에 바로 쓸 수 있도록 `serviceKey`를 제외한 공개 요청 파라미터만 담습니다.

여러 페이지가 필요하면 `hub.iter_pages(service, operation, ...)`를 사용합니다. `Page.total_count`, `page_no`, `num_of_rows`를 기준으로 다음 페이지를 판단하고, `max_pages` 또는 `max_items` guard를 지정할 수 있습니다.

## Services

| key | service name | operations | manual |
|---|---|---|---|
| `kor` | `KorService2` | `areaCode2`, `categoryCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `detailPetTour2`, `ldongCode2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596499508.zip) |
| `eng` | `EngService2` | `areaCode2`, `categoryCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `ldongCode2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596531873.zip) |
| `chs` | `ChsService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160495049.zip) |
| `cht` | `ChtService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596423271.zip) |
| `jpn` | `JpnService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596480579.zip) |
| `ger` | `GerService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596457504.zip) |
| `fre` | `FreService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596408255.zip) |
| `spn` | `SpnService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596391866.zip) |
| `rus` | `RusService2` | `areaCode2`, `categoryCode2`, `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `searchFestival2`, `searchStay2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `areaBasedSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596057411.zip) |
| `with` | `KorWithService2` | `areaCode2`, `categoryCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `detailWithTour2`, `areaBasedSyncList2`, `ldongCode2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596514908.zip) |
| `green` | `GreenTourService1` | `areaCode1`, `areaBasedList1`, `areaBasedSyncList1` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160406003.zip) |
| `photo_gallery` | `PhotoGalleryService1` | `galleryList1`, `gallerySearchList1`, `galleryDetailList1`, `gallerySyncDetailList1` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160396374.zip) |
| `gocamping` | `GoCamping` | `basedList`, `locationBasedList`, `searchList`, `imageList`, `basedSyncList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160387374.zip) |
| `odii` | `Odii` | `themeBasedList`, `themeLocationBasedList`, `themeSearchList`, `storyBasedList`, `storyLocationBasedList`, `storySearchList`, `themeBasedSyncList`, `storyBasedSyncList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1720672146251.zip) |
| `datalab` | `DataLabService` | `metcoRegnVisitrDDList`, `locgoRegnVisitrDDList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160370032.zip) |
| `durunubi` | `Durunubi` | `routeList`, `courseList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160359411.zip) |
| `employment` | `tursmService` | `empmnInfoList`, `empmnInfoDetail`, `code`, `syncList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1704160822554.zip) |
| `tats_concentration` | `TatsCnctrRateService` | `tatsCnctrRateList`, `tatsCnctrRatedList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1725501618773.zip) |
| `local_hub` | `LocgoHubTarService1` | `areaBasedList1` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1725501897980.zip) |
| `related_tour` | `TarRlteTarService1` | `areaBasedList1`, `searchKeyword1` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1725502022236.zip) |
| `pet` | `KorPetTourService2` | `ldongCode2`, `areaBasedList2`, `locationBasedList2`, `searchKeyword2`, `detailCommon2`, `detailIntro2`, `detailInfo2`, `detailImage2`, `detailPetTour2`, `petTourSyncList2`, `lclsSystmCode2` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1737596366080.zip) |
| `medical` | `MdclTursmService` | `ldongCode`, `areaBasedList`, `locationBasedList`, `searchKeyword`, `mdclTursmSyncList`, `detailCommon`, `detailIntro`, `detailMdclTursm` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1725080563660.zip) |
| `wellness` | `WellnessTursmService` | `ldongCode`, `areaBasedList`, `locationBasedList`, `searchKeyword`, `wellnessTursmSyncList`, `detailCommon`, `detailIntro`, `detailInfo`, `detailImage` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1725080513010.zip) |
| `photo_award` | `PhokoAwrdService` | `ldongCode`, `phokoAwrdList`, `phokoAwrdSyncList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/1725092509540.zip) |
| `area_diversity` | `AreaTarDivService` | `areaTouDivList`, `areaExpDivList`, `areaIntlDivList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/manual_areaTarDivService.zip) |
| `area_demand_strength` | `AreaTarDemDsService` | `areaTarSjrnDsList`, `areaTarExpDsList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/manual_areaTarDemDsService.zip) |
| `area_resource_demand` | `AreaTarResDemService` | `areaTarSvcDemList`, `areaCulResDemList` | [download](https://api.visitkorea.or.kr/upload/manual/guide/file/manual_areaTarResDemService.zip) |

## Notes

- `KorService2`처럼 typed high-level 메서드가 있는 서비스도 `TourApiHubClient`에서는 raw record로 반환합니다.
- 메뉴얼마다 구버전 서비스명과 최신 서비스명이 함께 섞여 있는 경우가 있어, 표에는 최신/가장 많이 등장한 서비스명을 기준으로 정리했습니다.
- 일부 메뉴얼의 예제 URL에는 오탈자가 있습니다. 예: Odii 메뉴얼에는 `themeBaseSyncdList`가 보이나 operation 표와 실제 패턴 기준으로 `themeBasedSyncList`를 사용합니다.
- Hub 클라이언트의 반환값은 Pydantic `Page[Mapping[str, Any]]`입니다. 서비스별 item 필드가 매우 다르므로 generic path에서는 typed item 모델을 만들지 않고 원문 record를 보존합니다.
- Hub `Page.context.request_params`에는 인증키 원문을 남기지 않습니다.
- `page_no`, `num_of_rows`, `content_id`, `content_type_id`, `coordinate` 같은 Python식 alias는 Hub에서도 지원합니다. 특히 `coordinate`는 `PlaceCoordinate`, `(latitude, longitude)` tuple, `{"longitude": ..., "latitude": ...}` 또는 `{"mapX": ..., "mapY": ...}` mapping을 `mapX`/`mapY`로 변환합니다.
- `related_tour`는 예외적으로 typed helper를 제공합니다. `area_based_list()`와 `search_keyword()`는 `Page[RelatedTourItem]`을 반환하고, generic `call()`은 기존처럼 raw mapping을 반환합니다. `area_cd`/`signgu_cd`는 TarRlteTarService1의 TourAPI 지역 코드이지 법정동코드가 아닙니다.
- `related_tour.iter_area_based_list()`와 `related_tour.iter_search_keyword()`는 typed `Page[RelatedTourItem]`을 페이지 단위로 반복합니다.
- 국문 `KorService2`의 자주 쓰는 endpoint는 `KrTourApiClient`에 typed method가 있습니다. 전체 서비스 범위가 필요하면 Hub, 더 강한 모델과 enum이 필요하면 typed client를 선택합니다.

## Catalog Maintenance

공식 활용신청 목록이나 메뉴얼 ZIP이 바뀌면 아래 순서로 갱신합니다.

1. `.manuals/`에 새 메뉴얼을 내려받는다.
2. `src/visitkorea/services.py`의 `SERVICE_DEFINITIONS`를 갱신한다.
3. `docs/openapi-catalog.md`의 service 표와 확인 기준일을 맞춘다.
4. `tests/test_hub.py`의 카탈로그 개수, service key, operation routing 테스트를 갱신한다.
5. 원본 ZIP/DOCX는 git에 올리지 않는다.

다운로드 스크립트:

```powershell
.\scripts\download_visitkorea_manuals.ps1
```
