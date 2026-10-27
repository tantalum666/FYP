"""Stage a Qwen key locally without network calls or enabling a provider."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from pathlib import Path

MODEL = "qwen3.8-omni-flash-realtime"
CHAT_BASE = "https://maas.qianwenaiapi.com/compatible-mode/v1"
REALTIME_URL = "wss://maas.qianwenaiapi.com/api-ws/v1/realtime"
DEFAULT_PATH = Path.home() / ".config" / "desk-companion" / "qwen.env"


class SetupError(Exception):
    pass


def parent_fd(path: Path, *, create: bool) -> int:
    """Open each directory without following links, including ancestors."""
    if not path.is_absolute() or ".." in path.parts:
        raise SetupError("An absolute local destination is required.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parent.parts[1:]:
            try:
                child = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def write_config(path: Path, key: str) -> None:
    # Restrict env syntax. Error messages never include the supplied value.
    if not re.fullmatch(r"[A-Za-z0-9_.-]{16,512}", key):
        raise SetupError("Invalid key format; nothing was saved.")
    content = (
        "# Local staged credential. No provider is enabled.\n"
        f"DASHSCOPE_API_KEY={key}\n"
        f"FYP_QWEN_MODEL={MODEL}\n"
        f"FYP_QWEN_CHAT_BASE_URL={CHAT_BASE}\n"
        f"FYP_QWEN_REALTIME_URL={REALTIME_URL}\n"
        "DESK_VOICE_PROVIDER=none\n"
        "DESK_TEXT_PROVIDER=none\n"
        "DESK_TEXT_BACKGROUND=0\n"
    ).encode("utf-8")
    directory = parent_fd(path, create=True)
    temporary = ".qwen-setup-" + secrets.token_hex(12)
    created = False
    try:
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise SetupError("Destination directory must be owned by you and mode0700.")
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        created = True
        with os.fdopen(fd, "wb") as file:
            os.fchmod(file.fileno(), 0o600)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        # Atomic publication without replacing an existing key, file or link.
        os.link(
            temporary,
            path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
    finally:
        if created:
            os.unlink(temporary, dir_fd=directory)
        os.close(directory)


def safe_status(path: Path) -> dict:
    result = {"path": str(path), "credential_present": False, "provider_enabled": False}
    try:
        directory = parent_fd(path, create=False)
    except FileNotFoundError:
        return result
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return result
        with os.fdopen(fd, "rb") as file:
            info = os.fstat(file.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 8192:
                raise SetupError("The local config is not a small regular file.")
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise SetupError("The local config must be owned by you and mode0600.")
            values = dict(
                line.split("=", 1)
                for line in file.read().decode("utf-8").splitlines()
                if line and not line.startswith("#") and "=" in line
            )
            result["credential_present"] = bool(values.get("DASHSCOPE_API_KEY"))
            result["provider_enabled"] = any(
                values.get(name, "none") != "none"
                for name in ("DESK_VOICE_PROVIDER", "DESK_TEXT_PROVIDER")
            )
            result["mode"] = "0600"
            result["selected_model"] = MODEL
            return result
    finally:
        os.close(directory)


def read_native_key(path: Path) -> str | None:
    if sys.platform != "darwin":
        raise SetupError("Native dialog is macOS-only; use hidden terminal input on Linux.")
    # The returned key stays in the child pipe and local Python memory.
    # It is never interpolated into AppleScript or command-line arguments.
    prompt = (
        "FYP: 在本机保存千问 API Key\n"
        f"保存位置：{path}\n"
        "输入会隐藏。仅保存到本机，不发起模型请求。"
    )
    script = (
        f"text returned of (display dialog {json.dumps(prompt, ensure_ascii=False)} "
        'default answer "" with hidden answer with title "FYP Qwen Key" '
        'buttons {"取消", "保存"} default button "保存" cancel button "取消")'
    )
    completed = subprocess.run(
        ["/usr/bin/osascript", "-e", script], capture_output=True, text=True, check=False
    )
    if completed.returncode:
        if "(-128)" in completed.stderr:
            return None
        raise SetupError("The hidden input dialog did not complete; no key was saved.")
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-dialog", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    path = args.path.expanduser()
    try:
        status = safe_status(path)
        if args.status:
            print(json.dumps(status, ensure_ascii=False))
            return 0
        if status["credential_present"]:
            raise SetupError("A staged key already exists; it has not been replaced.")
        if args.native_dialog:
            print("本机隐藏输入框已打开；请在那里粘贴 Key，聊天里无需发送。", flush=True)
            key = read_native_key(path)
        else:
            if not sys.stdin.isatty():
                raise SetupError("A real terminal is required for hidden input.")
            key = getpass.getpass("Qwen API Key (hidden): ").strip()
        if key is None:
            print("已取消。没有保存密钥或发起网络请求。")
            return 0
        write_config(path, key)
        key = ""
        print(json.dumps(safe_status(path), ensure_ascii=False))
        return 0
    except SetupError as error:
        # SetupError messages are static strings and never contain input values.
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(
            f"Local save failed ({type(error).__name__}, errno={getattr(error, 'errno', None)}); "
            "the key was not displayed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
