"""Owner-selected Live voice; no credentials or business authority are changed."""

import hashlib
from pathlib import Path
from pydantic import Field
from .schemas import StrictModel
from .store import DomainError

# Official Live options checked 8 November 2026; names do not imply language quality.
BUILTIN_VOICES = ("marin", "gleam", "willow", "quartz", "harema", "juni")


class VoiceSelection(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    voice: str = Field(min_length=1, max_length=120)
    delivery: str = Field(default="", max_length=1600)


class VoiceRegistration(StrictModel):
    expected_version: int = Field(ge=1, strict=True)
    id: str = Field(pattern=r"^voice_[A-Za-z0-9_-]{1,100}$")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)


class VoiceSettings:
    def __init__(self, store):
        self.store = store
        with store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS assistant_voice_settings(id INTEGER PRIMARY KEY CHECK(id=1),voice TEXT NOT NULL,delivery TEXT NOT NULL,version INTEGER NOT NULL)"
            )
            conn.execute("INSERT OR IGNORE INTO assistant_voice_settings VALUES(1,'','',1)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS assistant_custom_voices(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL)"
            )

    def current(self, default="marin"):
        with self.store.connection() as conn:
            state = dict(
                conn.execute(
                    "SELECT voice,delivery,version FROM assistant_voice_settings WHERE id=1"
                ).fetchone()
            )
            profiles = [
                dict(row)
                for row in conn.execute(
                    "SELECT id,name,description FROM assistant_custom_voices ORDER BY rowid"
                )
            ]
        state["voice"] = state["voice"] or default or "marin"
        state["choices"] = [
            {"id": name, "name": name.title(), "description": "", "custom": False, "preview": False}
            for name in BUILTIN_VOICES
        ]
        state["choices"] += [
            {
                **profile,
                "custom": True,
                "preview": self.sample_path(profile["id"]).is_file()
                and not self.sample_path(profile["id"]).is_symlink(),
            }
            for profile in profiles
        ]
        state["description"] = next(
            (profile["description"] for profile in profiles if profile["id"] == state["voice"]), ""
        )
        return state

    def select(self, request, key):
        def apply(conn):
            row = conn.execute("SELECT version FROM assistant_voice_settings WHERE id=1").fetchone()
            if row[0] != request.expected_version:
                raise DomainError("VERSION_CONFLICT", 409)
            if (
                request.voice not in BUILTIN_VOICES
                and not conn.execute(
                    "SELECT 1 FROM assistant_custom_voices WHERE id=?", (request.voice,)
                ).fetchone()
            ):
                raise DomainError("VOICE_CHOICE_UNAVAILABLE", 422)
            conn.execute(
                "UPDATE assistant_voice_settings SET voice=?,delivery=?,version=version+1 WHERE id=1",
                (request.voice, request.delivery.strip()),
            )
            self.store.record(conn, "voice_settings_updated")
            return {
                "version": row[0] + 1,
                "voice": request.voice,
                "delivery": request.delivery.strip(),
            }

        return self.store.operation(key, {"type": "voice_selection", **request.model_dump()}, apply)

    def register(self, request, key):
        def apply(conn):
            version = conn.execute(
                "SELECT version FROM assistant_voice_settings WHERE id=1"
            ).fetchone()[0]
            if version != request.expected_version:
                raise DomainError("VERSION_CONFLICT", 409)
            existing = conn.execute(
                "SELECT name,description FROM assistant_custom_voices WHERE id=?", (request.id,)
            ).fetchone()
            if existing:
                if tuple(existing) != (request.name, request.description):
                    raise DomainError("VOICE_CHOICE_CONFLICT", 409)
                return {"version": version, "id": request.id}
            if conn.execute("SELECT COUNT(*) FROM assistant_custom_voices").fetchone()[0] >= 12:
                raise DomainError("VOICE_CHOICE_LIMIT", 409)
            conn.execute(
                "INSERT INTO assistant_custom_voices VALUES(?,?,?)",
                (request.id, request.name, request.description),
            )
            conn.execute("UPDATE assistant_voice_settings SET version=version+1 WHERE id=1")
            self.store.record(conn, "custom_voice_registered")
            return {"version": version + 1, "id": request.id}

        return self.store.operation(
            key, {"type": "voice_registration", **request.model_dump()}, apply
        )

    def sample_path(self, voice):
        return (
            Path(self.store.directory)
            / "voice-samples"
            / (hashlib.sha256(voice.encode()).hexdigest() + ".wav")
        )


def selected_voice_payload(voice):
    return {"id": voice} if voice.startswith("voice_") else voice
