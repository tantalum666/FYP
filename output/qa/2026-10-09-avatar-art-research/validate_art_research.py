from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import unquote,urlsplit
import hashlib,json,re,subprocess
import httpx
root=Path.cwd();qa=root/'output/qa/2026-10-09-avatar-art-research'
docs=['README.md','product.md','handoff.md','decision-log.md','work-log.md','desk-companion/docs/avatar.md','research/2026-10-10-avatar-art/popular-character-study.md']
links=[];missing=[]
for name in docs:
 p=root/name;text=p.read_text()
 assert text.count('```')%2==0,name
 for dest in re.findall(r'\]\((<[^>]+>|[^\s)]+)\)',text):
  dest=dest.strip('<>')
  if re.match(r'^(?:https?:|mailto:|app:|codex:|#)',dest):continue
  target=(p.parent/unquote(dest.split('#')[0])).resolve()
  links.append({'from':name,'to':dest})
  if not target.exists():missing.append({'from':name,'to':dest})
assert not missing,missing
before=json.loads((root/'output/qa/task-enhancement-ux-2026-10-03/protected-after.json').read_text())['files']
changed=[]
for name,digest in before.items():
 p=Path(name)
 if not p.is_absolute():p=root/p
 if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
assert not changed,changed
source_paths=['desk-companion/backend','desk-companion/frontend','desk-companion/ios']
source_diff=subprocess.check_output(['git','diff','--name-only','6ac85d53d824bebcc742071b5dddcb05bb331d6a','--',*source_paths],text=True).splitlines()
assert not source_diff,source_diff
model=root/'desk-companion/frontend/public/avatars/pixiv-sample.vrm'
modelsha=hashlib.sha256(model.read_bytes()).hexdigest();assert modelsha=='12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2'
r=json.loads((qa/'reading-record.json').read_text());assert r['complete'] and r['totals']=={'files':128,'lines':12096,'chunks':48}
register=json.loads((root/'research/2026-10-10-avatar-art/source-register.json').read_text());assert len(register['references'])==8 and len(register['additional_sources'])==5
for frame in register['local_frames']:assert hashlib.sha256((root/frame['path']).read_bytes()).hexdigest()==frame['sha256']
with httpx.Client(trust_env=False,timeout=5) as client:
 inside=client.get('http://127.0.0.1:5192/research/2026-10-10-avatar-art/reference-board.html')
 outside=client.get('http://127.0.0.1:5192/AGENTS.md')
 assert inside.status_code==200 and outside.status_code==404
result={'checked_at':datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),'reading':r['totals'],'reading_complete':True,'local_markdown_links_checked':len(links),'missing_links':missing,'protected_files':len(before),'protected_changes':changed,'app_source_diff':source_diff,'model_sha256':modelsha,'references':8,'additional_sources':5,'frame_hashes_verified':len(register['local_frames']),'preview_server':{'pid':79229,'bind':'127.0.0.1:5192','research_status':inside.status_code,'outside_scope_status':outside.status_code},'browser':{'viewport':'1280x720 default, full-page screenshot','images_loaded':8,'horizontal_overflow':False,'light_and_dark_visually_checked':True,'narrow_viewport_tested':False},'updated_specs':docs,'application_tests':'Not rerun: no application changes. Prior test results are referenced with their dates.','school_documents':'No edits; no re-render needed.','git_status':'See git_delivery for the recorded research readback.'}
existing=qa/'validation.json'
if existing.exists():
 old=json.loads(existing.read_text())
 for key in ('git_delivery','staged_gitleaks_findings','gitleaks_command'):
  if key in old:result[key]=old[key]
(qa/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
