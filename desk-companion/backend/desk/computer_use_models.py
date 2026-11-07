"""Owner-admitted public browser preparation, carried by the existing job queue."""

import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .browser_policy import PublicOnlyInput, canonical_https
from .schemas import StrictModel

COMPUTER_USE_ACTIONS = {"computer_use"}
COMPUTER_DEMOS = {"demo:shopping", "demo:flights"}
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 800
MAX_SCREEN_BYTES = 2_000_000


class ComputerUseInput(PublicOnlyInput):
    action: Literal["computer_use"] = "computer_use"
    title: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=2000)
    start_url: str = Field(min_length=1, max_length=2000)
    allowed_origins: list[str] = Field(default_factory=list, max_length=8)
    share_screen: bool = Field(strict=True)
    max_steps: int = Field(default=8, ge=1, le=12, strict=True)
    task_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    task_version: int | None = Field(default=None, ge=1, strict=True)
    source_job_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def scope(self):
        try:
            self.title.encode("utf-8")
            self.goal.encode("utf-8")
        except UnicodeError:
            raise ValueError("Use valid Unicode text") from None
        if self.share_screen is not True:
            raise ValueError("Explicit screenshot sharing is required")
        if (self.task_id is None) != (self.task_version is None):
            raise ValueError("Task ID and version must be selected together")
        if not self.title.strip() or not self.goal.strip():
            raise ValueError("A task goal is required")
        if self.start_url in COMPUTER_DEMOS:
            if self.allowed_origins:
                raise ValueError("Demo pages cannot add external sites")
            return self
        initial = canonical_https(self.start_url)
        if not initial:
            raise ValueError("Choose a public HTTPS page without credentials")
        origins = {f"https://{initial.hostname}"}
        for origin in self.allowed_origins:
            parsed = canonical_https(origin)
            if not parsed or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                raise ValueError("Choose exact HTTPS site origins")
            origins.add(f"https://{parsed.hostname}")
        if len(origins) > 8:
            raise ValueError("At most eight exact sites may be admitted")
        self.allowed_origins = sorted(origins)
        return self


def validate_computer_request(request):
    public = {k: request[k] for k in ComputerUseInput.model_fields}
    ComputerUseInput.model_validate(public)
    extra = {
        "artifact_id",
        "executor",
        "scope",
        "content",
        "session_hash",
        "privacy_revision",
        "provider_revision",
        "source_state_sha256",
    }
    if set(request) != set(public) | extra:
        raise ValueError("Incomplete computer-use intent")
    for name in ("session_hash", "privacy_revision", "provider_revision"):
        if not isinstance(request[name], str) or not re.fullmatch(r"[a-f0-9]{64}", request[name]):
            raise ValueError("Invalid admission binding")
    if request["executor"] != "public_browser_computer_v1" or not re.fullmatch(
        r"public_browser:[a-f0-9]{64}", request["scope"]
    ):
        raise ValueError("Invalid computer environment")
    source_hash = request["source_state_sha256"]
    if (request["source_job_id"] is None) != (source_hash is None) or (
        source_hash is not None and not re.fullmatch(r"[a-f0-9]{64}", source_hash)
    ):
        raise ValueError("Invalid browser continuation")
    if (
        not re.fullmatch(r"[a-f0-9]{32}", request["artifact_id"])
        or request["content"] != request["goal"]
    ):
        raise ValueError("Invalid computer-use identity")
    return request


class ComputerUseReceipt(StrictModel):
    verified: bool
    reason: str
    artifact: str
    bytes: int = Field(ge=1, le=128000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    executor: Literal["public_browser_computer_v1"]
    scope: str
    outcome: Literal["review_ready", "needs_owner", "step_limit"]
    quality: Literal["not_goal_completion"] = "not_goal_completion"
    readback: dict


def origin_of(url):
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"
