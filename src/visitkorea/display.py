"""Display helpers for TourAPI policy and HTML-like text fields."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Final


@dataclass(frozen=True)
class CopyrightDisplayInfo:
    """Display metadata for a TourAPI `cpyrhtDivCd` value."""

    raw_code: str | None
    code: str | None
    label: str
    notice: str
    known: bool


_COPYRIGHT_POLICY: Final[dict[str, tuple[str, str]]] = {
    "Type1": (
        "Public Nuri Type 1: Attribution",
        "Show the source or credit when displaying or reusing this content.",
    ),
    "Type2": (
        "Public Nuri Type 2: Attribution, non-commercial",
        "Show the source or credit. Commercial reuse is not allowed.",
    ),
    "Type3": (
        "Public Nuri Type 3: Attribution, no derivatives",
        "Show the source or credit. Do not modify or create derivative works.",
    ),
    "Type4": (
        "Public Nuri Type 4: Attribution, non-commercial, no derivatives",
        "Show the source or credit. Commercial reuse and modifications are not allowed.",
    ),
}

_BLOCK_TAGS: Final[set[str]] = {
    "address",
    "article",
    "aside",
    "blockquote",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
_SKIP_TAGS: Final[set[str]] = {"script", "style"}
_SPACES_RE: Final[re.Pattern[str]] = re.compile(r"[ \t\f\v]+")
_NEWLINE_SPACES_RE: Final[re.Pattern[str]] = re.compile(r" *\n *")
_MANY_NEWLINES_RE: Final[re.Pattern[str]] = re.compile(r"\n{3,}")


def copyright_display_info(cpyrht_div_cd: str | None) -> CopyrightDisplayInfo:
    """Return a display label and notice for a TourAPI `cpyrhtDivCd` value.

    Unknown or blank codes are preserved in the returned object so callers can log,
    store, or review the exact KTO value without falling back to app-specific string
    mappings.
    """

    raw_code = cpyrht_div_cd
    code = _normalize_copyright_code(cpyrht_div_cd)
    if code is None:
        return CopyrightDisplayInfo(
            raw_code=raw_code,
            code=None,
            label="Copyright division unspecified",
            notice="Check the original TourAPI record before displaying or reusing content.",
            known=False,
        )
    policy = _COPYRIGHT_POLICY.get(code)
    if policy is None:
        return CopyrightDisplayInfo(
            raw_code=raw_code,
            code=code,
            label=f"Unknown copyright division: {code}",
            notice="Check the KTO/TourAPI policy for this copyright division before display.",
            known=False,
        )
    label, notice = policy
    return CopyrightDisplayInfo(
        raw_code=raw_code,
        code=code,
        label=label,
        notice=notice,
        known=True,
    )


def clean_tourapi_html(value: str | None) -> str | None:
    """Return plain display text from a TourAPI HTML fragment.

    This helper is intentionally opt-in and does not mutate parsed models or their
    `raw` records. It is not a security sanitizer; apps that render HTML should still
    run their own sanitizer after any app-specific formatting step. The returned text
    is NOT HTML-safe: HTML character references (e.g. `&lt;`) are decoded to their
    literal characters (e.g. `<`), so this output must be HTML-escaped by the caller
    before being interpolated into any HTML/markup context.
    """

    if value is None:
        return None
    if not value.strip():
        return None
    parser = _TourApiTextParser()
    parser.feed(value)
    parser.close()
    text = _normalize_display_text("".join(parser.parts))
    return text or None


def _normalize_copyright_code(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    compact = stripped.replace("_", "").replace("-", "").replace(" ", "").lower()
    if compact.startswith("type") and compact[4:].isdigit():
        return f"Type{int(compact[4:])}"
    return stripped


def _normalize_display_text(value: str) -> str:
    text = value.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = _SPACES_RE.sub(" ", text)
    text = _NEWLINE_SPACES_RE.sub("\n", text)
    text = _MANY_NEWLINES_RE.sub("\n\n", text)
    return text.strip()


class _TourApiTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._links: list[tuple[str, int]] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "br":
            self._append_newline()
            return
        if tag in _BLOCK_TAGS:
            self._append_newline()
        if tag == "a":
            href = _attr_value(attrs, "href")
            self._links.append((href, len(self.parts)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "br" and not self._skip_depth:
            self._append_newline()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a" and self._links:
            href, start_index = self._links.pop()
            link_text = _normalize_display_text("".join(self.parts[start_index:]))
            if href and href not in link_text:
                self.parts.append(f" ({href})")
        if tag in _BLOCK_TAGS:
            self._append_newline()

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def _append_newline(self) -> None:
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")


def _attr_value(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key.lower() == name and value:
            return value.strip()
    return ""
