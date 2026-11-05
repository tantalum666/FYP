"""Operator-configured execution transport and explicitly scoped source reads."""

import hashlib
import json
import os
import re
import stat
import subprocess
import time
from pathlib import Path

from .computer import ExecutionRejected, open_owner_directory
from .store import DomainError


def read_regular(path, limit=8_000_000):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    directory = open_owner_directory(path.parent)
    try:
        fd = os.open(path.name, flags, dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(fd, "rb") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError("APPLICATION_TARGET_DENIED")
        body = file.read(limit + 1)
        if len(body) > limit:
            raise ValueError("APPLICATION_TARGET_DENIED")
        return body


def rooted(root, relative):
    if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
        raise DomainError("APPLICATION_TARGET_DENIED", 403)
    path = root / relative
    if path.resolve() != path.absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise DomainError("APPLICATION_TARGET_DENIED", 403)
    return path


class ApplicationBridge:
    """Fixed helper invocation; model data never becomes a command or environment."""

    def __init__(self):
        self.engine = os.environ.get("DESK_APP_ENGINE", "docker")
        self.context = (
            os.environ.get("DESK_APP_DOCKER_CONTEXT", "") if self.engine == "docker" else ""
        )
        self.container = os.environ.get("DESK_APP_CONTAINER", "")
        self.configured = bool(
            self.engine in {"docker", "podman"}
            and (self.engine == "podman" or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", self.context))
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", self.container)
        )

    @property
    def scope(self):
        # Preserve existing Docker receipts; selecting another engine must fence
        # admitted work even when its paths and container name are unchanged.
        result = {"context": self.context, "container": self.container}
        if self.engine != "docker":
            result["engine"] = self.engine
        return result

    def run(self, payload, checkpoint=lambda: None, cancel_file=None):
        if not self.configured:
            raise ExecutionRejected("APPLICATION_UNAVAILABLE", 409)
        prefix = (
            ["docker", "--context", self.context]
            if self.engine == "docker"
            else ["podman", "--remote=false"]
        )
        command = prefix + [
            "exec",
            "-i",
            "--user",
            "desk",
            self.container,
            "timeout",
            "--kill-after=2s",
            "35s",
            "python3",
            "/opt/desk/application_bridge.py",
        ]
        checkpoint()
        environment = {
            k: v
            for k, v in os.environ.items()
            if k
            in {
                "PATH",
                "HOME",
                "USER",
                "LANG",
                "LC_ALL",
                "TMPDIR",
                "DOCKER_CONFIG",
                "XDG_RUNTIME_DIR",
            }
        }
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=environment,
        )
        body = json.dumps(payload, ensure_ascii=False).encode()
        deadline = time.monotonic() + 40
        try:
            while True:
                checkpoint()
                if time.monotonic() > deadline:
                    raise ExecutionRejected("APPLICATION_BRIDGE_TIMEOUT", 409)
                try:
                    output, _stderr = process.communicate(input=body, timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    body = None
            if process.returncode or len(output) > 500000:
                if cancel_file is not None:
                    (cancel_file.parent / "bridge-error.json").write_text(
                        json.dumps(
                            {
                                "exit": process.returncode,
                                "output": output.decode(errors="replace")[:2000],
                                "stderr": _stderr.decode(errors="replace")[:2000],
                            }
                        )
                    )
                raise ExecutionRejected("APPLICATION_BRIDGE_FAILED", 409)
            parsed = json.loads(output)
            if not isinstance(parsed, dict) or parsed.get("error"):
                raise ExecutionRejected("APPLICATION_BRIDGE_FAILED", 409)
            return parsed
        except BaseException:
            if cancel_file is not None:
                cancel_file.touch(mode=0o600, exist_ok=True)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
            raise


class ApplicationSources:
    def __init__(self, bridge):
        self.bridge = bridge
        raw = os.environ.get("DESK_APPLICATION_INPUTS")
        self.root = Path(raw).absolute() if raw else None
        self.fingerprint = hashlib.sha256(str(self.root).encode()).hexdigest()

    def listing(self):
        if self.root is None or not self.root.is_dir():
            return {"configured": False, "sources": []}
        sources = []
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in {".md", ".csv", ".txt", ".html"} or not path.is_file():
                continue
            relative = path.relative_to(self.root)
            if any(part.startswith(".") for part in relative.parts):
                continue
            safe = rooted(self.root, str(relative))
            body = read_regular(safe, 64000)
            sources.append(
                {
                    "source_id": str(relative),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "kind": "browser" if path.suffix.lower() == ".html" else "text",
                }
            )
            if len(sources) > 100:
                raise DomainError("APPLICATION_SOURCE_LIMIT", 422)
        return {"configured": True, "sources": sources}

    def content(self, source_id):
        item = next((v for v in self.listing()["sources"] if v["source_id"] == source_id), None)
        if item is None:
            raise DomainError("APPLICATION_SOURCE_NOT_FOUND", 404)
        path = rooted(self.root, source_id)
        if item["kind"] == "browser":
            observation = self.bridge.run({"mode": "browser", "source_id": source_id})
            if len(observation.get("text", "")) > 40000:
                raise DomainError("APPLICATION_SOURCE_LIMIT", 422)
        else:
            observation = {"text": read_regular(path, 64000).decode("utf-8")}
        if hashlib.sha256(read_regular(path, 64000)).hexdigest() != item["sha256"]:
            raise DomainError("APPLICATION_SOURCE_CHANGED", 409)
        return {**item, "observation": observation, "untrusted_source": True}

    def check(self, references):
        current = {v["source_id"]: v["sha256"] for v in self.listing()["sources"]}
        if any(current.get(r["source_id"]) != r["sha256"] for r in references):
            raise ExecutionRejected("APPLICATION_SOURCE_CHANGED", 409)
