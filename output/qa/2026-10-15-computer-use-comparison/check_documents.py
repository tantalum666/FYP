"""Validate local documentation without network, models or private runtime reads."""
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
BASE = 'd062755f43d110f03a876173bdc802ea87ed1a32'
PRIOR = 'output/qa/2026-10-15-voice-latency/reading-inventory.json'
EXCLUDE = ['.git', 'dependencies and caches', 'third-party packages', 'build outputs', 'output/qa generated evidence']
paths = sorted(subprocess.check_output([
    'rg', '--files', '--hidden', '-g', '*.md', '-g', '!**/.git/**',
    '-g', '!**/node_modules/**', '-g', '!**/.venv/**', '-g', '!**/__pycache__/**',
    '-g', '!**/dist/**', '-g', '!**/build/**', '-g', '!output/qa/**',
], cwd=ROOT, text=True).splitlines())
prior = json.loads((ROOT / PRIOR).read_text())
observed = {x['path']: x['sha256_before'] for x in prior['files']}
observed.update({x['path']: x['sha256_after'] for x in prior['reviewed_changes']})
records = []
for rel in paths:
    current = (ROOT / rel).read_text()
    result = subprocess.run(['git', 'show', f'{BASE}:{rel}'], cwd=ROOT, capture_output=True)
    if result.returncode:
        assert rel == 'research/2026-10-15-voice-ai/computer-use-comparison.md', rel
        old = ''
    else:
        assert hashlib.sha256(result.stdout).hexdigest() == observed[rel], rel
        old = result.stdout.decode()
    old_lines, new_lines = old.splitlines(), current.splitlines()
    inherited, authored = [], []
    for tag, i, j, a, b in SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
        if tag == 'equal' and b > a:
            inherited.append({'current': [a + 1, b], 'prior': [i + 1, j]})
        elif b > a:
            authored.append([a + 1, b])
    records.append({
        'path': rel, 'lines': len(new_lines),
        'sha256_after': hashlib.sha256(current.encode()).hexdigest(),
        'prior_version_observed': bool(old),
        'inherited_exact_ranges': inherited,
        'authored_and_reviewed_ranges': authored,
    })
inventory = {
    'scope': 'Same-session computer-use follow-up; inherited observed text plus authored/reviewed changes, not a fresh full read.',
    'base_commit': BASE, 'inherited_read_record': PRIOR, 'exclusions': EXCLUDE,
    'focused_reread': [
        'AGENTS.md', 'product.md', 'handoff.md', 'decision-log.md latest85 lines',
        'planning/2026-10-06/personal-agent-discussion-and-next-steps.md',
        'desk-companion/docs/computer-jobs.md',
        'docs/tooling-and-review/companion-architecture.md',
        'research/2026-10-15-voice-ai/voice-model-comparison.md',
        'work-log.md current52-line tail',
    ],
    'files': records, 'completed_at': datetime.now(timezone.utc).isoformat(),
}
(QA / 'reading-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
checked = paths + [str((QA / 'verification.md').relative_to(ROOT))]
(QA / 'document-checks.json').write_text('{}\n')
expected = {'file': 'desk-companion/README.md', 'target': '.runtime/credentials.json'}
missing, generated, bad_groups = [], [], []
count = 0
for rel in checked:
    p = ROOT / rel
    body = p.read_text()
    if re.search(r'\bGroup\s*(?:[013-9]|2\d)\b', body):
        bad_groups.append(rel)
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
            (generated if item == expected else missing).append(item)
assert (ROOT / 'planning/2026-09-14/group-2-details.json').is_file()
changed = subprocess.check_output(['git', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
assert all(x.endswith('.md') or x.startswith('output/qa/') for x in changed), changed
subprocess.run(['git', 'diff', '--check', BASE], cwd=ROOT, check=True)
results = {
    'project_markdown_versions': len(records), 'markdown_files_checked': len(checked),
    'local_links_checked': count, 'resolved_links': count - len(missing) - len(generated),
    'broken_links': missing, 'expected_generated_links': generated,
    'wrong_group_names': bad_groups, 'identity_source_exists': True,
    'application_source_changed': False, 'whitespace_check': 'passed',
}
(QA / 'document-checks.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results))
assert not missing, missing
assert not bad_groups, bad_groups
