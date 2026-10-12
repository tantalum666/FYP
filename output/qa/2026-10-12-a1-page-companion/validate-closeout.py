import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def compare(name):
    rows = json.loads((ROOT / name).read_text())
    failures = [r['path'] for r in rows if sha(ROOT / r['path']) != r['sha256']]
    return {'checked': len(rows), 'failures': failures}

protected = compare('output/qa/2026-10-12-a1-page-companion/protected-before.json')
runtime = compare('output/qa/2026-10-12-web-linux-preview/main-runtime-before.json')
source = ROOT / 'design/desk-companion/characters/2026-10-12-a1-interface'
native = []
for name in ['a1-idle-v1','a1-acknowledge-v1']:
    receipt = json.loads((source / (name+'.receipt.json')).read_text())
    native.append({'asset': name, 'native': sha(receipt['native_original_path']), 'source': sha(source / (name+'.png')), 'expected': receipt['sha256'], 'prompt': sha(source / receipt['prompt_path']) if not str(receipt['prompt_path']).startswith('/') else sha(receipt['prompt_path'])})
    assert native[-1]['native'] == native[-1]['source'] == native[-1]['expected']
    assert native[-1]['prompt'] == receipt['prompt_sha256']
public = ROOT / 'desk-companion/frontend/public/companion'
assert sha(public/'a1-idle-v1.png') == native[0]['expected']
assert not (public/'a1-acknowledge-v1.png').exists()
assert not (public/'a1-engineering-v1.glb').exists()
assert not (ROOT/'desk-companion/frontend/src/companion/A1Scene.tsx').exists()
assert not (ROOT/'desk-companion/frontend/src/companion/DepthCharacter.tsx').exists()

paths = subprocess.check_output(['rg','--files','--hidden','-g','*.md','-g','!.git/**','-g','!**/node_modules/**','-g','!**/.venv/**','-g','!**/dist/**','-g','!output/qa/**'], cwd=ROOT, text=True).splitlines()
baseline = json.loads((QA/'reading-record.json').read_text())
before = {r['path']: r for r in baseline['inventory']}
changed = [p for p in paths if p not in before or sha(ROOT/p) != before[p]['sha256']]
broken=[];links=0
for name in changed + ['output/qa/2026-10-12-a1-page-companion/verification.md']:
    path=ROOT/name
    for match in re.finditer(r'!?\[[^\]]*\]\((<[^>]*>|[^)]+)\)',path.read_text()):
        target=match.group(1).strip().strip('<>')
        if re.match(r'^[a-zA-Z][\w+.-]*:',target) or target.startswith('#'):continue
        target=unquote(target.split('#')[0])
        if not target:continue
        links+=1
        if not (path.parent/target).resolve().exists():broken.append({'file':name,'target':target})
browser=json.loads((QA/'browser-final-2d.json').read_text())
assert browser['logs'] == []
for r in browser['evidence']:
    assert r['renderer']=='whole-image-2d' and r['canvases']==0 and r['jointMasks']==0
    assert r['images']==(0 if r['mode']=='hidden' else 1)
    assert r['width']==r['viewport']
pose=next(r['responseTransform']for r in browser['evidence']if r['label']=='single-image-rigid-response')
matrix=[float(n)for n in re.findall(r'-?\d+(?:\.\d+)?',pose)]
a,b,c,d=matrix[:4]
assert abs(a*a+b*b-1)<.0001 and abs(c*c+d*d-1)<.0001 and abs(a*c+b*d)<.0001
assert '# pass 28' in (QA/'frontend-tests.log').read_text()
assert 'built in' in (QA/'build.log').read_text()
assert not protected['failures'] and not runtime['failures'] and not broken
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'protected':protected,'original_runtime':runtime,'native_and_source':native,'public_png_sha256':sha(public/'a1-idle-v1.png'),'current_project_md_count':len(paths),'changed_or_new_md':changed,'local_links_checked':links,'broken_links':broken,'final_frontend_tests':28,'browser_records':len(browser['evidence']),'rigid_response_matrix':matrix,'final_renderer':'whole-image-2d','original_vrm_sha256':sha(ROOT/'desk-companion/frontend/public/avatars/pixiv-sample.vrm')}
(QA/'closeout-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(QA/'closeout-reading.json').write_text(json.dumps({'inherited_full_read':baseline['inherited_full_read'],'inherited_full_read_count':139,'inherited_full_read_lines':12884,'baseline_readback':baseline['latest_readback'],'same_task_continuation':True,'current_inventory':[{'path':p,'lines':len((ROOT/p).read_text().splitlines()),'sha256':sha(ROOT/p)}for p in sorted(paths)],'new_full_reads':[p for p in changed if p not in before],'modified_content_readback':changed,'read_method':'New focused documents read fully; changed normative bodies read through diffs with truncated middle supplemented; unchanged historical bodies inherit verified full reads. Hashes detect changes only.','exclusions':baseline['exclusions'],'recorded_at':result['recorded_at']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k not in ['native_and_source','changed_or_new_md']},indent=2))
