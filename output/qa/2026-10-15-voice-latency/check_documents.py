"""Check local Markdown targets; no network or runtime credential access."""
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
paths = subprocess.check_output(['rg', '--files', '--hidden', '-g', '*.md', '-g', '!**/.git/**', '-g', '!**/node_modules/**', '-g', '!**/.venv/**', '-g', '!**/__pycache__/**', '-g', '!**/dist/**', '-g', '!**/build/**', '-g', '!output/qa/**'], cwd=ROOT, text=True).splitlines()
paths.extend([str((QA/'verification.md').relative_to(ROOT)), 'output/qa/2026-10-15-voice-model-refresh/verification.md'])
expected = [{'file': 'desk-companion/README.md', 'target': '.runtime/credentials.json'}]
count = 0
missing = []
generated = []
for rel in paths:
    p = ROOT/rel
    for raw in re.findall(r'\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)', p.read_text()):
        target = raw.strip().strip('<>')
        if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'):
            continue
        target = unquote(target.split('#', 1)[0].split('?', 1)[0])
        if not target:
            continue
        count += 1
        if not (p.parent/target).exists():
            item = {'file': rel, 'target': target}
            (generated if item in expected else missing).append(item)
result = {'markdown_files': len(paths), 'local_links_checked': count, 'resolved_links': count-len(generated)-len(missing), 'broken_links': missing, 'generated_local_targets_not_expected_in_isolated_worktree': generated}
(QA/'document-checks.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
assert not missing, missing
