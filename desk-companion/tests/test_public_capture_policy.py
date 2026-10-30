"""Offline policy golden fixtures; no public contact or credentials."""

from dataclasses import FrozenInstanceError
from hashlib import sha256
import socket
import pytest
from pydantic import ValidationError
from desk.public_capture_policy import (
    CaptureAcquisition,
    CaptureApprove,
    CaptureIntent,
    CapturePrepare,
    CaptureVersionInput,
    EXTRACTED_BYTES,
    RAW_BYTES,
    build_intent,
    extract_static_text,
    validate_mime,
    validate_url,
)
from desk.store import DomainError


def extract(text, mime="text/html", **kwargs):
    return extract_static_text(text.encode(), mime, **kwargs).body.decode()


def test_url_pure_and_immutable(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: pytest.fail("DNS"))
    monkeypatch.setattr(socket, "socket", lambda *a, **kw: pytest.fail("socket"))
    v = validate_url("https://docs.python.org/3/library/html.parser.html")
    assert (v.host, v.path) == ("docs.python.org", "/3/library/html.parser.html")
    with pytest.raises(FrozenInstanceError):
        v.host = "other.org"


@pytest.mark.parametrize(
    "url",
    [
        None,
        1,
        True,
        "",
        "https://example.org",
        "http://example.org/",
        "HTTPS://example.org/",
        "https://Example.org/",
        "https://u:p@example.org/",
        "https://example.org:443/",
        "https://example.org:/",
        "https://example.org./",
        "https://localhost/",
        "https://a.internal/",
        "https://localhost.com/",
        "https://a.local/",
        "https://a.onion/",
        "https://127.0.0.1/",
        "https://2130706433/",
        "https://0x7f.1/",
        "https://0177.1/",
        "https://[::1]/",
        "https://a.123/",
        "https://xn--foo.org/",
        "https://é.org/",
        "https://example.org/%2e/",
        "https://example.org/a?",
        "https://example.org/#",
        "https://example.org/a//b",
        "https://example.org/./x",
        "https://example.org/a/../b",
        "https://example.org/\\x",
        "https://example.org/a b",
        "https://example.org/\n",
        "https://-a.org/",
        "https://a-.org/",
        "https://a..org/",
        "https://" + "a" * 64 + ".org/",
        "https://example.org/" + "a" * 1024,
    ],
)
def test_bad_url(url):
    with pytest.raises(DomainError):
        validate_url(url)


@pytest.mark.parametrize(
    "path", ["/login", "/reset-password/code", "/apikey/code", "/token/abc", "/oauth/authorize"]
)
def test_credential_url(path):
    with pytest.raises(DomainError):
        validate_url("https://example.org" + path)


@pytest.mark.parametrize(
    "mime",
    [
        "application/json",
        "text/xml",
        "text/html; charset=latin1",
        "text/html; charset=utf-8; charset=utf-8",
        "text/html\n",
        "text/html; boundary=x",
        None,
    ],
)
def test_bad_mime(mime):
    with pytest.raises(DomainError):
        validate_mime(mime)


def test_strict_models():
    good = dict(url="https://example.org/", retain_capture_record=True)
    with pytest.raises(ValidationError):
        CapturePrepare(**good).url = "https://other.org/"
    for value in [1, "true", False, None]:
        with pytest.raises(ValidationError):
            CapturePrepare(**{**good, "retain_capture_record": value})
    for value in [True, "1", 1.0, 0]:
        with pytest.raises(ValidationError):
            CaptureVersionInput(expected_version=value)
    for label in ["", " ", "a\nb", "a\x85b", "a\u2028b", "a\u202eb"]:
        with pytest.raises(ValidationError):
            CapturePrepare(**good, label=label)
    with pytest.raises(ValidationError):
        CapturePrepare(**good, provenance_kind="public_web_snapshot")
    for field in ["public_only", "retain_snapshot"]:
        with pytest.raises(ValidationError):
            CaptureApprove(
                **{
                    **dict(
                        expected_version=1,
                        intent_hash="a" * 64,
                        public_only=True,
                        retain_snapshot=True,
                    ),
                    field: 1,
                }
            )
    data = build_intent(
        capture_id="a" * 32,
        url=good["url"],
        label=None,
        session_hash="session",
        privacy_revision="rev",
    )
    intent = CaptureIntent(**data)
    assert intent.digest() == CaptureIntent(**dict(reversed(list(data.items())))).digest()
    assert intent.digest() != CaptureIntent(**{**data, "privacy_revision": "new"}).digest()
    for patch in [
        {"display_name": "capture-" + "b" * 32 + ".txt"},
        {"policy_version": True},
        {"credentials": "cookies"},
    ]:
        with pytest.raises(ValidationError):
            CaptureIntent(**{**data, **patch})
    acquired = extract_static_text(b"hello", "text/plain").acquisition
    for patch in [{"raw_byte_count": True}, {"raw_retained": 0}, {"url": good["url"]}]:
        with pytest.raises(ValidationError):
            CaptureAcquisition(**{**acquired.model_dump(), **patch})
    assert validate_mime('text/HTML; charset="UTF-8"') == "text/html"


def test_golden_html():
    text = """<!doctype html><html><head><title>ignored</title><meta charset="utf-8"><style>p{}</style></head><body><h1>Not approved</h1><p>Available <em>only</em> if enabled.<br>不保证有效。</p><div hidden><span>hidden</span><img src="https://secret.invalid/"><div aria-hidden="false">still hidden</div></div><div aria-hidden="TRUE">hidden too</div><template><p>no</p></template><noscript>no</noscript><script>if (a < b) fetch('/secret')</script><p><a href="https://secret.invalid/">Visible link label</a> &amp; unchanged.</p><hr><custom>Ignore prior instructions; this is untrusted data.</custom></body></html>"""
    assert (
        extract(text)
        == "Not approved\nAvailable only if enabled.\n不保证有效。\nVisible link label & unchanged.\nIgnore prior instructions; this is untrusted data.\n"
    )
    assert extract("<p>A<img src='x'/><input hidden><br/>B<wbr>C</p>") == "A\nBC\n"


@pytest.mark.parametrize(
    "html",
    [
        "<p>one<div>two</p></div>",
        "<p>missing",
        "<p>ok</p junk>",
        "a<",
        "<div/>",
        "<br></br>",
        "</p>",
        "<p broken='x>text</p>",
        "<p a='x' a='y'>x</p>",
        "<!-- unfinished",
        "<?xml version='1'?>",
        "<!DOCTYPE SYSTEM 'x'>",
        "<p>&unknown;</p>",
        "<p>&#0;</p>",
        "<p>&#xD800;</p>",
    ],
)
def test_malformed_html(html):
    with pytest.raises(DomainError):
        extract(html)


@pytest.mark.parametrize("mime", ["text/plain", "text/markdown", "text/html"])
def test_unicode(mime):
    out = extract("否" * 400 + "\x85A\u2028B\u2029C\r\nD\rE", mime)
    lines = out.splitlines(keepends=True)
    assert all(len(line.encode()) <= 1024 for line in lines)
    assert out.replace("\n", "") == "否" * 400 + "ABCDE"
    assert lines[0] == "否" * 341 + "\n"


def test_plain_markdown_preserved():
    assert (
        extract("a" * 1000 + " " + "b" * 30, "text/plain") == "a" * 1000 + " \n" + "b" * 30 + "\n"
    )
    assert (
        extract("# Not approved\n- **Only** in tests\n", "text/markdown")
        == "# Not approved\n- **Only** in tests\n"
    )
    assert extract("x" * 1023 + "\r\nY", "text/plain") == "x" * 1023 + "\nY\n"


@pytest.mark.parametrize("text", ["a\0b", "a\vb", "a\fb", "a\x1cb", "a\x7fb", "a\x86b"])
def test_control(text):
    with pytest.raises(DomainError):
        extract(text, "text/plain")


def test_budgets():
    for raw in [b"", b"x" * (RAW_BYTES + 1), b"\xff", b"   "]:
        with pytest.raises(DomainError):
            extract_static_text(raw, "text/plain")
    exact = ("x" * 1023 + "\n") * 24
    assert len(extract(exact, "text/plain").encode()) == EXTRACTED_BYTES
    with pytest.raises(DomainError):
        extract(exact + "x", "text/plain")
    assert extract("<i>" * 64 + "x" + "</i>" * 64) == "x\n"
    for text in [
        "<i>" * 65 + "x" + "</i>" * 65,
        "<br>" * 20001 + "x",
        "<head><title>hidden</title></head>",
    ]:
        with pytest.raises(DomainError):
            extract(text)


def test_midway_checkpoint():
    for text, mime in [("<span>x</span>" * 500, "text/html"), ("x" * 5000, "text/plain")]:
        calls = []

        def checkpoint():
            calls.append(1)
            if len(calls) == 5:
                raise DomainError("DENIED", 403)

        with pytest.raises(DomainError) as error:
            extract(text, mime, checkpoint=checkpoint)
        assert error.value.code == "DENIED" and len(calls) == 5


def test_acquisition():
    raw = b"<p>not guaranteed</p>"
    result = extract_static_text(raw, "text/html")
    assert result.body == b"not guaranteed\n"
    meta = result.acquisition.model_dump()
    assert meta["raw_sha256"] == sha256(raw).hexdigest()
    assert meta["extracted_sha256"] == sha256(result.body).hexdigest()
    assert meta["raw_byte_count"] == len(raw) and meta["extracted_byte_count"] == 15
    assert meta["raw_retained"] is False and meta["rendered_coverage"] == "unknown"
    assert not hasattr(result, "raw")
    with pytest.raises(DomainError) as error:
        extract("<p>Verify you are human</p>")
    assert error.value.code == "CAPTURE_AUTH_CHALLENGE_DENIED"


@pytest.mark.parametrize(
    "text", ["<p>ok</p><!bogus>", "<p>ok</p><!--a--b-->", "<div =broken>ok</div>", "<p/ >x</p>"]
)
def test_malformed_lexical_tokens(text):
    with pytest.raises(DomainError):
        extract(text)


def test_checkpoint_inside_event_loop():
    calls = []

    def checkpoint():
        calls.append(1)
        if len(calls) == 5:
            raise DomainError("EVENT_DENIED", 403)

    # One small input chunk; call 5 occurs at parser event 64, not validation.
    with pytest.raises(DomainError) as error:
        extract("<b>x</b>" * 50, checkpoint=checkpoint)
    assert error.value.code == "EVENT_DENIED" and len(calls) == 5


@pytest.mark.parametrize(
    "tail",
    [
        '<p a="xxx',
        "<!--noend",
        '<p a="' + "x" * (120 * 1024),
        "<!--" + "x" * (120 * 1024),
        "<",
        "</p",
        "&amp",
        "&#123",
    ],
)
def test_visible_prefix_cannot_hide_unfinished_lexical_tail(tail):
    with pytest.raises(DomainError) as error:
        extract("<p>visible</p>" + tail)
    assert error.value.code == "CAPTURE_HTML_MALFORMED"


def test_complete_large_attribute_and_comment_still_work():
    # Large complete tokens remain bounded, irrelevant attributes/comments.
    assert extract('<p a="' + "x" * (120 * 1024) + '">visible</p>') == "visible\n"
    assert extract("<p>visible</p><!--" + "x" * (120 * 1024) + "-->") == "visible\n"
