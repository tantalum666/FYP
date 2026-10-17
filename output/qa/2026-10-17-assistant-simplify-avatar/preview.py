"""Loopback-only owner review preview. Providers forced off; no real media agents."""
import os,sys,json,sqlite3,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path('/Users/tantalum/Documents/ChatGPT/FYP/desk-companion/.runtime/user-preview-20261012')
REVIEW=ROOT/'desk-companion/.runtime/a1-review-20261017'
os.umask(0o077)
if not REVIEW.exists():
 REVIEW.mkdir(mode=0o700,parents=True)
 before_db=(SOURCE/'desk.sqlite3').read_bytes()
 before_credentials=(SOURCE/'credentials.json').read_bytes()
 shutil.copy2(SOURCE/'credentials.json',REVIEW/'credentials.json')
 with sqlite3.connect('file:'+str(SOURCE/'desk.sqlite3')+'?mode=ro',uri=True)as source,sqlite3.connect(REVIEW/'desk.sqlite3')as destination:source.backup(destination)
 notes=SOURCE/'computer-notes'
 if notes.is_dir() and not notes.is_symlink():
  (REVIEW/'computer-notes').mkdir(mode=0o700)
  for p in notes.glob('*.txt'):
   if p.is_file()and not p.is_symlink():shutil.copy2(p,REVIEW/'computer-notes'/p.name)
 assert before_db==(SOURCE/'desk.sqlite3').read_bytes()
 assert before_credentials==(SOURCE/'credentials.json').read_bytes()
 (Path(__file__).parent/'preview-preservation.json').write_text(json.dumps({'source_runtime_unchanged':True,'review_uses_independent_database_copy':True,'original_credentials_reused_privately':True,'providers':'none','listen':'localhost:8832','camera_microphone_output_agents_started':False},indent=2)+'\n')
for name in ['DESK_VOICE_PROVIDER','DESK_TEXT_PROVIDER']:os.environ[name]='none'
os.environ['DESK_TEXT_BACKGROUND']='0';os.environ['DESK_COMPUTER_ENABLED']='0';os.environ.pop('DESK_QWEN_CREDENTIAL_FILE',None)
sys.path.insert(0,str(ROOT/'desk-companion/backend'))
import uvicorn
from desk.app import create_app
app=create_app(REVIEW,scheduler=True)
assert app.state.runtime.voice.config.provider=='none'
uvicorn.run(app,host='127.0.0.1',port=8832,log_level='warning',access_log=False)
