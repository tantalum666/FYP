from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import unquote
import hashlib,json,re,subprocess
root=Path.cwd();qa=root/'output/qa/2026-10-10-avatar-wardrobe'
docs=['README.md','product.md','handoff.md','decision-log.md','work-log.md','desk-companion/docs/avatar.md','research/2026-10-10-avatar-art/popular-character-study.md','research/2026-10-10-avatar-art/wardrobe-study.md',str((qa/'verification.md').relative_to(root))]
links=[];missing=[]
for name in docs:
 p=root/name;s=p.read_text();assert s.count('```')%2==0,name
 for dest in re.findall(r'\]\((<[^>]+>|[^\s)]+)\)',s):
  dest=dest.strip('<>')
  if re.match(r'^(?:https?:|mailto:|app:|codex:|#)',dest):continue
  links.append((name,dest))
  if not (p.parent/unquote(dest.split('#')[0])).resolve().exists():missing.append((name,dest))
assert not missing,missing
protected=json.loads((root/'output/qa/task-enhancement-ux-2026-10-03/protected-after.json').read_text())['files']
changed=[]
for name,digest in protected.items():
 p=Path(name)
 if not p.is_absolute():p=root/p
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
assert not changed,changed
baseline='26cdf9f425ad093ed6296a4d32f003874e76595f'
appdiff=subprocess.check_output(['git','diff','--name-only',baseline,'--','desk-companion/backend','desk-companion/frontend','desk-companion/ios'],text=True).splitlines();assert not appdiff,appdiff
modelsha=hashlib.sha256((root/'desk-companion/frontend/public/avatars/pixiv-sample.vrm').read_bytes()).hexdigest();assert modelsha=='12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
sources=json.loads((root/'research/2026-10-10-avatar-art/wardrobe-source-register.json').read_text());assert len(sources['references'])==4 and len(sources['material_sources'])==2
for f in ['wardrobe-reference-board.html','wardrobe-study.md','wardrobe-source-register.json']:assert (root/'research/2026-10-10-avatar-art'/f).is_file()
r={'checked_at':datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),'initial_head':baseline,'local_links_checked':len(links),'missing_links':missing,'protected_files':len(protected),'protected_changes':changed,'application_diff':appdiff,'model_sha256':modelsha,'references':4,'material_guides':2,'original_outfit_briefs':['A1','B1','A2','B2'],'user_retained_directions':['A','B'],'concept_images_generated':False,'final_outfit_selected':False,'browser':{'default_viewport':'1280x720','images_loaded':4,'horizontal_overflow':False,'light_dark_verified':True,'viewport_override_set':False,'narrow_or_reduced_motion_tested':False},'updated_docs':docs,'tests':'No app/source or school document changes; no old suite or DOCX rerender repeated.','delivery':'Existing feature branch / PR4; final remote state read back in session.'}
(qa/'validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False,indent=2))
