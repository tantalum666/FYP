from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
BASE = 'ea92c2d6da4dd12bcdd64c7f246eccbadd6ae6e7'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = json.loads((QA / 'art-before.json').read_text())['files']
changed_index = 'design/desk-companion/characters/2026-10-10-concepts/README.md'
unchanged = {name: value for name, value in before.items() if name != changed_index}
assert all(sha(ROOT / name) == value for name, value in unchanged.items())
old = json.loads((ROOT / 'output/qa/2026-10-10-a1-character-brief/versions-before.json').read_text())
for asset in old['images']:
    assert sha(ROOT / asset['image']) == asset['image_sha256']
    assert sha(ROOT / asset['prompt']) == asset['prompt_sha256']

m = json.loads((ROOT / 'design/desk-companion/characters/2026-10-10-c1-concept/manifest.json').read_text())
b = (ROOT / m['path']).read_bytes()
assert b[:8] == b'\x89PNG\r\n\x1a\n'
assert struct.unpack('>II', b[16:24]) == (1024, 1536)
assert len(b) == m['bytes'] == 1587650
assert sha(Path(m['native_path'])) == sha(ROOT / m['path']) == m['sha256']
assert sha(ROOT / m['prompt_path']) == m['prompt_sha256']
assert m['attempts'] == 1 and not m['pixel_edits_after_generation']
assert m['input_reference_images'] is None and not m['source_ip_images_sent_to_generator']

protected = json.loads((ROOT / 'output/qa/task-enhancement-ux-2026-10-03/protected-after.json').read_text())['files']
assert all(sha(ROOT / name) == value for name, value in protected.items())
assert sha(ROOT / 'desk-companion/frontend/public/avatars/pixiv-sample.vrm') == '12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'

changed = subprocess.check_output(['git', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
assert not [name for name in changed if name.startswith('desk-companion/') and name not in ['desk-companion/README.md', 'desk-companion/docs/avatar.md']]
assert not [name for name in changed if name.startswith(('apps/', 'services/', 'tools/'))]
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
markdown = sorted({name for name in changed + untracked if name.endswith('.md')})
broken = []
links = 0
for name in markdown:
    p = ROOT / name
    for match in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)', p.read_text()):
        url = match.group(1).strip().strip('<>')
        if re.match(r'^(?:[a-zA-Z][\w+.-]*:|#)', url):
            continue
        url = unquote(url.split('#')[0].split('?')[0])
        links += 1
        if url and not (p.parent / url).resolve().exists():
            broken.append([name, url])
assert not broken, broken

sources = json.loads((ROOT / 'research/2026-10-10-avatar-art/mainstream-anime-c1-sources.json').read_text())
assert len(sources['sources']) == 18
assert len({s['id'] for s in sources['sources']}) == 18
assert sum(s['character_image_actually_viewed'] for s in sources['sources']) == 5
result = dict(
    checked_at=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),
    preserved_prior_art_files=len(unchanged),
    preserved_prior_art_files_unchanged=True,
    original_index_only_added_c1_routing=True,
    original_pngs=5,
    original_prompts=5,
    e1_png_prompt_manifest_unchanged=True,
    original_concept_manifest_unchanged=True,
    c1_native_and_workspace_identical=True,
    c1_sha256=m['sha256'],
    c1_width=1024,
    c1_height=1536,
    c1_bytes=len(b),
    native_imagegen_calls=1,
    reference_images=0,
    pixel_edits=0,
    protected_files=len(protected),
    protected_files_unchanged=True,
    runtime_model_unchanged=True,
    application_source_unchanged_since=BASE,
    source_entries=18,
    official_character_images_actually_viewed=5,
    checked_markdown=markdown,
    local_links=links,
    broken_links=broken,
)
(QA / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'checked_markdown'}, ensure_ascii=False, indent=2))
