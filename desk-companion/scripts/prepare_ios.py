"""Use checksum-verified official frameworks when Xcode's downloader is unavailable.

Run after `npx cap sync ios`. This changes only the generated Capacitor package
reference. Application source and the official framework binaries are untouched.
"""

import hashlib
import json
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
VERSION = "8.5.2"
CHECKSUMS = {
    "Capacitor": "134c65a8bd30bfaa8ccb158d78142fa7231bf3f472e4a5d808c5fbed90fd4c75",
    "Cordova": "57ff2c8f1e5dcd8d4379ac3cccde1407d81ccd575347dc2aff4f72272b8794a1",
}


def main():
    installed = json.loads(
        (ROOT / "frontend/node_modules/@capacitor/ios/package.json").read_text()
    )["version"]
    if installed != VERSION:
        raise SystemExit("Check upstream Package.swift checksums before changing the SDK version.")
    directory = ROOT / ".runtime/ios-vendor"
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in CHECKSUMS.items():
        archive = directory / (name + ".zip")
        if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            content = bytearray()
            with httpx.stream(
                "GET",
                f"https://github.com/ionic-team/capacitor-swift-pm/releases/download/{VERSION}/{name}.xcframework.zip",
                follow_redirects=True,
                timeout=60,
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 50_000_000:
                        raise ValueError("Framework download too large")
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError("Framework checksum mismatch")
            archive.write_bytes(content)
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                if entry.filename.startswith("/") or ".." in Path(entry.filename).parts:
                    raise ValueError("Invalid archive path")
            bundle.extractall(directory)
    (directory / "Package.swift").write_text("""// swift-tools-version:5.9
import PackageDescription
let package = Package(name: "DeskCapacitorVendor", products: [.library(name: "Capacitor", targets: ["Capacitor"]), .library(name: "Cordova", targets: ["Cordova"])], targets: [.binaryTarget(name: "Capacitor", path: "Capacitor.xcframework"), .binaryTarget(name: "Cordova", path: "Cordova.xcframework")])
""")
    package = ROOT / "frontend/ios/App/CapApp-SPM/Package.swift"
    text = package.read_text()
    remote = (
        f'.package(url: "https://github.com/ionic-team/capacitor-swift-pm.git", exact: "{VERSION}")'
    )
    local = '.package(name: "capacitor-swift-pm", path: "../../../../.runtime/ios-vendor")'
    if remote not in text and local not in text:
        raise ValueError("Unexpected Capacitor package layout")
    package.write_text(text.replace(remote, local))
    print("Official iOS frameworks verified; local Swift package prepared.")


if __name__ == "__main__":
    main()
