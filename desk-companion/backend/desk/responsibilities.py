"""Explicit local task-change enrollment; no provider or Work dispatch."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field, ValidationError, field_validator, model_validator

from .calendar import iso, wall_to_utc
from .schemas import EventInput, StrictModel
from .store import DomainError, encode
from .tasks import TaskStep
from .work_limits import WATCH_COUNT
from .responsibility_retention import (
    CHARGED_WATCH_PREDICATE,
    LIFETIME_IDENTITIES,
    TOMBSTONE,
    PreviewCache,
    RetentionAction,
    RetentionPreviewRequest,
    decode_body,
    digest,
    install_watch_triggers,
    owner_epoch,
    receipt_count,
    validate_retention_row,
    validate_watch_schema,
    watch_accounting,
)

WatchField = Literal["status", "due", "next_step", "waiting_for", "steps", "progress"]
FIELDS = ("status", "due", "next_step", "waiting_for", "steps", "progress")
DEFAULT_FIELDS = ["status", "due", "progress"]
TERMINAL = {"cancelled", "expired", "budget_exhausted"}
LIMITS = dict(
    definitions=WATCH_COUNT,
    tasks_per_definition=10,
    review_history=50,
    lifetime_reviews=100,
    daily_reviews=20,
    duration_days=30,
    ordinary_operations=256,
)
TaskID = Annotated[str, Field(min_length=1, max_length=64, strict=True)]
# Explicit safe projection for hidden stop controls. It never loads private JSON.
WATCH_METADATA_COLUMNS = (
    "id,version,generation,status,created_at,updated_at,baseline_at,expires_at,"
    "review_budget,reviews_used,daily_review_budget,budget_day,daily_used,blocked_code,eval_order,"
    "retention_state,retention_version,trashed_at,restored_at,purged_at"
)


def fingerprint(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


class ResponsibilitySelection(StrictModel):
    task_ids: list[TaskID] = Field(min_length=1, max_length=10)
    fields: list[WatchField] = Field(min_length=1, max_length=6)

    @field_validator("task_ids", "fields")
    @classmethod
    def unique(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Use unique selections")
        for value in values:
            value.encode("utf-8")
        return sorted(values)


class ResponsibilityCreate(ResponsibilitySelection):
    title: str = Field(min_length=1, max_length=160, strict=True)
    kind: Literal["selected_task_changes"]
    scope_revision: str = Field(pattern=r"^[a-f0-9]{64}$", strict=True)
    retain_change_history: Literal[True]
    expires_at: datetime
    review_budget: int = Field(ge=1, le=100, strict=True)
    daily_review_budget: int = Field(default=10, ge=1, le=20, strict=True)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        value.encode("utf-8")
        return EventInput.title_not_blank(value)

    @field_validator("retain_change_history", mode="before")
    @classmethod
    def explicit_retention(cls, value):
        if value is not True:
            raise ValueError("Explicit retention acknowledgment is required")
        return value

    @field_validator("expires_at")
    @classmethod
    def utc_expiry(cls, value):
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("Use an explicit UTC expiry")
        return value.astimezone(UTC)

    @model_validator(mode="before")
    @classmethod
    def supported_kind(cls, value):
        if isinstance(value, dict) and (
            any(k in value for k in ("source_ids", "artifact_ids", "event_ids"))
            or value.get("kind", "selected_task_changes") != "selected_task_changes"
        ):
            raise DomainError("RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED", 422)
        return value


class ResponsibilityAction(StrictModel):
    action: Literal["pause", "resume", "cancel", "recheck"]
    expected_version: int = Field(ge=1, strict=True)
    resume_policy: Literal["baseline_now"] | None = None

    @model_validator(mode="after")
    def policy(self):
        if (self.action == "resume") != (self.resume_policy == "baseline_now"):
            raise ValueError("Resume requires baseline_now; other actions cannot set it")
        return self


class ResponsibilityAcknowledge(StrictModel):
    expected_review_version: int = Field(ge=1, strict=True)


class ResponsibilityService:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.retention_previews = PreviewCache(self.store.clock)
        with self.store.connection(write=True) as conn:
            validate_watch_schema(conn)
            install_watch_triggers(conn)

    def _authority(self, conn, principal, *, visible=True):
        if (
            not isinstance(principal, dict)
            or principal.get("kind") != "owner"
            or not isinstance(principal.get("session"), str)
            or not principal["session"]
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        token_hash = hashlib.sha256(principal["session"].encode()).hexdigest()
        if not conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (token_hash, iso(self.store.clock())),
        ).fetchone():
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        hidden = self.store.settings(conn)["hide_private"]
        if visible and hidden:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
        return hidden

    def _reply(
        self, result, principal, *, visible=True, privacy_version=None, authority_epoch=None
    ):
        # A fresh snapshot catches logout/hide while the first read was in progress.
        with self.store.connection() as conn:
            self._authority(conn, principal, visible=visible)
            if visible and self.store.settings(conn)["version"] != privacy_version:
                raise DomainError("RESPONSIBILITY_CONTEXT_CHANGED")
            if (
                authority_epoch is not None
                and owner_epoch(conn, principal, self.store) != authority_epoch
            ):
                raise DomainError("RESPONSIBILITY_CONTEXT_CHANGED")
        return result

    @staticmethod
    def _get(conn, responsibility_id, *, private=True):
        columns = "*" if private else WATCH_METADATA_COLUMNS
        row = conn.execute(
            f"SELECT {columns} FROM responsibilities WHERE id=?", (responsibility_id,)
        ).fetchone()
        if row is None:
            raise DomainError("RESPONSIBILITY_NOT_FOUND", 404)
        return row

    def _projection(self, conn, task_id, fields):
        row = conn.execute(
            "SELECT id,data,status,version FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        try:
            if row is None:
                raise ValueError()
            data = json.loads(row["data"])
            if not isinstance(data, dict):
                raise ValueError()
            note = conn.execute(
                "SELECT id FROM task_evidence WHERE task_id=? AND kind='note' "
                "ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
            values = {}
            for field in fields:
                if field == "status":
                    value = row["status"]
                    if value not in {"todo", "in_progress", "waiting", "completed", "cancelled"}:
                        raise ValueError()
                elif field == "progress":
                    value = note[0] if note else None
                elif field == "due":
                    due, zone = data["due_local"], data["timezone"]
                    EventInput.valid_zone(zone)
                    if due is not None:
                        local = EventInput.local_datetime(datetime.fromisoformat(due))
                        wall_to_utc(local, zone, reject_ambiguous=True)
                    value = [due, zone]
                elif field == "steps":
                    value = data["steps"]
                    if not isinstance(value, list) or len(value) > 20:
                        raise ValueError()
                    value = [
                        TaskStep.model_validate(step).model_dump(mode="json") for step in value
                    ]
                else:
                    value = data[field]
                    if not isinstance(value, str) or len(value) > 500:
                        raise ValueError()
                values[field] = fingerprint(["task-field-v1", field, value])
            token = {"version": row["version"], "progress_id": note[0] if note else None}
            return {"id": task_id, "hashes": values, "token": token}
        except (ValueError, TypeError, KeyError, ValidationError, UnicodeError, OverflowError):
            raise DomainError("RESPONSIBILITY_SOURCE_UNAVAILABLE") from None

    @staticmethod
    def _label(conn, task_id):
        row = conn.execute(
            "SELECT id,data,version,status FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        try:
            title = json.loads(row["data"])["title"] if row else None
            if not isinstance(title, str) or not title.strip() or len(title) > 160:
                raise ValueError()
            title.encode("utf-8")
            return dict(
                id=task_id,
                title=title,
                version=row["version"],
                status=row["status"],
                available=True,
            )
        except (ValueError, TypeError, KeyError, UnicodeError):
            return dict(id=task_id, title="", version=None, status=None, available=False)

    def _scope(self, conn, ids, fields):
        projections = [self._projection(conn, task_id, fields) for task_id in ids]
        return fingerprint(["selected-task-scope-v1", ids, fields, projections]), projections

    def scope(self, principal, task_ids=None, fields=None):
        fields = list(DEFAULT_FIELDS if fields is None else fields)
        ids = list(task_ids or [])
        try:
            selection = ResponsibilitySelection(
                task_ids=ids or ["candidate-placeholder"], fields=fields
            )
        except ValidationError:
            raise DomainError("VALIDATION_FAILED", 422) from None
        ids, fields = sorted(ids), selection.fields
        with self.store.connection() as conn:
            self._authority(conn, principal)
            privacy_version = self.store.settings(conn)["version"]
            revision = self._scope(conn, ids, fields)[0] if ids else None
            candidates = ids or [
                r[0]
                for r in conn.execute("SELECT id FROM tasks ORDER BY updated_at DESC,id LIMIT 500")
            ]
            labels = [self._label(conn, task_id) for task_id in candidates]
            result = dict(
                tasks=[
                    {k: v for k, v in label.items() if k != "available"}
                    for label in labels
                    if label["available"]
                ],
                selected_task_ids=ids,
                fields=fields,
                scope_revision=revision,
                server_time=iso(self.store.clock()),
                limits=LIMITS,
                truncated=not ids
                and conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] > 500,
            )
        return self._reply(result, principal, privacy_version=privacy_version)

    def _view(self, conn, row, hidden=False):
        validate_retention_row(row)
        body = decode_body(row) if not hidden else None
        keys = (
            "id",
            "version",
            "generation",
            "status",
            "created_at",
            "updated_at",
            "baseline_at",
            "expires_at",
            "review_budget",
            "reviews_used",
            "daily_review_budget",
            "budget_day",
            "daily_used",
            "blocked_code",
            "retention_state",
            "retention_version",
            "trashed_at",
            "restored_at",
            "purged_at",
        )
        result = {key: row[key] for key in keys}
        result.update(
            hidden=hidden,
            pending_count=conn.execute(
                "SELECT COUNT(*) FROM responsibility_reviews WHERE responsibility_id=? AND delivery_state='pending'",
                (row["id"],),
            ).fetchone()[0],
        )
        if not hidden:
            result.update(body)
        return result

    @staticmethod
    def _review(row):
        return {
            **{key: row[key] for key in row.keys() if key != "data"},
            **json.loads(row["data"]),
            "title_source": "current_record",
            "result_code": "SELECTED_TASK_FIELDS_CHANGED",
        }

    def listing(self, principal):
        with self.store.connection() as conn:
            hidden = self._authority(conn, principal, visible=False)
            privacy_version = self.store.settings(conn)["version"]
            items = [
                self._view(conn, row, hidden)
                for row in conn.execute(
                    f"SELECT {WATCH_METADATA_COLUMNS if hidden else '*'} FROM responsibilities WHERE retention_state='retained' ORDER BY created_at DESC,id LIMIT 21"
                )
            ]
            result = dict(
                responsibilities=items,
                maintenance_usage=watch_accounting(conn),
                hidden=hidden,
                pending_count=sum(item["pending_count"] for item in items),
                revision=self.store.revision(conn),
                server_time=iso(self.store.clock()),
                limits=LIMITS,
            )
        return self._reply(result, principal, visible=not hidden, privacy_version=privacy_version)

    def detail(self, responsibility_id, principal):
        with self.store.connection() as conn:
            self._authority(conn, principal)
            privacy_version = self.store.settings(conn)["version"]
            row = self._get(conn, responsibility_id)
            self._require_retained(row)
            result = dict(
                responsibility=self._view(conn, row),
                reviews=[
                    self._review(review)
                    for review in conn.execute(
                        "SELECT * FROM responsibility_reviews WHERE responsibility_id=? ORDER BY sequence DESC LIMIT 51",
                        (responsibility_id,),
                    )
                ],
                selected_tasks=[
                    self._label(conn, task_id) for task_id in decode_body(row)["task_ids"]
                ],
                revision=self.store.revision(conn),
            )
        return self._reply(result, principal, privacy_version=privacy_version)

    def _operation(self, key, request, principal, apply, *, visible=True):
        if not isinstance(key, str) or not 1 <= len(key) <= 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        request_hash = fingerprint(request)
        with self.store.connection(write=True) as conn:
            hidden = self._authority(conn, principal, visible=visible)
            privacy_version = self.store.settings(conn)["version"]
            authority_epoch = owner_epoch(conn, principal, self.store)
            old = conn.execute(
                "SELECT * FROM responsibility_operations WHERE id=?", (key,)
            ).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise DomainError("OPERATION_ID_CONFLICT")
                responsibility_id, review_id, kind = (
                    old["responsibility_id"],
                    old["review_id"],
                    old["kind"],
                )
            else:
                responsibility_id, review_id, kind = apply(conn)
                conn.execute(
                    "INSERT INTO responsibility_operations VALUES(?,?,?,?,?)",
                    (key, request_hash, responsibility_id, review_id, kind),
                )
                self.store.bump(conn)
            row = self._get(conn, responsibility_id, private=not hidden)
            if row["retention_state"] != "retained":
                # Private maintenance/history is never a hidden-mode control.
                self._authority(conn, principal)
                validate_retention_row(row)
                hidden = False
                result = dict(
                    kind="retention_disposition",
                    responsibility_id=responsibility_id,
                    retention_state=row["retention_state"],
                    retention_version=row["retention_version"],
                    original_operation_kind=kind,
                    review_id=review_id,
                    operation_id=key,
                    revision=self.store.revision(conn),
                    recorded_success=True,
                )
            else:
                result = dict(
                    responsibility=self._view(conn, row, hidden),
                    operation_id=key,
                    revision=self.store.revision(conn),
                    saved=True,
                )
                if kind == "acknowledge":
                    result.update(review_id=review_id, acknowledged=True)
        return self._reply(
            result,
            principal,
            visible=not hidden,
            privacy_version=privacy_version,
            authority_epoch=authority_epoch,
        )

    @staticmethod
    def _require_retained(row):
        if row["retention_state"] != "retained":
            raise DomainError("RESPONSIBILITY_RETAINED_STATE_REQUIRED")
        validate_retention_row(row)

    @staticmethod
    def _operation_capacity(conn, responsibility_id, action):
        count = conn.execute(
            "SELECT COUNT(*) FROM responsibility_operations WHERE responsibility_id=?",
            (responsibility_id,),
        ).fetchone()[0]
        if count >= LIMITS["ordinary_operations"] and action not in {"pause", "cancel"}:
            raise DomainError("RESPONSIBILITY_OPERATION_LIMIT", 422)

    def create(self, payload, key, principal):
        data = payload.model_dump(mode="json")

        def apply(conn):
            if (
                len(
                    conn.execute(
                        f"SELECT 1 FROM responsibilities WHERE {CHARGED_WATCH_PREDICATE} LIMIT ?",
                        (LIMITS["definitions"],),
                    ).fetchall()
                )
                >= LIMITS["definitions"]
            ):
                raise DomainError("RESPONSIBILITY_LIMIT", 422)
            usage = watch_accounting(conn, LIMITS["definitions"])
            if usage["state"] != "known":
                raise DomainError("RESPONSIBILITY_METADATA_UNAVAILABLE")
            if usage["lifetime_count"] >= LIFETIME_IDENTITIES:
                raise DomainError("RESPONSIBILITY_METADATA_LIMIT", 422)
            for existing in conn.execute(
                f"SELECT * FROM responsibilities WHERE {CHARGED_WATCH_PREDICATE} LIMIT ?",
                (LIMITS["definitions"] + 1,),
            ):
                decode_body(existing)
            now = self.store.clock()
            if not now < payload.expires_at <= now + timedelta(days=LIMITS["duration_days"]):
                raise DomainError("RESPONSIBILITY_EXPIRY_INVALID", 422)
            revision, projections = self._scope(conn, payload.task_ids, payload.fields)
            if revision != payload.scope_revision:
                raise DomainError("RESPONSIBILITY_SCOPE_CHANGED")
            responsibility_id = uuid4().hex
            definition = {
                k: data[k] for k in ("title", "kind", "task_ids", "fields", "retain_change_history")
            }
            conn.execute(
                "INSERT INTO responsibilities(id,data,version,generation,status,created_at,updated_at,baseline_at,expires_at,review_budget,reviews_used,daily_review_budget,budget_day,daily_used,blocked_code,eval_order) VALUES(?,?,1,1,'active',?,?,?,?,?,0,?,?,0,NULL,0)",
                (
                    responsibility_id,
                    encode(definition),
                    iso(now),
                    iso(now),
                    iso(now),
                    iso(payload.expires_at),
                    payload.review_budget,
                    payload.daily_review_budget,
                    now.astimezone(UTC).date().isoformat(),
                ),
            )
            for projection in projections:
                conn.execute(
                    "INSERT INTO responsibility_sources VALUES(?,?,0,0,?,?)",
                    (
                        responsibility_id,
                        projection["id"],
                        encode(projection["token"]),
                        encode(projection["hashes"]),
                    ),
                )
            return responsibility_id, None, "create"

        return self._operation(key, {"type": "create", "data": data}, principal, apply)

    def action(self, responsibility_id, payload, key, principal):
        def apply(conn):
            row = self._get(
                conn, responsibility_id, private=payload.action not in {"pause", "cancel"}
            )
            self._require_retained(row)
            if row["version"] != payload.expected_version:
                raise DomainError("VERSION_CONFLICT")
            if row["status"] in TERMINAL or row["expires_at"] <= iso(self.store.clock()):
                raise DomainError("RESPONSIBILITY_CLOSED")
            action = payload.action
            valid = (
                (action == "pause" and row["status"] in {"active", "blocked"})
                or action == "cancel"
                or (action == "resume" and row["status"] == "paused")
                or (action == "recheck" and row["status"] == "blocked")
            )
            if not valid:
                raise DomainError("RESPONSIBILITY_ACTION_INVALID")
            self._operation_capacity(conn, responsibility_id, action)
            now, baseline = iso(self.store.clock()), row["baseline_at"]
            if action in {"resume", "recheck"}:
                data = json.loads(row["data"])
                projections = [
                    self._projection(conn, task_id, data["fields"]) for task_id in data["task_ids"]
                ]
                if action == "resume":
                    baseline = now
                    for projection in projections:
                        conn.execute(
                            "UPDATE responsibility_sources SET consumed_generation=dirty_generation,observed_source_token=?,field_hashes=? "
                            "WHERE responsibility_id=? AND source_id=?",
                            (
                                encode(projection["token"]),
                                encode(projection["hashes"]),
                                responsibility_id,
                                projection["id"],
                            ),
                        )
            state = {
                "pause": "paused",
                "cancel": "cancelled",
                "resume": "active",
                "recheck": "active",
            }[action]
            conn.execute(
                "UPDATE responsibilities SET status=?,version=version+1,generation=generation+1,updated_at=?,baseline_at=?,blocked_code=NULL WHERE id=?",
                (state, now, baseline, responsibility_id),
            )
            if action in {"pause", "cancel"}:
                conn.execute(
                    "UPDATE responsibility_reviews SET delivery_state='dismissed',version=version+1 WHERE responsibility_id=? AND delivery_state='pending'",
                    (responsibility_id,),
                )
            return responsibility_id, None, action

        return self._operation(
            key,
            {"type": "action", "id": responsibility_id, **payload.model_dump(mode="json")},
            principal,
            apply,
            visible=payload.action not in {"pause", "cancel"},
        )

    def acknowledge(self, responsibility_id, review_id, payload, key, principal):
        def apply(conn):
            self._require_retained(self._get(conn, responsibility_id))
            row = conn.execute(
                "SELECT * FROM responsibility_reviews WHERE id=? AND responsibility_id=?",
                (review_id, responsibility_id),
            ).fetchone()
            if row is None:
                raise DomainError("REVIEW_NOT_FOUND", 404)
            if row["version"] != payload.expected_review_version:
                raise DomainError("REVIEW_CHANGED")
            if row["delivery_state"] != "pending":
                raise DomainError("REVIEW_NOT_PENDING")
            self._operation_capacity(conn, responsibility_id, "acknowledge")
            conn.execute(
                "UPDATE responsibility_reviews SET delivery_state='acknowledged',version=version+1 WHERE id=?",
                (review_id,),
            )
            return responsibility_id, review_id, "acknowledge"

        return self._operation(
            key,
            {
                "type": "acknowledge",
                "id": responsibility_id,
                "review_id": review_id,
                **payload.model_dump(),
            },
            principal,
            apply,
        )

    def maintenance_listing(self, principal):
        with self.store.connection() as conn:
            self._authority(conn, principal)
            epoch = owner_epoch(conn, principal, self.store)
            usage = watch_accounting(conn)
            items = [
                self._view(conn, row)
                for row in conn.execute(
                    "SELECT * FROM responsibilities WHERE retention_state='trashed' ORDER BY trashed_at DESC,id LIMIT 21"
                )
            ]
            result = dict(
                responsibilities=items,
                maintenance_usage=usage,
                revision=self.store.revision(conn),
                server_time=iso(self.store.clock()),
            )
        return self._reply(result, principal, privacy_version=epoch[1], authority_epoch=epoch)

    def maintenance_detail(self, responsibility_id, principal):
        with self.store.connection() as conn:
            self._authority(conn, principal)
            epoch = owner_epoch(conn, principal, self.store)
            row = self._get(conn, responsibility_id)
            body = decode_body(row)  # Purged identities return stable 410, not a fake receipt.
            result = dict(
                responsibility=self._view(conn, row),
                reviews=[
                    self._review(review)
                    for review in conn.execute(
                        "SELECT * FROM responsibility_reviews WHERE responsibility_id=? ORDER BY sequence DESC LIMIT 51",
                        (responsibility_id,),
                    )
                ],
                selected_tasks=[self._label(conn, task_id) for task_id in body["task_ids"]],
                revision=self.store.revision(conn),
            )
        return self._reply(result, principal, privacy_version=epoch[1], authority_epoch=epoch)

    def _retention_inventory(self, conn, row):
        body = decode_body(row)
        sources = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM responsibility_sources WHERE responsibility_id=? ORDER BY source_id LIMIT 11",
                (row["id"],),
            )
        ]
        reviews = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM responsibility_reviews WHERE responsibility_id=? ORDER BY id LIMIT 51",
                (row["id"],),
            )
        ]
        if (
            len(sources) > 10
            or len(reviews) > 50
            or {s["source_id"] for s in sources} != set(body["task_ids"])
            or any(r["delivery_state"] == "pending" for r in reviews)
            or any(len(encode(item).encode("utf-8")) > 65536 for item in sources + reviews)
        ):
            raise DomainError("RESPONSIBILITY_METADATA_UNAVAILABLE")
        count = receipt_count(conn, row["id"])
        return digest([dict(row), sources, reviews, count]), len(sources), len(reviews), count

    @staticmethod
    def _retention_transition(row, payload, count):
        validate_retention_row(row)
        if (
            row["version"] != payload.expected_version
            or row["retention_version"] != payload.expected_retention_version
        ):
            raise DomainError("VERSION_CONFLICT")
        if row["status"] not in TERMINAL:
            raise DomainError("RESPONSIBILITY_NOT_TERMINAL")
        state, action = row["retention_state"], payload.action
        if (
            action == "trash"
            and state != "retained"
            or action == "restore"
            and state != "trashed"
            or action == "purge"
            and state not in {"retained", "trashed"}
        ):
            raise DomainError("RESPONSIBILITY_RETENTION_INVALID")
        if action == "trash" and count > LIMITS["ordinary_operations"] - 2:
            raise DomainError("RESPONSIBILITY_OPERATION_LIMIT", 422)
        if action == "restore" and count > LIMITS["ordinary_operations"] - 1:
            raise DomainError("RESPONSIBILITY_OPERATION_LIMIT", 422)
        if action == "purge" and count > LIMITS["ordinary_operations"] + 2:
            raise DomainError("RESPONSIBILITY_OPERATION_LIMIT", 422)

    @staticmethod
    def _retention_binding(row, payload, epoch, inventory):
        return (
            row["id"],
            payload.action,
            payload.expected_version,
            payload.expected_retention_version,
            epoch,
            inventory,
        )

    def retention_preview(self, responsibility_id, payload, principal):
        with self.store.connection() as conn:
            self._authority(conn, principal)
            epoch = owner_epoch(conn, principal, self.store)
            row = self._get(conn, responsibility_id)
            count = receipt_count(conn, responsibility_id)
            self._retention_transition(row, payload, count)
            inventory, sources, reviews, count = self._retention_inventory(conn, row)
            binding = self._retention_binding(row, payload, epoch, inventory)
            preview_id, expiry = self.retention_previews.issue(binding)
            result = dict(
                kind="watch_retention_preview",
                preview_id=preview_id,
                action=payload.action,
                responsibility={
                    **{
                        k: row[k]
                        for k in ("id", "status", "version", "retention_state", "retention_version")
                    },
                    "title": decode_body(row)["title"],
                },
                counts=dict(
                    definitions=1,
                    source_baselines=sources,
                    retained_reviews=reviews,
                    operation_receipts=count,
                ),
                retained_operation_receipts_after=count + 1,
                logical_slots_released=1 if payload.action == "purge" else 0,
                receipts_retained=True,
                independent_tasks_retained=True,
                independent_work_retained=True,
                expires_at=expiry,
                maintenance_usage=watch_accounting(conn),
                revision=self.store.revision(conn),
            )
        return self._reply(result, principal, privacy_version=epoch[1], authority_epoch=epoch)

    def retention_action(self, responsibility_id, payload, key, principal):
        def apply(conn):
            # _operation has already checked the durable original-key receipt and
            # actual visible owner in this write transaction before this closure.
            row = self._get(conn, responsibility_id)
            epoch = owner_epoch(conn, principal, self.store)
            count = receipt_count(conn, responsibility_id)
            self._retention_transition(row, payload, count)
            inventory, _, _, _ = self._retention_inventory(conn, row)
            self.retention_previews.check(
                payload.preview_id, self._retention_binding(row, payload, epoch, inventory)
            )
            now = iso(self.store.clock())
            if payload.action == "purge":
                # DB-only: body/history, tombstone and receipt commit together.
                conn.execute(
                    "DELETE FROM responsibility_sources WHERE responsibility_id=?",
                    (responsibility_id,),
                )
                conn.execute(
                    "DELETE FROM responsibility_reviews WHERE responsibility_id=?",
                    (responsibility_id,),
                )
                conn.execute(
                    "UPDATE responsibilities SET data=?,retention_state='purged',retention_version=retention_version+1,purged_at=? WHERE id=?",
                    (TOMBSTONE, now, responsibility_id),
                )
            elif payload.action == "trash":
                conn.execute(
                    "UPDATE responsibilities SET retention_state='trashed',retention_version=retention_version+1,trashed_at=? WHERE id=?",
                    (now, responsibility_id),
                )
            else:
                conn.execute(
                    "UPDATE responsibilities SET retention_state='retained',retention_version=retention_version+1,restored_at=? WHERE id=?",
                    (now, responsibility_id),
                )
            return responsibility_id, None, payload.action

        return self._operation(
            key,
            {
                "type": "retention",
                "id": responsibility_id,
                **payload.model_dump(mode="json", exclude_unset=True),
            },
            principal,
            apply,
        )

    def _evaluate(self, conn, row, now):
        current = self._get(conn, row["id"])
        self._require_retained(current)
        if current["generation"] != row["generation"] or current["status"] != "active":
            raise DomainError("RESPONSIBILITY_CLOSED")
        responsibility_id, data = row["id"], decode_body(row)
        sources = conn.execute(
            "SELECT * FROM responsibility_sources WHERE responsibility_id=? ORDER BY source_id",
            (responsibility_id,),
        ).fetchall()
        if {s["source_id"] for s in sources} != set(data["task_ids"]):
            raise DomainError("RESPONSIBILITY_SOURCE_UNAVAILABLE")
        projections = {
            source["source_id"]: self._projection(conn, source["source_id"], data["fields"])
            for source in sources
        }
        changed_ids, changed_fields = set(), set()
        for source in sources:
            old, new = (
                json.loads(source["field_hashes"]),
                projections[source["source_id"]]["hashes"],
            )
            changed = {field for field in data["fields"] if old[field] != new[field]}
            if changed:
                changed_ids.add(source["source_id"])
                changed_fields.update(changed)
        pending = conn.execute(
            "SELECT * FROM responsibility_reviews WHERE responsibility_id=? AND delivery_state='pending'",
            (responsibility_id,),
        ).fetchone()
        day = max(row["budget_day"], now.astimezone(UTC).date().isoformat())
        used = row["daily_used"] if day == row["budget_day"] else 0
        if changed_ids and not pending:
            if row["reviews_used"] >= row["review_budget"]:
                conn.execute(
                    "UPDATE responsibilities SET status='budget_exhausted',version=version+1,generation=generation+1,updated_at=? WHERE id=?",
                    (iso(now), responsibility_id),
                )
                return True
            if used >= row["daily_review_budget"]:
                return False
        if changed_ids:
            review_data = dict(
                changed_ids=sorted(changed_ids),
                changed_fields=sorted(changed_fields),
                from_tokens={
                    s["source_id"]: json.loads(s["observed_source_token"]) for s in sources
                },
                to_tokens={key: projection["token"] for key, projection in projections.items()},
                catch_up=any(s["dirty_generation"] - s["consumed_generation"] > 1 for s in sources),
            )
            if pending:
                old_data = json.loads(pending["data"])
                review_data.update(
                    changed_ids=sorted(changed_ids | set(old_data["changed_ids"])),
                    changed_fields=sorted(changed_fields | set(old_data["changed_fields"])),
                    from_tokens=old_data["from_tokens"],
                    catch_up=True,
                )
                conn.execute(
                    "UPDATE responsibility_reviews SET data=?,version=version+1,last_observed_at=? WHERE id=?",
                    (encode(review_data), iso(now), pending["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO responsibility_reviews VALUES(?,?,?,1,'pending',?,?,?)",
                    (
                        uuid4().hex,
                        responsibility_id,
                        row["reviews_used"] + 1,
                        encode(review_data),
                        iso(now),
                        iso(now),
                    ),
                )
                conn.execute(
                    "UPDATE responsibilities SET reviews_used=reviews_used+1,budget_day=?,daily_used=?,updated_at=? WHERE id=?",
                    (day, used + 1, iso(now), responsibility_id),
                )
                conn.execute(
                    "DELETE FROM responsibility_reviews WHERE responsibility_id=? AND delivery_state!='pending' "
                    "AND id NOT IN (SELECT id FROM responsibility_reviews WHERE responsibility_id=? ORDER BY sequence DESC LIMIT ?)",
                    (responsibility_id, responsibility_id, LIMITS["review_history"]),
                )
        for source in sources:
            projection = projections[source["source_id"]]
            conn.execute(
                "UPDATE responsibility_sources SET consumed_generation=dirty_generation,observed_source_token=?,field_hashes=? WHERE responsibility_id=? AND source_id=?",
                (
                    encode(projection["token"]),
                    encode(projection["hashes"]),
                    responsibility_id,
                    source["source_id"],
                ),
            )
        return bool(changed_ids)

    def advance(self):
        """At most ten dirty definitions, called through an independent worker boundary."""
        with self.store.connection(write=True) as conn:
            now = self.store.clock()
            expired = conn.execute(
                "UPDATE responsibilities SET status='expired',version=version+1,generation=generation+1,updated_at=? "
                "WHERE retention_state='retained' AND status IN ('active','paused','blocked') AND expires_at<=?",
                (iso(now), iso(now)),
            ).rowcount
            if expired:
                conn.execute(
                    "UPDATE responsibility_reviews SET delivery_state='dismissed',version=version+1 "
                    "WHERE delivery_state='pending' AND responsibility_id IN "
                    "(SELECT id FROM responsibilities WHERE retention_state='retained' AND status='expired')"
                )
            rows = conn.execute(
                "SELECT * FROM responsibilities WHERE retention_state='retained' AND status='active' AND EXISTS "
                "(SELECT 1 FROM responsibility_sources s WHERE s.responsibility_id=responsibilities.id "
                "AND s.dirty_generation!=s.consumed_generation) "
                "AND (daily_used<daily_review_budget OR budget_day<? OR reviews_used>=review_budget OR EXISTS "
                "(SELECT 1 FROM responsibility_reviews rr WHERE rr.responsibility_id=responsibilities.id AND rr.delivery_state='pending')) "
                "ORDER BY eval_order,id LIMIT 10",
                (now.astimezone(UTC).date().isoformat(),),
            ).fetchall()
            changed = bool(expired)
            for row in rows:
                order = conn.execute(
                    "SELECT COALESCE(MAX(eval_order),0)+1 FROM responsibilities"
                ).fetchone()[0]
                conn.execute(
                    "UPDATE responsibilities SET eval_order=? WHERE id=?", (order, row["id"])
                )
                conn.execute("SAVEPOINT watch_evaluation")
                try:
                    evaluated = self._evaluate(conn, row, now)
                    conn.execute("RELEASE watch_evaluation")
                    changed = evaluated or changed
                except (DomainError, ValueError, KeyError, TypeError, UnicodeError):
                    conn.execute("ROLLBACK TO watch_evaluation")
                    conn.execute("RELEASE watch_evaluation")
                    conn.execute(
                        "UPDATE responsibilities SET status='blocked',blocked_code='RESPONSIBILITY_SOURCE_UNAVAILABLE',"
                        "version=version+1,generation=generation+1,updated_at=? WHERE id=?",
                        (iso(now), row["id"]),
                    )
                    changed = True
            if changed:
                self.store.bump(conn)
        return len(rows)

    tick = advance


def responsibility_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/responsibilities", dependencies=[Depends(owner)])

    def principal(request, authenticated):
        return {**authenticated, "session": request.cookies.get("desk_companion_session")}

    @router.get("/scope")
    def scope(
        request: Request,
        task_id: list[str] = Query(default=[]),
        field: list[str] | None = Query(default=None),
        authenticated=Depends(owner),
    ):
        return runtime.responsibilities.scope(principal(request, authenticated), task_id, field)

    @router.get("")
    def listing(request: Request, authenticated=Depends(owner)):
        return runtime.responsibilities.listing(principal(request, authenticated))

    @router.post("")
    def create(
        payload: ResponsibilityCreate,
        request: Request,
        key=Depends(operation_id),
        authenticated=Depends(owner),
    ):
        return runtime.responsibilities.create(payload, key, principal(request, authenticated))

    @router.get("/maintenance")
    def maintenance_listing(request: Request, authenticated=Depends(owner)):
        return runtime.responsibilities.maintenance_listing(principal(request, authenticated))

    @router.get("/{responsibility_id}/maintenance")
    def maintenance_detail(responsibility_id: str, request: Request, authenticated=Depends(owner)):
        return runtime.responsibilities.maintenance_detail(
            responsibility_id, principal(request, authenticated)
        )

    @router.post("/{responsibility_id}/maintenance-preview")
    def retention_preview(
        responsibility_id: str,
        payload: RetentionPreviewRequest,
        request: Request,
        authenticated=Depends(owner),
    ):
        return runtime.responsibilities.retention_preview(
            responsibility_id, payload, principal(request, authenticated)
        )

    @router.post("/{responsibility_id}/retention")
    def retention_action(
        responsibility_id: str,
        payload: RetentionAction,
        request: Request,
        key=Depends(operation_id),
        authenticated=Depends(owner),
    ):
        return runtime.responsibilities.retention_action(
            responsibility_id, payload, key, principal(request, authenticated)
        )

    @router.get("/{responsibility_id}")
    def detail(responsibility_id: str, request: Request, authenticated=Depends(owner)):
        return runtime.responsibilities.detail(responsibility_id, principal(request, authenticated))

    @router.post("/{responsibility_id}/actions")
    def action(
        responsibility_id: str,
        payload: ResponsibilityAction,
        request: Request,
        key=Depends(operation_id),
        authenticated=Depends(owner),
    ):
        return runtime.responsibilities.action(
            responsibility_id, payload, key, principal(request, authenticated)
        )

    @router.post("/{responsibility_id}/reviews/{review_id}/acknowledge")
    def acknowledge(
        responsibility_id: str,
        review_id: str,
        payload: ResponsibilityAcknowledge,
        request: Request,
        key=Depends(operation_id),
        authenticated=Depends(owner),
    ):
        return runtime.responsibilities.acknowledge(
            responsibility_id, review_id, payload, key, principal(request, authenticated)
        )

    return router
