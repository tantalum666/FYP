"""Artifact preservation and local-reference verification for this research phase."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[3]
QA=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
frozen=json.loads((QA/'versions-preserved-before.json').read_text())
checked=[]
for row in frozen['images']:
 for key,hkey in [('image','image_sha256'),('prompt','prompt_sha256')]:
  p=ROOT/row[key];assert sha(p)==row[hkey],row[key];checked.append(row[key])
old=json.loads((QA/'manifest-before.json').read_text())
new=json.loads((ROOT/'design/desk-companion/characters/2026-10-10-concepts/manifest.json').read_text())
assert new['assets']==old['assets'],'Asset provenance entries changed'
protected=json.loads((ROOT/'output/qa/task-enhancement-ux-2026-10-03/protected-after.json').read_text())['files']
assert all(sha(ROOT/p)==h for p,h in protected.items()),'Protected file changed'
model=ROOT/'desk-companion/frontend/public/avatars/pixiv-sample.vrm'
assert sha(model)=='12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
changed=subprocess.check_output(['git','diff','--name-only','352199fd1cc5a3a8f40ccb4ad8ab61a44785ac8c'],cwd=ROOT,text=True).splitlines()
assert not [p for p in changed if p.startswith('desk-companion/') and p not in ['desk-companion/README.md','desk-companion/docs/avatar.md']], 'Application source changed'
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
md=sorted({p for p in changed+untracked if p.endswith('.md')})
bad=[];links=0
for name in md:
 p=ROOT/name
 for m in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)',p.read_text()):
  u=m.group(1).strip().strip('<>')
  if re.match(r'^(?:[a-zA-Z][\w+.-]*:|#)',u):continue
  u=unquote(u.split('#')[0].split('?')[0])
  if not u:continue
  links+=1
  if not (p.parent/u).exists():bad.append([name,u])
generated_targets={QA/'checks.json',QA/'versions-preserved-after.json'}
bad=[(name,u) for name,u in bad if ((ROOT/name).parent/u).resolve() not in generated_targets]
assert not bad,bad
source=json.loads((ROOT/'research/2026-10-10-avatar-art/japanese-character-sources.json').read_text())
assert len(source['sources'])==13 and len(source['visuals'])==6 and len(source['extra_visuals'])==2
assert len({v['id'] for v in source['sources']})==13
result=dict(completed_at=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),preserved_pngs=5,preserved_prompts=5,raw_asset_hashes_identical=True,manifest_asset_entries_identical=True,protected_files=len(protected),protected_files_unchanged=True,application_source_unchanged_since='352199fd1cc5a3a8f40ccb4ad8ab61a44785ac8c',runtime_model_unchanged=True,checked_markdown_files=md,checked_local_links=links,broken_local_links=bad,sources=13,official_character_visuals=6,additional_visuals=2,new_imagegen_calls=0)
(QA/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(QA/'versions-preserved-after.json').write_text(json.dumps(dict(completed_at=result['completed_at'],files={p:sha(ROOT/p) for p in checked}),ensure_ascii=False,indent=2)+'\n')
assert all(p.exists() for p in generated_targets)
print(json.dumps({k:v for k,v in result.items() if k!='checked_markdown_files'},ensure_ascii=False,indent=2))
