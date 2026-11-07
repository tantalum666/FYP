import asyncio

import pytest

from desk.computer_use_observation import snapshot, scoped_storage
from desk.computer_use_worker import Boundary
from desk.store import DomainError


@pytest.mark.parametrize("when", ["screen", "dom"])
@pytest.mark.parametrize("outside", [True, False])
def test_navigation_during_capture_is_not_persisted_or_mixed(tmp_path, monkeypatch, when, outside):
    boundary = Boundary(["https://allowed.example"])

    async def allow(_):
        pass

    monkeypatch.setattr("desk.computer_use_observation.checkpoint", allow)

    class Page:
        url = "https://allowed.example/one"
        captures = 0
        changed = False

        def move(self):
            if not self.changed:
                self.changed = True
                boundary.document_generation += 1
                # Same URL reload is also a different document.
                if outside:
                    self.url = "https://unapproved.example/private"

        async def screenshot(self, **_):
            self.captures += 1
            value = b"old-page-image" if not self.changed else b"new-page-image"
            if when == "screen":
                self.move()
            return value

        async def evaluate(self, _):
            if when == "dom":
                self.move()
            return {
                "title": "new document" if self.changed else "old document",
                "text": "content",
                "controls": [],
            }

    page = Page()
    if outside:
        with pytest.raises(DomainError, match="BROWSER_TARGET_CHANGED"):
            asyncio.run(snapshot(page, tmp_path, 1, boundary))
        assert not list(tmp_path.iterdir())
    else:
        result = asyncio.run(snapshot(page, tmp_path, 1, boundary))
        assert page.captures == 2 and result["document_generation"] == 1
        assert result["title"] == "new document"
        assert (tmp_path / result["screen"]).read_bytes() == b"new-page-image"


def test_resume_storage_drops_unadmitted_origins_and_cookies():
    raw = {
        "origins": [
            {"origin": "https://shop.example", "localStorage": []},
            {"origin": "https://outside.example", "localStorage": []},
        ],
        "cookies": [
            {"name": "kept", "domain": ".shop.example", "value": "fixture"},
            {"name": "dropped", "domain": "outside.example", "value": "fixture"},
        ],
    }
    result = scoped_storage(raw, {"https://shop.example"})
    assert [x["origin"] for x in result["origins"]] == ["https://shop.example"]
    assert [x["name"] for x in result["cookies"]] == ["kept"]
    assert len(raw["origins"]) == 2
