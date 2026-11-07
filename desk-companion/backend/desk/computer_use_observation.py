"""Observe one admitted document; discard captures that race a navigation."""

import hashlib
import sys
from urllib.parse import urlsplit

from .browser_worker import checkpoint
from .computer_use_files import write_file
from .computer_use_models import MAX_SCREEN_BYTES, SCREEN_HEIGHT, SCREEN_WIDTH, origin_of
from .store import DomainError


def same_document(page, boundary, observation):
    return (
        page.url == observation["url"]
        and boundary.document_generation == observation["document_generation"]
        and origin_of(page.url) in boundary.origins
    )


def scoped_storage(state, origins):
    hosts = {urlsplit(origin).hostname for origin in origins}
    return {
        "origins": [item for item in state.get("origins", []) if item["origin"] in origins],
        "cookies": [
            item
            for item in state.get("cookies", [])
            if any(
                host == item["domain"].lstrip(".")
                or host.endswith("." + item["domain"].lstrip("."))
                for host in hosts
                if host
            )
        ],
    }


async def snapshot(page, directory, sequence, boundary):
    for _ in range(3):
        await checkpoint("computer_observe")
        identity = {"url": page.url, "document_generation": boundary.document_generation}
        if not same_document(page, boundary, identity) or len(identity["url"]) > 2000:
            raise DomainError("BROWSER_TARGET_CHANGED", 409)
        screen = await page.screenshot(type="png", full_page=False)
        if not same_document(page, boundary, identity):
            continue  # Discard bytes; never persist/upload the changed document.
        if len(screen) > MAX_SCREEN_BYTES:
            raise ValueError("Screen exceeds the bounded image size")
        content = await page.evaluate("""() => ({
          title: document.title.slice(0,300), text:(document.body?.innerText||'').slice(0,6000),
          controls:Array.from(document.querySelectorAll('button,input,select,a')).slice(0,80).map(el=>{
            const r=el.getBoundingClientRect();return {tag:el.tagName.toLowerCase(),
              label:(el.getAttribute('aria-label')||el.labels?.[0]?.innerText||el.innerText||el.getAttribute('placeholder')||'').slice(0,120),
              x:r.x+r.width/2,y:r.y+r.height/2,visible:r.width>0&&r.height>0&&r.y>=0&&r.bottom<=innerHeight};
          }).filter(x=>x.visible).slice(0,40)
        })""")
        if not same_document(page, boundary, identity):
            continue
        name = f"screen-{sequence}.png"
        write_file(directory, name, screen)
        return {
            **identity,
            **content,
            "sequence": sequence,
            "screen": name,
            "sha256": hashlib.sha256(screen).hexdigest(),
            "width": SCREEN_WIDTH,
            "height": SCREEN_HEIGHT,
            "platform": sys.platform,
            "blocked_reason": boundary.reason,
            "blocked_network_requests": list(boundary.blocked),
            "previous_input_status": boundary.action_note,
        }
    raise DomainError("BROWSER_TARGET_CHANGED", 409)
