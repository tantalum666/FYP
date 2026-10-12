"""Validate source-backed inventory and preserve preceding user deliverables."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
UPDATED = [
    'README.md', 'product.md', 'handoff.md', 'decision-log.md', 'work-log.md',
    'desk-companion/README.md', 'desk-companion/docs/architecture.md',
    'planning/2026-10-12/software-function-inventory.md',
]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


now = datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat()
prior = json.loads((QA / 'preservation-before-save.json').read_text())
unchanged = []
for item in prior['files']:
    if item['path'] in UPDATED:
        continue
    assert digest(ROOT / item['path']) == item['sha256'], item['path']
    unchanged.append(item['path'])
protected = json.loads((ROOT / 'output/qa/2026-10-12-a1-turnaround-details/protected-before.json').read_text())
for item in protected:
    assert digest(ROOT / item['path']) == item['sha256'], item['path']

app_diff = subprocess.check_output(['git', 'diff', '--name-only', 'e45afd2', '--', 'desk-companion'], cwd=ROOT, text=True).splitlines()
assert set(app_diff).issubset({'desk-companion/README.md', 'desk-companion/docs/architecture.md'}), app_diff
assert not list((ROOT / '.github/workflows').glob('*'))
document = (ROOT / UPDATED[-1]).read_text()
module_numbers = [int(n) for n in re.findall(r'^\| (\d+)\.', document, re.M)]
assert module_numbers == list(range(1, 18)), module_numbers
assert all(token in document for token in ['149', '15', '22', '26', '长期个人记忆', '作业归档', '真实验证', '默认关闭'])
details = (ROOT / 'planning/2026-09-14/group-2-details.json').read_text()
assert all(name in details for name in ['Yuan Yuchen', 'Xu Ziqian', 'Li Wenhua'])
for rel in UPDATED + [str((QA / 'verification.md').relative_to(ROOT))]:
    body = (ROOT / rel).read_text()
    assert body.endswith('\n') and not body.endswith('\n\n'), rel
    assert not any(line.rstrip() != line for line in body.splitlines()), rel
    assert not re.search(r'Group\s+[013-9]\b', body), rel

found = subprocess.check_output(['rg', '--files', '--hidden', '-g', '*.md'], cwd=ROOT, text=True).splitlines()
exclude = {'.git', '.venv', 'node_modules', '.runtime', 'dist', 'build', '__pycache__', '.cache'}
inventory = []
for rel in sorted(found):
    parts = Path(rel).parts
    if parts[:2] == ('output', 'qa') or any(part in exclude for part in parts):
        continue
    inventory.append({'path': rel, 'lines': len((ROOT / rel).read_text().splitlines()), 'sha256': digest(ROOT / rel)})
assert len(inventory) == 145, len(inventory)
before = json.loads((QA / 'reading-record.json').read_text())
old_hashes = {i['path']: i['sha256'] for i in before['current_inventory']}
unexpected = [i['path'] for i in inventory if i['path'] in old_hashes and i['sha256'] != old_hashes[i['path']] and i['path'] not in UPDATED]
assert not unexpected, unexpected

write(QA / 'inventory-git-delivery.json', {'status': 'pending final inventory push', 'preservation_commit': 'e45afd2700e87f07c7e8044a7f67ce3b09237cae'})
write(QA / 'final-validation.json', {'status': 'checking'})
broken, checked = [], 0
links = re.compile(r'!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)')
for path in [ROOT / i['path'] for i in inventory] + [QA / 'verification.md']:
    for match in links.finditer(path.read_text()):
        dest = match.group(1).strip()
        if dest.startswith('<') and dest.endswith('>'):
            dest = dest[1:-1]
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', dest) or dest.startswith('#'):
            continue
        dest = unquote(dest.split('#')[0].split('?')[0])
        if not dest:
            continue
        checked += 1
        target = Path(dest) if Path(dest).is_absolute() else path.parent / dest
        if not target.exists():
            broken.append({'source': str(path.relative_to(ROOT)), 'target': dest})
assert not broken, broken
diff = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, text=True, capture_output=True)
assert diff.returncode == 0, diff.stdout + diff.stderr

source_paths = sorted(set(re.findall(r'\]\(([^)]+)\)', document)))
source_files = []
for rel in source_paths:
    p = (ROOT / UPDATED[-1]).parent / rel
    if p.is_file() and p.suffix in {'.py', '.tsx'}:
        source_files.append({'path': str(p.resolve().relative_to(ROOT)), 'sha256': digest(p)})
write(QA / 'source-crosscheck.json', {
    'method': 'Read current route/declaration lists, actual LocalNotesExecutor and TextConfig, frontend entry references, plus focused project contracts and dated validation.',
    'source_files_referenced': source_files,
    'workflow_files': [], 'application_changes': app_diff,
    'historical_validation': {'2026-10-09-integration': {'backend': 149, 'frontend': 15}, '2026-10-09-avatar': {'targeted_backend': 26, 'frontend': 22}},
    'tests_rerun_this_inventory': False,
})
readback = {
    'README.md': [[13, 23]], 'product.md': [[1, 4], [61, 79]],
    'handoff.md': [[1, 20]], 'desk-companion/README.md': [[9, 19]],
    'desk-companion/docs/architecture.md': [[1, 8]],
    'decision-log.md': [[784, 792]], 'work-log.md': [[957, 967]],
    UPDATED[-1]: [[1, len(document.splitlines())]],
}
write(QA / 'closeout-reading.json', {
    'inherited_reading': str((QA / 'reading-record.json').relative_to(ROOT)),
    'actual_readback': [{'path': rel, 'ranges': spans, 'sha256': digest(ROOT / rel)} for rel, spans in readback.items()],
    'completed_at': now,
})
before['final_inventory'] = inventory
before['final_inventory_count'] = len(inventory)
before['closeout_reading'] = str((QA / 'closeout-reading.json').relative_to(ROOT))
before['completed_at'] = now
write(QA / 'reading-record.json', before)
result = {
    'status': 'passed_local', 'completed_at': now,
    'software_modules': 17, 'updated_project_markdown': UPDATED,
    'project_markdown_inventory_count': 145, 'local_links_checked': checked,
    'broken_local_links': broken, 'old_71_protected_files_unchanged': True,
    'earlier_saved_files_outside_current_markdown_updates_unchanged': len(unchanged),
    'all_art_and_school_bytes_unchanged': True, 'application_code_changed': False,
    'group_identity_verified': True, 'new_source_whitespace': 'passed',
    'git_diff_check': 'passed for current tracked documentation updates',
    'original_staged_prompt_evidence_whitespace_exceptions': 'preservation-whitespace-check.json',
    'app_tests_rerun': False, 'new_paid_or_physical_tests': False,
    'delivery_record': 'inventory-git-delivery.json',
}
write(QA / 'final-validation.json', result)
print(json.dumps({k: result[k] for k in ['status', 'software_modules', 'project_markdown_inventory_count', 'local_links_checked', 'broken_local_links', 'application_code_changed']}, ensure_ascii=False, indent=2))
