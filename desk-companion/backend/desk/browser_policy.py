"""Experimental public-only catalog, never a general URL or browser-code tool.

Request filtering and DNS checks are defense in depth, NOT a network sandbox.
Only fixed public sources and an owner-reviewed synthetic/public brief are admitted.
"""

import hashlib
import ipaddress
import os
import re
import socket
import stat
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from .schemas import StrictModel
from .store import DomainError, encode

ADAPTER = "stackedit_markdown_v1"
CATALOG_VERSION = 1
STACKEDIT_URL = "https://stackedit.io/app"
STACKEDIT_ORIGIN = "https://stackedit.io"
MAX_EXPORT_BYTES = 64 * 1024
SOURCE_CATALOG = {
    "python_asyncio": {
        "url": "https://docs.python.org/3/library/asyncio.html",
        "label": "Python official documentation: asyncio",
    },
    "python_pathlib": {
        "url": "https://docs.python.org/3/library/pathlib.html",
        "label": "Python official documentation: pathlib",
    },
}
ID_PATTERN = r"^[a-f0-9]{32}$"
SHA_PATTERN = r"^[a-f0-9]{64}$"


class PublicOnlyInput(StrictModel):
    public_only: Literal[True]

    @field_validator("public_only", mode="before")
    @classmethod
    def explicit_acknowledgment(cls, value):
        if value is not True:
            raise ValueError("Explicit public/synthetic acknowledgment required")
        return value


class PublicObservationInput(PublicOnlyInput):
    source_id: Literal["python_asyncio", "python_pathlib"]


class BrowserJobInput(PublicOnlyInput):
    observation_id: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=2000)
    public_only: Literal[True]

    @field_validator("title", "note")
    @classmethod
    def valid_text(cls, value):
        value.encode("utf-8")
        if any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("Unsupported control character")
        return value

    @field_validator("title")
    @classmethod
    def title_line(cls, value):
        if not value.strip() or "\n" in value or "\t" in value:
            raise ValueError("Use one nonblank title line")
        return value


class BrowserApproval(PublicOnlyInput):
    expected_version: int = Field(ge=1, strict=True)
    intent_hash: str = Field(pattern=SHA_PATTERN)
    public_only: Literal[True]


class SourceObservation(StrictModel):
    id: str = Field(pattern=ID_PATTERN)
    source_id: Literal["python_asyncio", "python_pathlib"]
    url: str = Field(max_length=160)
    title: str = Field(min_length=1, max_length=300)
    heading: str = Field(min_length=1, max_length=300)
    excerpt: str = Field(min_length=1, max_length=1800)
    sha256: str = Field(pattern=SHA_PATTERN)
    observed_at: str = Field(max_length=40)
    version: Literal[1] = 1


class BrowserIntent(PublicOnlyInput):
    adapter: Literal["stackedit_markdown_v1"] = ADAPTER
    catalog_version: Literal[1] = CATALOG_VERSION
    job_id: str = Field(pattern=ID_PATTERN)
    environment_id: str = Field(pattern=SHA_PATTERN)
    source: SourceObservation
    title: str = Field(min_length=1, max_length=120)
    document_name: str = Field(pattern=r"^fyp-source-[a-f0-9]{32}$")
    content: str = Field(min_length=1, max_length=16000)
    destination: Literal["https://stackedit.io/app"] = STACKEDIT_URL
    public_only: Literal[True]
    persistence: Literal["ephemeral_editor_retained_export"] = "ephemeral_editor_retained_export"


class BrowserReceipt(StrictModel):
    verified: Literal[True]
    adapter: Literal["stackedit_markdown_v1"]
    catalog_version: Literal[1]
    job_id: str = Field(pattern=ID_PATTERN)
    execution_id: str = Field(pattern=ID_PATTERN)
    intent_hash: str = Field(pattern=SHA_PATTERN)
    source_sha256: str = Field(pattern=SHA_PATTERN)
    environment_id: str = Field(pattern=SHA_PATTERN)
    destination: Literal["https://stackedit.io/app"]
    document_name: str = Field(pattern=r"^fyp-source-[a-f0-9]{32}$")
    sha256: str = Field(pattern=SHA_PATTERN)
    byte_count: int = Field(ge=1, le=MAX_EXPORT_BYTES, strict=True)
    download_count: Literal[1]
    export_method: Literal["stackedit_ui_markdown_download"]
    browser_version: str = Field(min_length=1, max_length=100)
    sandbox_requested: Literal[True]
    browser_close_confirmed: Literal[True]
    network_boundary: Literal["routing_only"]
    data_scope: Literal["public_synthetic_only"]


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def source_entry(source_id):
    if source_id not in SOURCE_CATALOG:
        raise DomainError("BROWSER_SOURCE_DENIED", 403)
    return SOURCE_CATALOG[source_id]


def canonical_https(url):
    """Canonical public HTTPS shape. Matching the catalog is a separate check."""
    try:
        p = urlsplit(url)
        if (
            p.scheme != "https" or not p.hostname or p.username or p.password or p.port
            or p.netloc != p.hostname or "\\" in url or "%" in p.netloc
            or any(ord(c) <= 32 for c in url)
        ):
            return None
        return p
    except (ValueError, TypeError):
        return None


def request_allowed(url, method, *, source_id=None, destination=False, navigation=False):
    p = canonical_https(url)
    if not p or method != "GET":
        return False
    if destination:
        if p.hostname != "stackedit.io" or p.query or p.fragment:
            return False
        if navigation:
            return url == STACKEDIT_URL
        # Reviewed static app paths; no auth/sync/publish/API endpoints.
        return p.path == "/app" or bool(re.fullmatch(
            r"/static/(?:js|css|fonts|img)/[A-Za-z0-9_.-]+", p.path
        )) or bool(re.fullmatch(r"/icons-[a-f0-9]+/[A-Za-z0-9_.-]+", p.path))
    entry = source_entry(source_id)
    if navigation:
        return url == entry["url"]
    if p.hostname != "docs.python.org":
        return False
    return url == entry["url"] or bool(re.fullmatch(
        r"/3/_static/[A-Za-z0-9_.-]+", p.path
    )) and (not p.query or bool(re.fullmatch(r"v=[A-Za-z0-9]+", p.query))) and not p.fragment


def require_public_dns(host, resolver=socket.getaddrinfo):
    """Preflight only: does not pin Chromium DNS or prevent rebinding."""
    try:
        addresses = {row[4][0] for row in resolver(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise ValueError("Non-public address")
    except (OSError, ValueError):
        raise DomainError("BROWSER_PUBLIC_DNS_REQUIRED", 409) from None


def quoted_text(value):
    """Literal Markdown text, not links/images/HTML or an executable instruction."""
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_{}\[\]()#!|])", r"\\\1", value)


def brief_content(observation, title, note):
    return (
        f"# {quoted_text(title)}\n\n"
        f"Source: {observation['url']}\n\n"
        f"Retrieved (UTC): {observation['observed_at']}\n\n"
        f"Source title: {quoted_text(observation['title'])}\n\n"
        f"Observed heading: {quoted_text(observation['heading'])}\n\n"
        "## Observed excerpt (untrusted source data)\n\n"
        + "\n".join("> " + quoted_text(line) for line in observation["excerpt"].splitlines())
        + "\n\n## Owner-provided public/synthetic note\n\n"
        + "\n".join("> " + quoted_text(line) for line in (note or "(none)").splitlines())
        + "\n"
    )


def safe_read(directory, filename, limit=MAX_EXPORT_BYTES):
    """Fixed-slot independent readback; no supplied paths, links or special files."""
    if filename not in {"export.md", "receipt.json"}:
        raise DomainError("BROWSER_ARTIFACT_DENIED", 403)
    root = os.open(Path(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise DomainError("BROWSER_ARTIFACT_DENIED", 403)
            body = stream.read(limit + 1)
            if len(body) > limit:
                raise DomainError("BROWSER_ARTIFACT_TOO_LARGE", 422)
            return body
    finally:
        os.close(root)


def exclusive_write(directory, filename, body):
    """Copies actual downloaded bytes / evidence, never synthesizes a final export."""
    if filename not in {"export.md", "receipt.json"} or len(body) > MAX_EXPORT_BYTES:
        raise DomainError("BROWSER_ARTIFACT_DENIED", 403)
    root = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=root)
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(root)
    finally:
        os.close(root)
