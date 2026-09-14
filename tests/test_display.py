from __future__ import annotations

from visitkorea import clean_tourapi_html, copyright_display_info

from .conftest import FakeResponse, tour_payload


def test_copyright_display_info_preserves_known_and_unknown_codes() -> None:
    known = copyright_display_info(" type-03 ")

    assert known.raw_code == " type-03 "
    assert known.code == "Type3"
    assert known.known is True
    assert "Type 3" in known.label
    assert "Do not modify" in known.notice

    unknown = copyright_display_info("KTO-CUSTOM")

    assert unknown.raw_code == "KTO-CUSTOM"
    assert unknown.code == "KTO-CUSTOM"
    assert unknown.known is False
    assert "KTO-CUSTOM" in unknown.label

    blank = copyright_display_info(" ")

    assert blank.raw_code == " "
    assert blank.code is None
    assert blank.known is False


def test_clean_tourapi_html_returns_plain_display_text() -> None:
    value = (
        "<div>First&nbsp;line<br>Second line</div>"
        "<script>alert('x')</script>"
        "<a href='https://example.com'>Official</a>"
    )

    assert clean_tourapi_html(value) == (
        "First line\nSecond line\nOfficial (https://example.com)"
    )
    assert clean_tourapi_html(" Already&nbsp;text ") == "Already text"
    assert clean_tourapi_html("") is None
    assert clean_tourapi_html(None) is None


async def test_display_helpers_are_opt_in_and_keep_raw_fields(fake_client_factory) -> None:
    detail_row = {
        "contentid": "1",
        "contenttypeid": "12",
        "title": "Sample",
        "homepage": "<a href='https://example.com'>Official</a>",
        "overview": "<p>Hello&nbsp;world</p><p>Next<br>line</p>",
        "cpyrhtDivCd": "Type1",
    }
    repeat_row = {
        "contentid": "1",
        "contenttypeid": "25",
        "serialnum": "0",
        "infoname": "Course",
        "infotext": "<div>Stop&nbsp;1<br>Stop 2</div>",
    }
    client, _session = fake_client_factory(
        FakeResponse(tour_payload(detail_row)),
        FakeResponse(tour_payload(repeat_row)),
    )

    detail = (await client.detail_common("1"))
    repeat = (await client.detail_info("1", "25")).items[0]

    assert detail.homepage == detail_row["homepage"]
    assert detail.overview == detail_row["overview"]
    assert detail.raw["overview"] == detail_row["overview"]
    assert repeat.info_text == repeat_row["infotext"]
    assert repeat.raw["infotext"] == repeat_row["infotext"]

    assert clean_tourapi_html(detail.homepage) == "Official (https://example.com)"
    assert clean_tourapi_html(detail.overview) == "Hello world\nNext\nline"
    assert clean_tourapi_html(repeat.info_text) == "Stop 1\nStop 2"
    assert copyright_display_info(detail.copyright_division_code).code == "Type1"
