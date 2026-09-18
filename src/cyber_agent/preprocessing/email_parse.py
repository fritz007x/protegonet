"""RFC-822 (.eml) parsing.

Recovers the real ``<a href>`` targets from an email so the phishing agent scans
where a link actually *goes*, not the anchor text a user would otherwise have to
copy by hand. Also undoes quoted-printable / base64 transfer encoding, which
splits long URLs across lines and hides them from a plain regex sweep.

Stdlib only, and every failure path degrades to ``None`` / ``""`` so the pipeline
stays offline-safe.
"""
from __future__ import annotations

import re
from email import message_from_bytes, message_from_string, policy
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Any, Iterator
from urllib.parse import urlparse


# Headers only a real MIME message carries. Pasted plain text that merely opens
# with "From:"/"Subject:" (the GUI demo samples do) must NOT be treated as MIME,
# or it would change how existing pasted input is parsed.
_MIME_MARKERS = (
    "mime-version:",
    "message-id:",
    "received:",
    "return-path:",
    "delivered-to:",
    "content-type:",
    "dkim-signature:",
)

# Only the header block is searched for those markers, so a PDF stream or body
# text that happens to contain "Content-Type:" can't masquerade as an email.
_HEADER_SCAN_LIMIT = 8192
_HEADER_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9\-]*:")
_BLANK_LINE_RE = re.compile(r"\r?\n\r?\n")
_DOMAIN_RE = re.compile(r"\b((?:[a-z0-9-]+\.)+[a-z]{2,})\b", re.IGNORECASE)

# (display label, header name) — the single source of truth for which headers are
# read and how they are labelled in the rendered blob.
_HEADER_FIELDS = (
    ("SENDER", "from"),
    ("REPLY-TO", "reply-to"),
    ("RECIPIENT", "to"),
    ("SUBJECT", "subject"),
    ("SENT", "date"),
)
# "Invoice_4821.pdf" as anchor text is a domain to _DOMAIN_RE; claiming the link
# impersonates "4821.pdf" would put a fabricated warning in front of the LLM.
_FILE_EXTENSIONS = frozenset(
    "pdf zip rar doc docx xls xlsx ppt pptx csv txt htm html png jpg jpeg gif exe msg eml".split()
)


def looks_like_email(source: Any) -> bool:
    """True when `source` opens with a MIME header block."""
    # Slice before decoding — `source` may be a multi-megabyte PDF.
    text = _decode(source[:_HEADER_SCAN_LIMIT] if isinstance(source, (bytes, str)) else source)
    if not text:
        return False
    head = _BLANK_LINE_RE.split(text, maxsplit=1)[0]
    first = next((ln for ln in head.splitlines() if ln.strip()), "")
    if not _HEADER_LINE_RE.match(first):
        return False
    lowered = head.lower()
    return any(marker in lowered for marker in _MIME_MARKERS)


def parse_email(source: Any) -> dict | None:
    """Parse an RFC-822 message into body text, headers and real link targets.

    Returns None when `source` isn't a MIME message, so callers can fall back to
    treating it as ordinary text.
    """
    if not looks_like_email(source):
        return None
    try:
        msg = (
            message_from_bytes(source, policy=policy.default)
            if isinstance(source, bytes)
            else message_from_string(_decode(source), policy=policy.default)
        )
    except Exception:
        return None

    # Every text/html part is parsed exactly once; body text and link targets
    # both come out of that same pass.
    html_parts = _parse_html_parts(msg)
    body = _display_text(msg, html_parts)
    links = _collect_links(html_parts)
    headers = {key: _header(msg, key) for _, key in _HEADER_FIELDS}
    sender = parseaddr(headers["from"])[1] or headers["from"]

    return {
        "text": _render(headers, links, body),
        "body": body,
        "sender": sender,
        "subject": headers["subject"],
        "links": links,
    }


def _decode(source: Any) -> str:
    if isinstance(source, bytes):
        return source.decode("utf-8", errors="ignore")
    return source if isinstance(source, str) else ""


def _header(msg, name: str) -> str:
    try:
        value = msg[name]
    except Exception:  # malformed header value
        return ""
    return " ".join(str(value).split()) if value else ""


def _walk(msg) -> Iterator[Any]:
    """Every part, descending into message/rfc822 (forwarded-as-attachment)."""
    try:
        yield from msg.walk()
    except Exception:  # malformed tree — stop yielding, don't invent a part
        return


def _content(part) -> str:
    try:
        content = part.get_content()
    except Exception:  # unknown charset, broken encoding
        return ""
    return content if isinstance(content, str) else ""


def _parse_html_parts(msg) -> list[tuple[Any, _HtmlExtractor]]:
    """Parse every text/html part once, in document order.

    `_HtmlExtractor` yields visible text and anchors from a single pass, so both
    `_display_text` and `_collect_links` read from these results rather than
    decoding and re-parsing the same body twice.
    """
    parsed: list[tuple[Any, _HtmlExtractor]] = []
    for part in _walk(msg):
        if part.get_content_maintype() != "text" or part.get_content_subtype() != "html":
            continue
        html = _content(part)
        if html:
            parsed.append((part, _parse_html(html)))
    return parsed


def _parse_html(html: str) -> _HtmlExtractor:
    parser = _HtmlExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # malformed markup
        pass
    return parser


def _display_text(msg, html_parts: list[tuple[Any, _HtmlExtractor]]) -> str:
    """Readable body, preferring the plain-text alternative."""
    already_parsed = {id(part): parser for part, parser in html_parts}

    def text_of(part) -> str:
        parser = already_parsed.get(id(part))
        return parser.text() if parser is not None else _content(part)

    try:
        part = msg.get_body(preferencelist=("plain", "html"))
    except Exception:
        part = None
    if part is not None:
        text = text_of(part).strip()
        if text:
            return text
    # Structures get_body() won't reach — notably a message forwarded as an
    # attachment — still have readable text somewhere in the tree.
    for sub in _walk(msg):
        if sub.get_content_maintype() == "text" and sub.get_content_subtype() in ("plain", "html"):
            text = text_of(sub).strip()
            if text:
                return text
    return ""


def _collect_links(html_parts: list[tuple[Any, _HtmlExtractor]]) -> list[dict]:
    """Real href targets from every text/html part, in document order.

    Anchors only: an <img src> to a CDN is not a link the user can click, and
    padding the list would push the actual payload past the phishing agent's
    per-message URL cap.
    """
    links: list[dict] = []
    seen: set[str] = set()
    for _, parser in html_parts:
        for link in parser.links:
            if link["url"] in seen:
                continue
            seen.add(link["url"])
            links.append(link)
    return links


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:  # malformed authority, e.g. an unterminated IPv6 literal
        return ""


def _display_mismatch(host: str, text: str) -> str | None:
    """The domain the anchor text advertises, when the href goes elsewhere.

    Classic phishing tell: the link reads "paypal.com" but points at an
    attacker-controlled host.
    """
    if not host or not text:
        return None
    for candidate in _DOMAIN_RE.findall(text):
        claimed = candidate.lower().strip(".")
        if claimed.rsplit(".", 1)[-1] in _FILE_EXTENSIONS:
            continue  # a filename, not a domain the anchor claims to reach
        if claimed == host or host.endswith("." + claimed) or claimed.endswith("." + host):
            return None
        return claimed
    return None


class _HtmlExtractor(HTMLParser):
    """Collects visible text and http(s) anchors in a single pass."""

    _SKIP = {"script", "style", "head", "title"}
    _BREAK = {"br", "p", "div", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._anchor: dict | None = None

    def text(self) -> str:
        joined = "".join(self._chunks)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(ln.strip() for ln in joined.splitlines())).strip()

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
            return
        if tag in self._BREAK:
            self._chunks.append("\n")
        if tag == "a":
            href = (dict(attrs).get("href") or "").strip()
            if href.lower().startswith(("http://", "https://")):
                self._flush_anchor()
                self._anchor = {"url": href, "text": ""}

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in self._BREAK:
            self._chunks.append("\n")
        if tag == "a":
            self._flush_anchor()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._chunks.append(data)
        if self._anchor is not None:
            self._anchor["text"] += data

    def close(self) -> None:
        super().close()
        self._flush_anchor()

    def _flush_anchor(self) -> None:
        """Finalise the open anchor into a complete link record.

        `host` and `mismatch` are derived here, while the anchor is closed, so a
        link dict has one shape from the moment it exists and `urlparse` runs
        once per link inside the parser's own failure guard.
        """
        if self._anchor is None:
            return
        link = self._anchor
        self._anchor = None
        link["text"] = " ".join(link["text"].split())
        link["host"] = _hostname(link["url"])
        link["mismatch"] = _display_mismatch(link["host"], link["text"])
        self.links.append(link)


def _render(headers: dict, links: list[dict], body: str) -> str:
    """Flatten the message into the single text blob the agents reason over.

    Links lead the body so they survive the agents' prompt truncation.

    Header labels avoid the RFC field names (SENDER, not From) as cheap
    insurance: `extract_invoice_fields` matches /vendor|from/ and /date/ and
    takes the first hit. `preprocess` already keeps this blob away from it by
    extracting invoice fields from the body alone, so the wording is
    defence-in-depth rather than load-bearing.
    """
    lines: list[str] = []
    for label, key in _HEADER_FIELDS:
        if headers.get(key):
            lines.append(f"{label}: {headers[key]}")

    if links:
        lines.append("")
        lines.append(f"LINK TARGETS ({len(links)} in message body):")
        for i, link in enumerate(links, 1):
            lines.append(f"  [{i}] {link['url']}")
            if link["text"]:
                lines.append(f"      displayed as: {link['text']}")
            if link["mismatch"]:
                lines.append(
                    f"      WARNING: display text claims {link['mismatch']} "
                    f"but the link goes to {link['host'] or '?'}"
                )

    if body:
        lines.append("")
        lines.append("MESSAGE:")
        lines.append(body)
    return "\n".join(lines)
