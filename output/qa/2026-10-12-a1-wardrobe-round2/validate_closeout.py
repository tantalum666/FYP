from pathlib import Path
import json,hashlib,re,subprocess,datetime
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP');QA=ROOT/'output/qa/2026-10-12-a1-wardrobe-round2';OUT=ROOT/'design/desk-companion/characters/2026-10-12-a1-wardrobe-round2'
updated=json.loads((QA/'updated-norms.json').read_text());record=json.loads((QA/'reading-record.json').read_text());protected=json.loads((QA/'protected-before.json').read_text())
changed=[]
for x in protected:
    if hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']:changed.append(x['path'])
assert not changed,changed
md_changed=[]
for x in record['inventory']:
    if hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']:md_changed.append(x['path'])
assert set(md_changed)==set(updated),(set(md_changed)^set(updated))
newmd=[OUT/'README.md',ROOT/'design/desk-companion/characters/a1-wardrobe-index.md'];files=[ROOT/p for p in updated]+newmd+[QA/'verification.md'];links=[];broken=[]
for p in files:
    text=p.read_text();assert text.endswith('\n'),p
    for m in re.finditer(r'!?\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)',text):
        target=m.group(1).strip();target=target[1:-1] if target.startswith('<') else target
        if target.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
        target=target.split('#',1)[0]
        if not target:continue
        dest=(p.parent/target).resolve();links.append({'from':str(p.relative_to(ROOT)),'target':target})
        if not dest.exists() and dest != QA/'closeout-validation.json':broken.append(links[-1])
assert not broken,broken
manifest=json.loads((OUT/'manifest.json').read_text());assert len(manifest['items'])==6
for x in manifest['items']:
    data=(OUT/x['output']).read_bytes();assert hashlib.sha256(data).hexdigest()==x['sha256'];assert data==Path(x['native_original_path']).read_bytes()
    assert hashlib.sha256((OUT/x['prompt']).read_bytes()).hexdigest()==x['prompt_sha256']
r=json.loads((OUT/'a1-w8-seaside.receipt.json').read_text());assert r['same_prompt_for_both_attempts']
for a in r['attempts']:
    assert Path(a['actual_prompt_path']).read_bytes()==Path(r['prompt_path']).read_bytes()
    if 'sha256' in a:
        data=Path(a['workspace_output_path']).read_bytes();assert hashlib.sha256(data).hexdigest()==a['sha256'];assert data==Path(a['native_original_path']).read_bytes()
brief=(ROOT/'design/desk-companion/characters/a1-character-brief.md').read_text();original=subprocess.check_output(['git','show','HEAD:design/desk-companion/characters/a1-character-brief.md'],cwd=ROOT,text=True)
for key in ['画风','语气','基础表情','反应顺序']:
    old=next(line for line in original.splitlines() if line.startswith('- **'+key+'：**'))
    assert old in brief,key
assert '已明确确定A1为后续形象' in brief
assert '用户已确定A1为后续角色' in (ROOT/'handoff.md').read_text()
code=[x for x in subprocess.check_output(['git','diff','--name-only','--','desk-companion'],cwd=ROOT,text=True).splitlines() if not x.endswith('.md')]
assert not code
assert subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True).returncode==0
for p in OUT.glob('*.json'):json.loads(p.read_text())
for p in (OUT/'prompts').glob('*.txt'):assert not any(line.rstrip()!=line for line in p.read_text().splitlines())
result={'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'task_continuation':True,'inherited_full_read':{'files':139,'lines':12884},'starting_inventory':record['current_inventory_count'],'updated_existing_markdown':updated,'new_markdown':[str(p.relative_to(ROOT)) for p in newmd],'protected_count':len(protected),'protected_changed':changed,'candidate_image_count':6,'native_calls':7,'retry_count':1,'A1_wardrobe_total':9,'character_selection':'A1 user confirmed','outfit_selection':None,'native_bytes_equal':True,'all_six_root_view_image_reviewed':True,'w8_same_prompt_verified':True,'brief_four_rules_preserved':True,'local_links_checked':len(links),'broken_links':broken,'code_changes':code,'git_diff_check':'PASS','browser':{'images_loaded':6,'natural_dimensions':[1024,1536],'viewport_width':1280,'scroll_width':1280,'columns':6,'marked_deliverable':True,'server_session_id':83436},'git_write_performed':False,'runtime_vrm_changed':False,'school_files_changed':False}
(QA/'closeout-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'protected_unchanged':len(protected),'valid_images':6,'native_calls':7,'local_links_checked':len(links),'broken_links':0,'updated_existing_markdown':len(updated),'new_markdown':len(newmd),'A1_wardrobe_total':9,'brief_rules':'PASS','code_changes':0,'git_diff_check':'PASS'},ensure_ascii=False,indent=2))
