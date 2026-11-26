"""Check the resolved colors of the Connections dialog in the compiled workspace."""

import os
from pathlib import Path
import socket

import pytest

from ui_fixture_paths import CHROME, compiled_fixture, stop_fixture

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
ROOT = Path(__file__).resolve().parents[1]


def test_connections_contrast_from_settings_and_home(tmp_path):
    if not os.access(CHROME, os.X_OK):
        pytest.skip("local Chrome is required")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    seed = (
        "import uvicorn\nfrom desk.app import create_app\n"
        f"app = create_app({str(tmp_path)!r}, development_origin={origin!r}, "
        "password='fixture', scheduler=False)\n"
        f"uvicorn.run(app, host='127.0.0.1', port={port}, log_level='warning')"
    )
    process = compiled_fixture(seed, ROOT, {**os.environ, "PYTHONPATH": str(ROOT / "backend")}, port)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROME)
            page = browser.new_page()
            login = page.request.post(
                origin + "/api/session",
                data={"username": "owner", "password": "fixture"},
                headers={"X-Desk-Request": "1"},
            )
            assert login.ok
            for scheme in ("dark", "light"):
                page.emulate_media(color_scheme=scheme)
                for entry in ("device", "assistant"):
                    page.goto(f"{origin}/?page={entry}&settings=connections")
                    dialog = page.get_by_role("dialog")
                    heading = dialog.get_by_role("heading", name="Apps", exact=True)
                    search = dialog.get_by_role("searchbox", name="Search apps")
                    heading.wait_for()
                    for target, pseudo in ((heading, None), (search, "::placeholder")):
                        ratio = target.evaluate(RENDERED_CONTRAST, pseudo)
                        assert ratio >= 4.5, (entry, scheme, pseudo, ratio)
            browser.close()
    finally:
        stop_fixture(process)


# Composite the rendered text and its ancestor backgrounds, including the
# transparent search input inside the colored search-field wrapper.
RENDERED_CONTRAST = r"""(element, pseudo) => {
  const rgba = value => value.match(/[\d.]+/g).map(Number);
  const over = (front, back) => front.slice(0, 3).map((v, i) =>
    v * (front[3] ?? 1) + back[i] * (1 - (front[3] ?? 1)));
  const luminance = rgb => rgb.reduce((sum, v, i) => {
    const x = v / 255;
    return sum + [0.2126, 0.7152, 0.0722][i] *
      (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4);
  }, 0);
  const ancestors = [];
  for (let node = element; node; node = node.parentElement) ancestors.push(node);
  const background = ancestors.reverse().reduce(
    (back, node) => over(rgba(getComputedStyle(node).backgroundColor), back), [255, 255, 255]);
  const style = getComputedStyle(element, pseudo);
  const text = rgba(style.color);
  if (pseudo) text[3] = (text[3] ?? 1) * Number(style.opacity);
  const fg = luminance(over(text, background)), bg = luminance(background);
  return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
}"""
