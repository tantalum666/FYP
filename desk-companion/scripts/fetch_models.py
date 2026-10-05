"""Fetch only models listed in the checked-in manifest, verifying size and SHA-256."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def fetch(name):
    root = Path(__file__).resolve().parents[1]
    entry = json.loads((root / "config/models.json").read_text())[name]
    directory = root / ".runtime/models"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / entry["filename"]
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
        print(f"{name}: already verified")
        return target
    temporary = target.with_suffix(target.suffix + ".download")
    try:
        count, digest = 0, hashlib.sha256()
        with urlopen(entry["url"], timeout=30) as response, temporary.open("wb") as out:
            while block := response.read(65536):
                count += len(block)
                if count > entry["max_bytes"]:
                    raise ValueError("Model exceeds the documented size limit")
                digest.update(block)
                out.write(block)
        if digest.hexdigest() != entry["sha256"]:
            raise ValueError("Model checksum changed; review upstream before updating the manifest")
        temporary.replace(target)
        print(f"{name}: verified {count} bytes")
        return target
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("name", choices=["pose_lite"], default="pose_lite", nargs="?")
    fetch(parser.parse_args().name)
