"""Typed, bounded application operations; no caller-selected executable or path."""

import math
import re
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .schemas import StrictModel

APP_ACTIONS = {"application"}
MAX_APP_BYTES = 8_000_000
FILENAME = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(xlsx|odt|pdf|txt|md)$"
HEX_ID = r"^[a-f0-9]{32}$"
HASH = r"^[a-f0-9]{64}$"
FORMULA_FUNCTIONS = {
    "SUM",
    "MIN",
    "MAX",
    "ROUND",
    "IF",
    "AND",
    "OR",
    "NOT",
    "COUNT",
    "COUNTA",
    "COUNTIF",
    "SUMIF",
    "ABS",
}


def safe_formula(value):
    if not value.startswith("=") or not re.fullmatch(r'[A-Za-z0-9_ $.,;:()+*/=<>!"\-]+', value):
        raise ValueError("Use bounded arithmetic and worksheet formulas")
    calls = set(re.findall(r"([A-Za-z_][A-Za-z0-9_.]*)\s*\(", value))
    if not {call.upper() for call in calls} <= FORMULA_FUNCTIONS:
        raise ValueError("Formula function is not available")
    expressions = re.sub(r'"(?:[^"]|"")*"', "", value.upper())
    for col, row in re.findall(r"\b\$?([A-Z]{1,3})\$?([0-9]+)\b", expressions):
        if len(col) != 1 or not "A" <= col <= "X" or not 1 <= int(row) <= 150:
            raise ValueError("Formula reference exceeds the bounded worksheet")
    return value


class CellEdit(StrictModel):
    cell: str = Field(pattern=r"^[A-X]([1-9]|[1-9][0-9]|1[0-4][0-9]|150)$")
    kind: Literal["text", "number", "formula"]
    value: str | Annotated[float, Field(strict=True)]
    format: Literal["plain", "money", "percent", "heading"] = "plain"

    @model_validator(mode="after")
    def typed_value(self):
        if self.kind == "number":
            if (
                not isinstance(self.value, (int, float))
                or isinstance(self.value, bool)
                or not math.isfinite(self.value)
                or abs(self.value) > 1e12
            ):
                raise ValueError("Use a finite number")
        elif not isinstance(self.value, str) or len(self.value) > 2000:
            raise ValueError("Use bounded text")
        elif self.kind == "formula":
            safe_formula(self.value)
        return self


class SheetEdit(StrictModel):
    sheet: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,29}$")
    cells: list[CellEdit] = Field(min_length=1, max_length=250)

    @model_validator(mode="after")
    def distinct(self):
        if len({c.cell for c in self.cells}) != len(self.cells):
            raise ValueError("Duplicate cell in one patch")
        return self


class WorkbookStep(StrictModel):
    kind: Literal["workbook"]
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.xlsx$")
    source_job_id: str | None = Field(default=None, pattern=HEX_ID)
    sheets: list[SheetEdit] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def bounded(self):
        if sum(len(s.cells) for s in self.sheets) > 500 or len(
            {s.sheet for s in self.sheets}
        ) != len(self.sheets):
            raise ValueError("Workbook patch too large or duplicated")
        return self


class Paragraph(StrictModel):
    kind: Literal["title", "heading", "paragraph", "page_break"]
    text: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def readable(self):
        if (self.kind == "page_break" and self.text) or (
            self.kind != "page_break" and not self.text.strip()
        ):
            raise ValueError("Use text for content and an empty page-break block")
        return self


class Table(StrictModel):
    kind: Literal["table"]
    rows: list[list[str]] = Field(min_length=1, max_length=45)

    @model_validator(mode="after")
    def rectangle(self):
        width = len(self.rows[0])
        if not 1 <= width <= 8 or any(
            len(row) != width or any(len(cell) > 500 for cell in row) for row in self.rows
        ):
            raise ValueError("Use a bounded rectangular table")
        return self


class DocumentStep(StrictModel):
    kind: Literal["document"]
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.odt$")
    source_job_id: str | None = Field(default=None, pattern=HEX_ID)
    mode: Literal["replace", "append"] = "replace"
    blocks: list[Paragraph | Table] = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def bounded(self):
        if len(self.model_dump_json()) > 60000 or (
            self.mode == "append" and not self.source_job_id
        ):
            raise ValueError("Document request is too large or lacks a base")
        return self


class PdfStep(StrictModel):
    kind: Literal["pdf"]
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.pdf$")
    source_job_id: str = Field(pattern=HEX_ID)
    replace_job_id: str | None = Field(default=None, pattern=HEX_ID)


class TextStep(StrictModel):
    kind: Literal["text"]
    filename: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.(txt|md)$")
    source_job_id: str | None = Field(default=None, pattern=HEX_ID)
    text: str = Field(min_length=1, max_length=16000)


ApplicationStep = Annotated[
    WorkbookStep | DocumentStep | PdfStep | TextStep, Field(discriminator="kind")
]


class SourceReference(StrictModel):
    source_id: str = Field(min_length=1, max_length=150)
    sha256: str = Field(pattern=HASH)


class ApplicationJobInput(StrictModel):
    action: Literal["application"] = "application"
    title: str = Field(min_length=1, max_length=120)
    task_id: str = Field(pattern=HEX_ID)
    task_version: int = Field(ge=1, strict=True)
    stage: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    depends_on: list[str] = Field(default_factory=list, max_length=12)
    sources: list[SourceReference] = Field(default_factory=list, max_length=20)
    step: ApplicationStep

    @field_validator("depends_on")
    @classmethod
    def ids(cls, value):
        if len(value) != len(set(value)) or any(not re.fullmatch(HEX_ID, v) for v in value):
            raise ValueError("Use distinct job identifiers")
        return value

    @model_validator(mode="after")
    def readable(self):
        if not self.title.strip() or len(self.model_dump_json().encode()) > 100000:
            raise ValueError("Use a readable bounded application request")
        return self


class SourceQuery(StrictModel):
    source_id: str = Field(min_length=1, max_length=150)


class ApplicationStateQuery(StrictModel):
    task_id: str = Field(pattern=HEX_ID)


class ArtifactReference(StrictModel):
    job_id: str = Field(pattern=HEX_ID)
    filename: str = Field(pattern=FILENAME)
    sha256: str = Field(pattern=HASH)
    kind: Literal["workbook", "document", "pdf", "text"]


class SavedApplicationIntent(ApplicationJobInput):
    artifact_id: str = Field(pattern=HEX_ID)
    executor: Literal["office_applications_v1"]
    scope: str = Field(pattern=r"^applications:[a-f0-9]{64}$")
    content: str = Field(max_length=200)
    dependencies: list[ArtifactReference] = Field(max_length=14)
    base: ArtifactReference | None
    previous: ArtifactReference | None
    base_snapshot: dict | None

    @model_validator(mode="after")
    def readable(self):
        # The public operation stays bounded independently of stored prior readback.
        public = {k: getattr(self, k) for k in ApplicationJobInput.model_fields}
        ApplicationJobInput.model_validate(public)
        if self.base_snapshot is not None and len(str(self.base_snapshot).encode()) > 256000:
            raise ValueError("Application base observation is too large")
        return self


class ApplicationReceipt(StrictModel):
    verified: bool = Field(strict=True)
    reason: Literal[
        "read_back_matches",
        "artifact_missing",
        "target_denied",
        "content_mismatch",
        "verification_unavailable",
        "workflow_incomplete",
    ]
    artifact: str | None = None
    bytes: int | None = Field(default=None, ge=0, le=MAX_APP_BYTES, strict=True)
    sha256: str | None = Field(default=None, pattern=HASH)
    executor: str | None = None
    scope: str | None = None
    operation_id: str | None = Field(default=None, pattern=HEX_ID)
    apps_verified: list[Literal["libreoffice_calc", "libreoffice_writer", "local_text"]] | None = (
        None
    )
    readback: dict | None = None

    @model_validator(mode="after")
    def proof(self):
        if self.verified and (
            self.reason != "read_back_matches"
            or any(
                v is None
                for v in (
                    self.artifact,
                    self.bytes,
                    self.sha256,
                    self.executor,
                    self.scope,
                    self.operation_id,
                    self.apps_verified,
                    self.readback,
                )
            )
        ):
            raise ValueError("Complete application evidence is required")
        return self
