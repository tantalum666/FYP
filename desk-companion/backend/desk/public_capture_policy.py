"""Pure, bounded static capture policy. Syntax/public claims never prove public access.

No network, rendering, storage, credentials or model dispatch occurs here. HTML is
strictly balanced (no browser-style optional closing tags); void tags never push
stack entries. Every block boundary becomes LF, horizontal HTML whitespace is
collapsed, and all extracted lines end with LF. CSS is deliberately not evaluated.
"""

from dataclasses import dataclass
from hashlib import sha256
from html import unescape
from html.entities import html5
from html.parser import HTMLParser
import json
import re
import unicodedata
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .store import DomainError

RAW_BYTES = 128 * 1024
EXTRACTED_BYTES = 24 * 1024
LINE_BYTES = 1024
MAX_DEPTH = 64
MAX_EVENTS = 20000
PARSER_CHUNK = 1024
EXTRACTOR_VERSION = "static_text_v1"
POLICY_VERSION = 1
Checkpoint = Callable[[], None]
Mime = Literal["text/plain", "text/markdown", "text/html"]
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_RESERVED = {
    "localhost",
    "local",
    "internal",
    "intranet",
    "lan",
    "home",
    "test",
    "invalid",
    "example",
    "onion",
    "arpa",
}
_CREDENTIAL = re.compile(
    r"(?:^|[/_.-])(?:token|access[-_]token|api[-_]key|apikey|password|secret|reset[-_]password|password[-_]reset|magic[-_]link|signin|sign-in|login|oauth|authorize|session)(?:$|[/_.-])",
    re.I,
)


def _fail(code, status=422):
    raise DomainError(code, status)


@dataclass(frozen=True, slots=True)
class ValidatedURL:
    url: str
    host: str
    path: str


def validate_url(url: str) -> ValidatedURL:
    """Admit exact ASCII syntax only, without normalization or DNS lookup."""
    if type(url) is not str or len(url) > 1024 or not url.isascii():
        _fail("CAPTURE_URL_INVALID")
    match = re.fullmatch(r"https://([^/]+)(/[A-Za-z0-9/_~.\-]*)", url)
    if not match:
        _fail("CAPTURE_URL_INVALID")
    host, path = match.groups()
    labels = host.split(".")
    if (
        len(host) > 253
        or len(labels) < 2
        or any(not re.fullmatch(_LABEL, label) for label in labels)
        or any(label.startswith("xn--") for label in labels)
        or labels[-1] in _RESERVED
        or not re.fullmatch(r"[a-z]{2,63}", labels[-1])
        or any(label in {"localhost", "local", "internal", "intranet"} for label in labels)
        or "//" in path
        or any(s in {".", ".."} for s in path.split("/"))
    ):
        _fail("CAPTURE_URL_INVALID")
    if _CREDENTIAL.search(path):
        _fail("CAPTURE_CREDENTIAL_URL_DENIED")
    return ValidatedURL(url, host, path)


def validate_mime(value: str) -> Mime:
    if type(value) is not str or len(value) > 128:
        _fail("CAPTURE_CONTENT_TYPE_DENIED")
    match = re.fullmatch(
        r'(text/(?:plain|markdown|html))(?:;[ \t]*charset=(?:utf-8|"utf-8"))?', value, re.I
    )
    if not match:
        _fail("CAPTURE_CONTENT_TYPE_DENIED")
    return match[1].lower()


def _plain_label(value):
    if value is not None and (
        not value.strip()
        or any(unicodedata.category(c).startswith("C") or c in "\u2028\u2029" for c in value)
    ):
        raise ValueError("A plain single-line label is required")
    return value


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def exact_literals(cls, value):
        # Pydantic Literal[True]/Literal[1] otherwise admit equal int/bool values.
        if isinstance(value, dict):
            for name in ("retain_capture_record", "public_only", "retain_snapshot", "raw_retained"):
                if name in value and type(value[name]) is not bool:
                    raise ValueError("Strict boolean required")
            for name in ("policy_version", "intent_version", "disclosure_version"):
                if name in value and type(value[name]) is not int:
                    raise ValueError("Strict integer required")
        return value


class CapturePrepare(FrozenModel):
    url: str = Field(max_length=1024)
    label: str | None = Field(default=None, min_length=1, max_length=120)
    retain_capture_record: Literal[True]

    @field_validator("url")
    @classmethod
    def accepted_url(cls, value):
        try:
            validate_url(value)
        except DomainError:
            raise ValueError("Capture URL is not admitted") from None
        return value

    _label = field_validator("label")(_plain_label)


class CaptureApprove(FrozenModel):
    expected_version: int = Field(ge=1, le=2147483647)
    intent_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    public_only: Literal[True]
    retain_snapshot: Literal[True]


class CaptureVersionInput(FrozenModel):
    expected_version: int = Field(ge=1, le=2147483647)


class CaptureIntent(CapturePrepare):
    capture_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    session_hash: str = Field(min_length=1, max_length=128)
    privacy_revision: str = Field(min_length=1, max_length=128)
    display_name: str = Field(pattern=r"^capture-[a-f0-9]{32}\.txt$")
    intent_version: Literal[1] = 1
    policy_version: Literal[1] = 1
    disclosure_version: Literal[1] = 1
    extractor_version: Literal["static_text_v1"] = EXTRACTOR_VERSION
    method: Literal["GET"] = "GET"
    credentials: Literal["none"] = "none"
    redirects: Literal["deny"] = "deny"
    public_only: Literal[True] = True
    retention: Literal["local_indefinite_no_delete_control"] = "local_indefinite_no_delete_control"
    raw_retention: Literal["none"] = "none"

    @model_validator(mode="after")
    def matching_name(self):
        if self.display_name != f"capture-{self.capture_id}.txt":
            raise ValueError("Generated filename must match capture identity")
        return self

    def digest(self) -> str:
        return sha256(
            json.dumps(
                self.model_dump(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()


class CaptureAcquisition(FrozenModel):
    response_mime: Mime
    response_charset: Literal["utf-8"] = "utf-8"
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_byte_count: int = Field(ge=1, le=RAW_BYTES)
    extracted_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extracted_byte_count: int = Field(ge=1, le=EXTRACTED_BYTES)
    extractor_version: Literal["static_text_v1"] = EXTRACTOR_VERSION
    coverage: Literal["complete_accepted_static_extraction"] = "complete_accepted_static_extraction"
    raw_retained: Literal[False] = False
    rendered_coverage: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class StaticExtraction:
    body: bytes
    acquisition: CaptureAcquisition


def _normalize(text):
    for char in text:
        if unicodedata.category(char) == "Cc" and char not in "\t\n\r\x85":
            _fail("CAPTURE_TEXT_CONTROL_DENIED")
        if unicodedata.category(char) == "Cs":
            _fail("CAPTURE_TEXT_CONTROL_DENIED")
    return (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\x85", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
    )


_VOID = set("area base br col embed hr img input link meta param source track wbr".split())
_HIDDEN = {"head", "script", "style", "template", "noscript"}
_BLOCK = set(
    "address article aside blockquote br dd div dl dt fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table tbody td th thead tr ul".split()
)
_ATTR = re.compile(r"""\s+[^\s/<>="'`]+(?:\s*=\s*(?:"[^"<>]*"|'[^'<>]*'|[^\s<>="'`]+))?""")


class _StaticHTML(HTMLParser):
    def __init__(self, checkpoint):
        super().__init__(convert_charrefs=False)
        self.checkpoint = checkpoint
        self.stack = []
        self.parts = []
        self.size = 0
        self.events = 0

    def feed(self, data):
        # Some Python versions defer incomplete-token chunks in a private
        # pending queue until close(), whose EOF repair discards malformed
        # tails. Parse each bounded feed without EOF repair so the retained
        # lexical tail is observable. Total input remains capped at 128KiB.
        self.rawdata += data
        self.goahead(0)

    def event(self):
        self.events += 1
        if self.events > MAX_EVENTS:
            _fail("CAPTURE_PARSER_LIMIT")
        if self.events % 32 == 0:
            self.checkpoint()

    def emit(self, value):
        if self.stack and self.stack[-1][1]:
            return
        self.size += len(value.encode("utf-8"))
        if self.size > RAW_BYTES:
            _fail("CAPTURE_OUTPUT_LIMIT", 413)
        self.parts.append(value)

    def handle_starttag(self, tag, attrs):
        self.event()
        raw = self.get_starttag_text()
        # HTMLParser is permissive; admit only a complete unambiguous token.
        inner = raw[1:-1].rstrip()
        if inner.endswith("/"):
            if not raw.endswith("/>") or tag not in _VOID:
                _fail("CAPTURE_HTML_MALFORMED")
            inner = inner[:-1].rstrip()
        name = re.match(r"[A-Za-z][A-Za-z0-9:-]*", inner)
        if not name:
            _fail("CAPTURE_HTML_MALFORMED")
        pos = name.end()
        while pos < len(inner):
            attr = _ATTR.match(inner, pos)
            if not attr:
                _fail("CAPTURE_HTML_MALFORMED")
            pos = attr.end()
        names = [key for key, _ in attrs]
        if len(set(names)) != len(names):
            _fail("CAPTURE_HTML_MALFORMED")
        hidden = (
            bool(self.stack and self.stack[-1][1])
            or tag in _HIDDEN
            or any(
                key == "hidden"
                or (key == "aria-hidden" and (value or "").strip().lower() == "true")
                for key, value in attrs
            )
        )
        if tag in _BLOCK and not hidden:
            self.emit("\n")
        if tag not in _VOID:
            if len(self.stack) >= MAX_DEPTH:
                _fail("CAPTURE_PARSER_LIMIT")
            self.stack.append((tag, hidden))

    def handle_startendtag(self, tag, attrs):
        # XML-style self closing is supported only for HTML void elements.
        if tag not in _VOID:
            _fail("CAPTURE_HTML_MALFORMED")
        self.handle_starttag(tag, attrs)

    def parse_endtag(self, i):
        end = self.rawdata.find(">", i)
        if end >= 0 and not re.fullmatch(
            r"</[A-Za-z][A-Za-z0-9:-]*\s*>", self.rawdata[i : end + 1]
        ):
            _fail("CAPTURE_HTML_MALFORMED")
        return super().parse_endtag(i)

    def handle_endtag(self, tag):
        self.event()
        if tag in _VOID or not self.stack or self.stack[-1][0] != tag:
            _fail("CAPTURE_HTML_MALFORMED")
        _, hidden = self.stack.pop()
        if tag in _BLOCK and not hidden:
            self.emit("\n")

    def handle_data(self, data):
        self.event()
        if "<" in data and not (self.stack and self.stack[-1][0] in {"script", "style"}):
            _fail("CAPTURE_HTML_MALFORMED")
        self.emit(_normalize(data))

    def handle_entityref(self, name):
        self.event()
        if name + ";" not in html5:
            _fail("CAPTURE_HTML_MALFORMED")
        self.emit(_normalize(unescape("&" + name + ";")))

    def handle_charref(self, name):
        self.event()
        try:
            code = int(name[1:], 16) if name.lower().startswith("x") else int(name)
            value = chr(code)
        except (ValueError, OverflowError):
            _fail("CAPTURE_HTML_MALFORMED")
        self.emit(_normalize(value))

    def parse_comment(self, i, report=True):
        # Newer HTMLParser calls this directly, bypassing declaration parsing.
        tail = self.rawdata[i:]
        if tail[4:].startswith((">", "->")):
            _fail("CAPTURE_HTML_MALFORMED")
        end = tail.find("-->", 4)
        if end < 0:
            if "--!>" in tail:
                _fail("CAPTURE_HTML_MALFORMED")
            return -1
        data = tail[4:end]
        if "--" in data:
            _fail("CAPTURE_HTML_MALFORMED")
        if report:
            self.handle_comment(data)
        return i + end + 3

    def parse_html_declaration(self, i):
        tail = self.rawdata[i:]
        if tail.startswith("<!--"):
            return self.parse_comment(i)
        if not "<!doctype".startswith(tail.lower()) and not tail.lower().startswith("<!doctype"):
            _fail("CAPTURE_HTML_MALFORMED")
        return super().parse_html_declaration(i)

    def handle_comment(self, data):
        self.event()
        if "--" in data:
            _fail("CAPTURE_HTML_MALFORMED")

    def handle_decl(self, decl):
        self.event()
        if decl.lower() != "doctype html":
            _fail("CAPTURE_HTML_MALFORMED")

    def unknown_decl(self, data):
        _fail("CAPTURE_HTML_MALFORMED")

    def handle_pi(self, data):
        _fail("CAPTURE_HTML_MALFORMED")


def _wrap(text, checkpoint):
    output = []
    size = 0
    for line in text.split("\n"):
        checkpoint()
        # Each output line includes its LF in the byte budget.
        while len(line.encode()) > LINE_BYTES - 1:
            used, end, space = 0, 0, 0
            for end, char in enumerate(line):
                used += len(char.encode())
                if used > LINE_BYTES - 1:
                    break
                if char.isspace():
                    space = end + 1
            end = space or end
            part, line = line[:end], line[end:]
            output.append(part + "\n")
            size += len(part.encode()) + 1
            if size > EXTRACTED_BYTES:
                _fail("CAPTURE_OUTPUT_LIMIT", 413)
            checkpoint()
        output.append(line + "\n")
        size += len(line.encode()) + 1
        if size > EXTRACTED_BYTES:
            _fail("CAPTURE_OUTPUT_LIMIT", 413)
    return "".join(output).encode()


def extract_static_text(
    raw: bytes, mime_type: str, checkpoint: Checkpoint = lambda: None
) -> StaticExtraction:
    checkpoint()
    if type(raw) is not bytes or not 1 <= len(raw) <= RAW_BYTES:
        _fail("CAPTURE_BODY_LIMIT", 413)
    mime = validate_mime(mime_type)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail("CAPTURE_UTF8_REQUIRED")
    # Bound validation work too, including plain/Markdown and hidden HTML.
    for offset in range(0, len(text), PARSER_CHUNK):
        checkpoint()
        _normalize(text[offset : offset + PARSER_CHUNK])
    # Normalize CRLF before chunks so a chunk edge cannot double the newline.
    text = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\x85", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
    )
    if mime == "text/html":
        if any(
            marker in text.lower()
            for marker in (
                "/cdn-cgi/challenge-platform/",
                "cf-chl-",
                "verify you are human",
                "checking your browser",
            )
        ):
            _fail("CAPTURE_AUTH_CHALLENGE_DENIED")
        parser = _StaticHTML(checkpoint)
        try:
            for offset in range(0, len(text), PARSER_CHUNK):
                checkpoint()
                parser.feed(text[offset : offset + PARSER_CHUNK])
            # close() can discard an unfinished quoted tag/comment, silently
            # turning a truncated document into a successful visible prefix.
            # Feed has already consumed every complete token: reject any tail
            # before close is allowed to repair or discard it.
            if parser.rawdata:
                _fail("CAPTURE_HTML_MALFORMED")
            parser.close()
        except (AssertionError, RecursionError):
            _fail("CAPTURE_HTML_MALFORMED")
        if parser.stack or parser.rawdata:
            _fail("CAPTURE_HTML_MALFORMED")
        text = "".join(parser.parts)
        text = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n"))
        text = re.sub(r"\n+", "\n", text).strip("\n")
    else:
        text = text.removesuffix("\n")
    if not text.strip():
        _fail("CAPTURE_EMPTY_TEXT")
    body = _wrap(text, checkpoint)
    checkpoint()
    return StaticExtraction(
        body,
        CaptureAcquisition(
            response_mime=mime,
            raw_sha256=sha256(raw).hexdigest(),
            raw_byte_count=len(raw),
            extracted_sha256=sha256(body).hexdigest(),
            extracted_byte_count=len(body),
        ),
    )


PrepareCapture = CapturePrepare
ApproveCapture = CaptureApprove
CaptureVersion = CaptureVersionInput


def build_intent(*, capture_id, url, label, session_hash, privacy_revision):
    return CaptureIntent(
        capture_id=capture_id,
        url=url,
        label=label,
        retain_capture_record=True,
        session_hash=session_hash,
        privacy_revision=privacy_revision,
        display_name=f"capture-{capture_id}.txt",
    ).model_dump()


def validate_intent(value) -> CaptureIntent:
    return CaptureIntent.model_validate(value)
