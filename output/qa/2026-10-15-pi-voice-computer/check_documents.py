"""Check the same-session Pi research and retain exact-text reading provenance."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
BASE = '83b24763585156e592b319a02a05a9b016d9bbc8'
PRIOR = 'output/qa/2026-10-15-computer-use-comparison/reading-inventory.json'
observed = {x['path']: x['sha256_after'] for x in json.loads((ROOT / PRIOR).read_text())['files']}
paths = sorted(subprocess.check_output([
    'rg', '--files', '--hidden', '-g', '*.md', '-g', '!**/.git/**',
    '-g', '!**/node_modules/**', '-g', '!**/.venv/**', '-g', '!**/__pycache__/**',
    '-g', '!**/dist/**', '-g', '!**/build/**', '-g', '!output/qa/**',
], cwd=ROOT, text=True).splitlines())
files = []
for rel in paths:
    blob = subprocess.check_output(['git', 'show', f'{BASE}:{rel}'], cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest() == observed[rel], rel
    old, new = blob.decode().splitlines(), (ROOT / rel).read_text().splitlines()
    inherited, authored = [], []
    for tag, i, j, a, b in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == 'equal' and b > a:
            inherited.append({'current': [a + 1, b], 'prior': [i + 1, j]})
        elif b > a:
            authored.append([a + 1, b])
    files.append({'path': rel, 'lines': len(new), 'sha256_after': hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), 'inherited_exact_ranges': inherited, 'authored_and_reviewed_ranges': authored})
record = {
    'scope': 'Same-session Pi/Linux, region and single-model follow-up; no independent full-read claim.',
    'base_commit': BASE, 'inherited_read_record': PRIOR,
    'exclusions': ['.git', 'dependencies/caches/third-party packages', 'build outputs', 'output/qa generated snapshots'],
    'focused_reread': ['AGENTS.md', 'product.md', 'handoff.md', 'computer-use comparison EOF', 'latest decision/work-log tails', 'companion architecture latest sections'],
    'files': files, 'completed_at': datetime.now(timezone.utc).isoformat(),
}
(QA / 'reading-inventory.json').write_text(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
(QA / 'document-checks.json').write_text('{}\n')
missing, expected_missing, wrong_groups = [], [], []
count = 0
checked = paths + [str((QA / 'verification.md').relative_to(ROOT))]
for rel in checked:
    p = ROOT / rel
    body = p.read_text()
    if re.search(r'\bGroup\s*(?:[013-9]|2\d)\b', body):
        wrong_groups.append(rel)
    for raw in re.findall(r'\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)', body):
        target = raw.strip().strip('<>')
        if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'):
            continue
        target = unquote(target.split('#', 1)[0].split('?', 1)[0])
        if not target:
            continue
        count += 1
        if not (p.parent / target).exists():
            item = {'file': rel, 'target': target}
            (expected_missing if item == {'file': 'desk-companion/README.md', 'target': '.runtime/credentials.json'} else missing).append(item)
allowed = {
    'product.md', 'handoff.md', 'decision-log.md', 'work-log.md',
    'research/2026-10-15-voice-ai/voice-model-comparison.md',
    'research/2026-10-15-voice-ai/computer-use-comparison.md',
    'docs/tooling-and-review/companion-architecture.md',
}
changed = subprocess.check_output(['git', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
assert all(x in allowed or x.startswith('output/qa/2026-10-15-pi-voice-computer/') for x in changed), changed
assert (ROOT / 'planning/2026-09-14/group-2-details.json').is_file()
subprocess.run(['git', 'diff', '--check', BASE], cwd=ROOT, check=True)
result = {'project_markdown_versions': len(files), 'markdown_documents_checked': len(checked), 'local_references': count, 'resolved': count - len(missing) - len(expected_missing), 'broken_links': missing, 'expected_generated_targets': expected_missing, 'wrong_group_names': wrong_groups, 'identity_source_exists': True, 'protected_path_scope': 'passed', 'whitespace': 'passed'}
(QA / 'document-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
assert not missing and not wrong_groups
