"""Download only the pinned public model files; never execute archive contents."""

import hashlib
import io
import json
import tarfile
from pathlib import Path
import httpx


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "config/wake-model.json").read_text())
    target = root / ".runtime/models/wake"
    target.mkdir(parents=True, exist_ok=True)
    if all(
        (target / name).is_file()
        and hashlib.sha256((target / name).read_bytes()).hexdigest() == entry["sha256"]
        for name, entry in manifest["files"].items()
    ):
        print("Wake model already verified.")
        return
    content = bytearray()
    with httpx.stream("GET", manifest["url"], follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > 128_000_000:
                raise ValueError("Download too large")
    if hashlib.sha256(content).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Archive checksum mismatch")
    found = set()
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:bz2") as archive:
        for item in archive.getmembers():
            name = Path(item.name).name
            if name not in manifest["files"] or not item.isfile():
                continue
            if name in found:
                raise ValueError("Duplicate archive entry")
            expected = manifest["files"][name]
            if item.size != expected["bytes"]:
                raise ValueError("Invalid model size")
            data = archive.extractfile(item).read()
            if hashlib.sha256(data).hexdigest() != expected["sha256"]:
                raise ValueError("Model checksum mismatch")
            temp = target / (name + ".part")
            temp.write_bytes(data)
            temp.replace(target / name)
            found.add(name)
    if found != set(manifest["files"]):
        raise ValueError("Archive is incomplete")
    print("Wake model downloaded and verified.")


if __name__ == "__main__":
    main()
