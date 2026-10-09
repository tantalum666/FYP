from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,re,struct,subprocess
from urllib.parse import unquote
root=Path.cwd();qa=root/'output/qa/2026-10-10-character-concepts';out=root/'design/desk-companion/characters/2026-10-10-concepts'
docs=['README.md','product.md','handoff.md','decision-log.md','work-log.md','desk-companion/docs/avatar.md','research/2026-10-10-avatar-art/popular-character-study.md','research/2026-10-10-avatar-art/wardrobe-study.md','research/2026-10-10-avatar-art/character-concepts.md',str((out/'README.md').relative_to(root)),str((qa/'verification.md').relative_to(root))]
links=[];missing=[]
for name in docs:
 p=root/name;s=p.read_text();assert s.count('```')%2==0,name
 for dest in re.findall(r'\]\((<[^>]+>|[^\s)]+)\)',s):
  dest=dest.strip('<>')
  if re.match(r'^(?:https?:|mailto:|app:|codex:|#)',dest):continue
  links.append((name,dest))
  if not (p.parent/unquote(dest.split('#')[0])).resolve().exists():missing.append((name,dest))
assert not missing,missing
m=json.loads((out/'manifest.json').read_text());assert len(m['assets'])==2
for a in m['assets']:
 data=(root/a['path']).read_bytes();assert len(data)==a['bytes'] and hashlib.sha256(data).hexdigest()==a['sha256'];assert data==Path(a['native_path']).read_bytes()
 assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(1024,1536)
 prompt=out/(a['id'].lower()+'-prompt.txt');assert prompt.exists() and len(prompt.read_text())>1500;a['prompt_path']=str(prompt.relative_to(root))
(out/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
protected=json.loads((root/'output/qa/task-enhancement-ux-2026-10-03/protected-after.json').read_text())['files'];changed=[]
for name,digest in protected.items():
 p=Path(name)
 if not p.is_absolute():p=root/p
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
assert not changed,changed
baseline='e219fbecc60e5a12e51e71e8205fe5d129f8826e'
appdiff=subprocess.check_output(['git','diff','--name-only',baseline,'--','desk-companion/backend','desk-companion/frontend','desk-companion/ios'],text=True).splitlines();assert not appdiff,appdiff
modelsha=hashlib.sha256((root/'desk-companion/frontend/public/avatars/pixiv-sample.vrm').read_bytes()).hexdigest();assert modelsha=='12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
r={'checked_at':datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),'initial_head':baseline,'links_checked':len(links),'missing_links':missing,'native_calls':2,'retries':0,'image_dimensions':[1024,1536],'native_and_project_bytes_equal':True,'prompts_preserved':True,'actual_visual_review':'Semi-realistic stylized 3D; full bodies and clothing visible; framing/heels/shorts/accent deviations documented.','user_selection':None,'protected_files':len(protected),'protected_changes':changed,'app_source_diff':appdiff,'runtime_model_sha256':modelsha,'tests':'No app source or school-document changes; no repeated software suite / document render.','rich_board_mounted':False,'direct_native_image_delivery':True,'updated_docs':docs}
(qa/'validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False,indent=2))
