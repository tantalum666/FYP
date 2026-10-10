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
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((QA/'versions-before.json').read_text())
files={}
for a in old['images']:
 for key,hkey in [('image','image_sha256'),('prompt','prompt_sha256')]:
  assert sha(ROOT/a[key])==a[hkey],a[key];files[a[key]]=a[hkey]
m=json.loads((ROOT/'design/desk-companion/characters/2026-10-10-expression-study/manifest.json').read_text())
assert sha(Path(m['native_path']))==sha(ROOT/m['path'])==m['sha256']
assert sha(ROOT/m['prompt_path'])==m['prompt_sha256']
assert sha(ROOT/m['input_path'])==m['input_sha256']
assert (m['width'],m['height'])==(1536,1024) and m['attempts']==1 and not m['pixel_edits_after_generation']
current=json.loads((ROOT/'design/desk-companion/characters/2026-10-10-concepts/manifest.json').read_text())
oldmanifest=json.loads((ROOT/'output/qa/2026-10-10-japanese-character-study/manifest-before.json').read_text())
assert current['assets']==oldmanifest['assets']
protected=json.loads((ROOT/'output/qa/task-enhancement-ux-2026-10-03/protected-after.json').read_text())['files']
assert all(sha(ROOT/p)==h for p,h in protected.items())
assert sha(ROOT/'desk-companion/frontend/public/avatars/pixiv-sample.vrm')=='12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
changed=subprocess.check_output(['git','diff','--name-only','44f45733f715a1deca6be2d589f9b9ae3942fa1e'],cwd=ROOT,text=True).splitlines()
assert not [p for p in changed if p.startswith('desk-companion/') and p not in ['desk-companion/README.md','desk-companion/docs/avatar.md']]
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
md=sorted({p for p in changed+untracked if p.endswith('.md')})
bad=[];count=0;outputs={QA/'checks.json',QA/'versions-after.json'}
for name in md:
 p=ROOT/name
 for match in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)',p.read_text()):
  u=match.group(1).strip().strip('<>')
  if re.match(r'^(?:[a-zA-Z][\w+.-]*:|#)',u):continue
  u=unquote(u.split('#')[0].split('?')[0]);target=(p.parent/u).resolve();count+=1
  if u and not target.exists() and target not in outputs:bad.append([name,u])
assert not bad,bad
now=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat()
r=dict(checked_at=now,original_pngs=5,original_prompts=5,original_hashes_unchanged=True,original_manifest_assets_unchanged=True,native_e1_and_workspace_identical=True,expression_width=m['width'],expression_height=m['height'],expression_bytes=m['bytes'],expression_sha256=m['sha256'],native_imagegen_calls=1,pixel_edits=0,protected_files=len(protected),protected_files_unchanged=True,runtime_model_unchanged=True,application_source_unchanged_since='44f45733f715a1deca6be2d589f9b9ae3942fa1e',checked_markdown_files=md,checked_local_links=count,broken_links=bad)
(QA/'checks.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
(QA/'versions-after.json').write_text(json.dumps(dict(checked_at=now,files=files,expression_file=m['path'],expression_sha256=m['sha256']),ensure_ascii=False,indent=2)+'\n')
assert all(p.exists() for p in outputs)
print(json.dumps({k:v for k,v in r.items() if k!='checked_markdown_files'},ensure_ascii=False,indent=2))
