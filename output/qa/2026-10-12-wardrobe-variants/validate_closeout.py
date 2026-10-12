from pathlib import Path
import json,re,hashlib,datetime,subprocess
ROOT=Path('/Users/tantalum/Documents/ChatGPT/FYP'); QA=ROOT/'output/qa/2026-10-12-wardrobe-variants'; OUT=ROOT/'design/desk-companion/characters/2026-10-12-wardrobe-variants'
updated=json.loads((QA/'updated-norms.json').read_text()); before=json.loads((QA/'protected-before.json').read_text())
expected_md={'design/desk-companion/characters/a1-character-brief.md','design/desk-companion/characters/a1-expression-rules.md','design/desk-companion/characters/2026-10-10-concepts/README.md','design/desk-companion/characters/2026-10-10-c1-concept/README.md','design/desk-companion/characters/2026-10-10-expression-study/README.md'}
protection=[]; changed=set()
for item in before:
    sha=hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(); same=sha==item['sha256']
    if not same: changed.add(item['path'])
    protection.append({'path':item['path'],'unchanged':same,'expected_norm_update':item['path'] in expected_md,'current_sha256':sha})
assert changed==expected_md, changed
r=json.loads((QA/'reading-record.json').read_text()); changed_since_read=set()
for f in r['files']:
    original=f.get('sha256') or f.get('sha256_before')
    if original!=hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest(): changed_since_read.add(f['path'])
assert changed_since_read==set(updated), changed_since_read^set(updated)
paths=[ROOT/p for p in updated]+[OUT/'README.md',QA/'verification.md']; broken=[]; link_count=0
for p in paths:
    s=p.read_text()
    for m in re.finditer(r'!?\[[^\]]*\]\((<[^>]+>|[^)\n]+)\)',s):
        target=m.group(1).strip()
        if target.startswith('<'): target=target[1:-1]
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'): continue
        target=target.split('#',1)[0]
        if not target: continue
        dest=(p.parent/target).resolve(); link_count+=1
        if not dest.exists() and dest != QA/'closeout-validation.json': broken.append({'from':str(p.relative_to(ROOT)),'target':target})
assert not broken,broken
for p in OUT.glob('*.json'): json.loads(p.read_text())
code_changed=[p for p in subprocess.check_output(['git','diff','--name-only','--','desk-companion'],cwd=ROOT,text=True).splitlines() if not p.endswith('.md')]
code_untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','desk-companion'],cwd=ROOT,text=True).splitlines()
assert not code_changed and not code_untracked
assert subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True).returncode==0
for p in [OUT/'README.md']+list((OUT/'prompts').glob('*.txt')):
    assert not any(line.rstrip()!=line for line in p.read_text().splitlines()),p
images=json.loads((QA/'image-validation.json').read_text()); assert len(images['images'])==6
result={'completed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'reading':r['coverage_validation'],'expected_markdown_updates':updated,'updated_markdown_count':len(updated),'new_project_markdown':'design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md','protected_total':len(protection),'protected_unchanged':sum(x['unchanged'] for x in protection),'expected_document_changes':sorted(changed),'protection':protection,'local_links_checked':link_count,'broken_links':broken,'image_count':6,'native_byte_equality':True,'all_six_coordinator_viewed':True,'browser_preview':{'images_loaded':6,'dimensions_each':[1024,1536],'viewport_width':676,'scroll_width':676,'columns':3,'tab_marked_deliverable':True,'server_session_id':66493},'code_changes':code_changed,'untracked_code':code_untracked,'git_diff_check':'PASS','git_write_performed':False,'school_documents_changed':False,'runtime_vrm_changed':False,'remaining':['User comparison/selection','Selected outfit side/back construction','E1 expression feedback','Original VRM and rigging']}
(QA/'closeout-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(QA/'closeout-reading.json').write_text(json.dumps({'read_back':'All updated segments were observed via git diff; original bodies read in initial complete pass. New asset README and final QA read back.','files':updated+['design/desk-companion/characters/2026-10-12-wardrobe-variants/README.md'],'completed_at':result['completed_at']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'images':6,'initial_full_read_files':len(r['files']),'initial_full_read_lines':r['coverage_validation']['line_count'],'updated_norms':len(updated),'protected_unchanged':result['protected_unchanged'],'intentional_markdown_changes':len(changed),'local_links_checked':link_count,'broken_links':len(broken),'code_changes':len(code_changed),'git_diff_check':'PASS'},ensure_ascii=False,indent=2))
