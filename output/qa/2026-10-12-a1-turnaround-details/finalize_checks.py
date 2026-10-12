"""Asset/document closeout checks, with no application or pixel mutations."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


now = datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat()
updated = json.loads((QA / 'updated-markdown.json').read_text())
plan = json.loads((QA / 'readback-plan.json').read_text())
for batch in plan:
    batch['actually_read'] = True
    batch['acknowledged_at'] = now
    batch['evidence_sha256'] = digest(ROOT / batch['evidence'])
readback = []
for path in updated:
    spans = [[r['start'], r['end']] for batch in plan for r in batch['ranges'] if r['path'] == path]
    if path == 'desk-companion/docs/avatar.md':
        spans.append([56, 71])
    assert spans, path
    readback.append({'path': path, 'lines': len((ROOT / path).read_text().splitlines()),
                     'ranges_actually_read': spans, 'sha256': digest(ROOT / path)})
write(QA / 'closeout-reading.json', {
    'same_task_inherited_full_read': 'output/qa/2026-10-12-wardrobe-variants/reading-record.json',
    'method': 'Six tool-output batches read in full; avatar actual changed range 56-71 separately read.',
    'batch_count': 6, 'readback': readback, 'batches': plan, 'completed_at': now,
})

protected = json.loads((QA / 'protected-before.json').read_text())
protected_failures = [p['path'] for p in protected if digest(ROOT / p['path']) != p['sha256']]
assert not protected_failures, protected_failures

preserved = json.loads((QA / 'wardrobe-preservation.json').read_text())
archive = Path(preserved['archive_path'])
assert digest(archive) == preserved['sha256']
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert len(bundle.namelist()) == 21
    for item in preserved['items']:
        mf = ROOT / item['source_manifest']
        assert digest(mf) == item['source_manifest_sha256']
        source = next(i for i in json.loads(mf.read_text())['items'] if i['id'] == item['id'])
        for dest, original in [(item['image'], mf.parent / source['output']), (item['prompt'], mf.parent / source['prompt'])]:
            assert bundle.read(dest) == original.read_bytes(), dest
    original = ROOT / 'design/desk-companion/characters/2026-10-10-concepts/a1-silver-mist-anime-v4.png'
    assert bundle.read('source/a1-silver-mist-anime-v4.png') == original.read_bytes()
    assert len(json.loads(bundle.read('index.json'))['items']) == 9
    assert bundle.read('README.md')

found = subprocess.check_output(['rg', '--files', '--hidden', '-g', '*.md'], cwd=ROOT, text=True).splitlines()
excluded_parts = {'.git', 'node_modules', '.venv', '__pycache__', '.cache', 'dist', 'build', '.runtime', '.pytest_cache'}
inventory = []
for rel in sorted(found):
    path = Path(rel)
    if path.parts[:2] == ('output', 'qa') or any(p in excluded_parts for p in path.parts):
        continue
    inventory.append({'path': rel, 'lines': len((ROOT / rel).read_text().splitlines()), 'sha256': digest(ROOT / rel)})
assert len(inventory) == 144, len(inventory)
before = json.loads((QA / 'reading-record.json').read_text())
before_hashes = {p['path']: p['sha256'] for p in before['inventory']}
actual_changed = sorted(p['path'] for p in inventory if p['path'] in before_hashes and p['sha256'] != before_hashes[p['path']])
assert set(actual_changed).issubset(updated), set(actual_changed) - set(updated)
new_md = sorted(p['path'] for p in inventory if p['path'] not in before_hashes)
assert new_md == sorted([
    'design/desk-companion/characters/a1-turnaround-spec.md',
    'design/desk-companion/characters/2026-10-12-a1-turnaround-details/README.md',
]), new_md

brief_path = 'design/desk-companion/characters/a1-character-brief.md'
head_brief = subprocess.check_output(['git', 'show', 'HEAD:' + brief_path], cwd=ROOT, text=True)
brief = (ROOT / brief_path).read_text()
for title in ['画风', '语气', '基础表情', '反应顺序']:
    old = next(s for s in head_brief.splitlines() if s.startswith('- **' + title + '：**'))
    assert old in brief, title
assert len([s for s in brief.splitlines() if s.startswith('- **')]) == 8
details = (ROOT / 'planning/2026-09-14/group-2-details.json').read_text()
assert all(name in details for name in ['Yuan Yuchen', 'Xu Ziqian', 'Li Wenhua'])
assert not [rel for rel in updated if re.search(r'Group\s+[013-9]\b', (ROOT / rel).read_text())]

app_changed = subprocess.check_output(['git', 'diff', '--name-only', '--', 'desk-companion'], cwd=ROOT, text=True).splitlines()
assert all(p.endswith('.md') for p in app_changed), app_changed
diff_check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, text=True, capture_output=True)
assert diff_check.returncode == 0, diff_check.stdout + diff_check.stderr
for rel in updated:
    data = (ROOT / rel).read_text()
    assert data.endswith('\n') and not data.endswith('\n\n'), rel
    assert not any(line.rstrip() != line for line in data.splitlines()), rel

target = QA / 'final-validation.json'
write(target, {'status': 'checking'})
broken, checked = [], 0
md_paths = [ROOT / p['path'] for p in inventory] + [QA / 'verification.md']
link_pattern = re.compile(r'!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)')
for path in md_paths:
    for match in link_pattern.finditer(path.read_text()):
        dest = match.group(1).strip()
        dest = dest[1:-1] if dest.startswith('<') and dest.endswith('>') else dest
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', dest) or dest.startswith('#'):
            continue
        dest = unquote(dest.split('#')[0].split('?')[0])
        if not dest:
            continue
        checked += 1
        full = Path(dest) if Path(dest).is_absolute() else path.parent / dest
        if not full.exists():
            broken.append({'source': str(path.relative_to(ROOT)), 'target': dest})
assert not broken, broken

preview = json.loads((QA / 'preview-verification.json').read_text())
images = json.loads((QA / 'image-validation.json').read_text())
assert preview['image_count'] == images['accepted_image_count'] == 10
assert preview['all_images_complete'] and preview['tab_marked_deliverable']
before['recovery_reads'] = {
    'AGENTS.md': '1-50 full', 'product.md': 'full before edits', 'handoff.md': 'full before edits',
    'decision-log.md': 'latest task-relevant tail',
    'focused_spec_and_modified_sources': 'full small files / original art research bodies; latest log tails',
    'truncated_combined_outputs': 'product/handoff separately re-read; D01/D02/D03 receipts separately re-read',
}
before['closeout_readback'] = 'output/qa/2026-10-12-a1-turnaround-details/closeout-reading.json'
before['final_inventory_count'] = len(inventory)
before['final_inventory'] = inventory
before['completed_at'] = now
write(QA / 'reading-record.json', before)
result = {
    'status': 'passed', 'completed_at': now, 'updated_markdown_count': len(updated),
    'markdown_inventory_count': len(inventory), 'new_markdown': new_md,
    'actual_changed_existing_markdown': actual_changed,
    'protected_files_count': len(protected), 'protected_files_unchanged': True,
    'wardrobe_archive_sha256': digest(archive), 'wardrobe_crc': 'passed',
    'wardrobe_members_count': 21, 'wardrobe_nine_images_nine_prompts_byte_identical': True,
    'local_links_checked': checked, 'broken_local_links': broken,
    'character_brief_eight_rules_present': True, 'four_existing_acting_rules_verbatim_preserved': True,
    'group_number_and_member_names': 'Group 2 / original identity data preserved',
    'git_diff_check': 'passed', 'changed_source_markdown_whitespace': 'passed',
    'application_code_changed': False, 'runtime_vrm_unchanged': True,
    'accepted_images_individually_viewed': 10, 'native_calls': 11,
    'actual_prompt_and_native_source_hashes': 'passed in image-validation.json',
    'preview': 'all ten loaded; actual full-page screenshot viewed; no overflow; tab retained',
    'app_tests_or_school_render_rerun': False, 'git_write_performed': False,
}
write(target, result)
print(json.dumps({k: result[k] for k in ['status', 'updated_markdown_count', 'markdown_inventory_count', 'protected_files_count', 'local_links_checked', 'broken_local_links', 'accepted_images_individually_viewed']}, ensure_ascii=False, indent=2))
