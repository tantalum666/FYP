"""Check the two bundled presentation assets without downloading or changing them."""

import hashlib
import json
from pathlib import Path


def check_assets(frontend: Path) -> list[str]:
    failures = []
    public = frontend / "public"
    manifests = [("avatars", "source.json"), ("companion", "source.json")]
    for directory, filename in manifests:
        manifest = public / directory / filename
        try:
            source = json.loads(manifest.read_text(encoding="utf-8"))
            entries = (
                [{"image": source["asset"], "sha256": source["sha256"]}]
                if directory == "avatars"
                else source["assets"]
            )
            if not isinstance(entries, list) or not entries:
                raise ValueError("empty asset list")
            for entry in entries:
                name, expected = entry["image"], entry["sha256"]
                if (
                    not isinstance(name, str)
                    or Path(name).name != name
                    or name in {"", ".", ".."}
                    or not isinstance(expected, str)
                    or len(expected) != 64
                    or any(character not in "0123456789abcdef" for character in expected)
                ):
                    raise ValueError("invalid asset identity")
                asset = public / directory / name
                if not asset.is_file():
                    failures.append(f"Missing bundled asset: public/{directory}/{name}")
                elif hashlib.sha256(asset.read_bytes()).hexdigest() != expected:
                    failures.append(f"Asset hash mismatch: public/{directory}/{name}")
        except (OSError, ValueError, KeyError, TypeError):
            failures.append(f"Unreadable or invalid manifest: public/{directory}/{filename}")
    return failures


def main() -> int:
    frontend = Path(__file__).resolve().parents[1] / "frontend"
    failures = check_assets(frontend)
    for failure in failures:
        print(failure)
    if failures:
        return 1
    print("Bundled VRM and A1 asset hashes match their provenance manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
