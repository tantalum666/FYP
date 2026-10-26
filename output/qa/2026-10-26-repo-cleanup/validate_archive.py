"""Validate the relocated tree against its explicit original-path manifest."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import hashlib,json,posixpath,re,subprocess
ROOT=Path(__file__).resolve().parents[3];QA=Path(__file__).parent
manifest_path=ROOT/'archive/senplate/archive-manifest.json';manifest=json.loads(manifest_path.read_text());base=manifest['base_commit'];moves={x['old_path']:x['new_path'] for x in manifest['moves']}
repairs={'scripts/dev.py':'Loopback TCP avoids deep Unix socket path limit','apps/operations-web/package.json':'Vite 8.3.5 security patch','apps/operations-web/package-lock.json':'Vite build dependencies and source-map-js 1.2.2 patch'}
changes=[];media=0;licences=0
for x in manifest['moves']:
 old,new=x['old_path'],x['new_path'];p=ROOT/new;assert p.is_file(),new;assert not (ROOT/old).exists(),old
 raw=p.read_bytes();after=hashlib.sha256(raw).hexdigest();changed=after!=x['sha256_before']
 if changed:
  assert p.suffix=='.md' or old in repairs,old
  changes.append({'path':new,'reason':repairs.get(old,'Navigational Markdown links')})
 x.update(sha256_after=after,bytes_after=len(raw),content_change=repairs.get(old,'navigation links only') if changed else 'byte-identical')
 if p.suffix.lower() in {'.pdf','.doc','.docx','.xlsx','.png','.jpg','.jpeg','.gif','.webp','.zip','.tar','.gz','.ttf','.woff','.woff2','.otf'}:assert not changed,new;media+=1
 if re.search(r'(^|/)(licen[cs]e[^/]*|ofl[^/]*)$',new,re.I):assert not changed,new;licences+=1
manifest['post_relocation_repairs']=repairs;manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
basefiles=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',base],cwd=ROOT).decode().split('\0')[:-1]
assert all((ROOT/moves.get(p,p)).is_file() for p in basefiles)
identity='planning/2026-09-14/group-2-details.json';original=subprocess.check_output(['git','show',base+':'+identity],cwd=ROOT);snapshot=ROOT/'archive/senplate'/identity
assert snapshot.read_bytes()==original
oldgroup=json.loads(original);newgroup=json.loads((ROOT/identity).read_text())
for key in ['group_number','group_display_name','programme','class_code','proposed_supervisor','supervisor_verbal_agreement','members']:assert oldgroup[key]==newgroup[key],key
assert sum(m['planned_contribution_percent'] for m in newgroup['members'])==100
inputs=json.loads((ROOT/'inputs/manifest.json').read_text())
for f in inputs['files']:assert hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
current_deliverables=[p for p in basefiles if p.startswith('output/submission/') or (p.startswith('output/docx/') and 'DeskCompanion' in p)]
for p in current_deliverables:assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show',base+':'+p],cwd=ROOT),p
code_changes=subprocess.check_output(['git','diff','--name-only',base,'--','desk-companion/'],cwd=ROOT,text=True).splitlines()
assert set(code_changes)<={'desk-companion/README.md','desk-companion/frontend/package.json','desk-companion/frontend/package-lock.json'},code_changes
# Frozen QA copies retain source-root links; vendor examples may refer to unvendored docs.
paths={moves.get(p,p) for p in basefiles if p.endswith('.md')};paths.update(['archive/senplate/README.md','archive/senplate/decision-log.md','archive/senplate/work-log.md','output/qa/2026-10-26-repo-cleanup/verification.md'])
excluded=[];bad=[];checked=0
for name in sorted(paths):
 if '/vendor/' in name or ('output/qa/' in name and '-before' in Path(name).name):excluded.append({'path':name,'reason':'Frozen automatic snapshot or third-party example; retain original bytes and historical links'});continue
 for raw in re.findall(r'\]\((<[^>]+>|[^)\n]+)\)',(ROOT/name).read_text()):
  target=raw.strip('<>').split('#')[0]
  if not target or target.startswith('/') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
  dest=posixpath.normpath(posixpath.join(str(Path(name).parent),unquote(target)));checked+=1
  if not (ROOT/dest).exists():bad.append({'source':name,'target':dest})
assert not bad,bad
strip_links=lambda s:re.sub(r'\]\((<[^>]+>|[^)\n]+)\)','](LINK)',s)
for name in ['decision-log.md','work-log.md']:
 old=subprocess.check_output(['git','show',base+':'+name],cwd=ROOT,text=True);before=old[:re.search(r'^## 2026-09-25\b',old,re.M).start()]
 assert strip_links(before).rstrip() in strip_links((ROOT/'archive/senplate'/name).read_text()),name
for name in ['desk','senplate']:
 audit=json.loads((QA/f'{name}-audit-after.json').read_text());assert audit['metadata']['vulnerabilities']['total']==0
result={'base_commit':base,'moved_files':len(moves),'byte_identical_moved_files':len(moves)-len(changes),'intentional_text_changes':changes,'preserved_media_documents_fonts_archives':media,'preserved_licence_files':licences,'canonical_identity_preserved':True,'exact_historical_identity_snapshot':True,'input_original_hashes_checked':len(inputs['files']),'current_school_deliverables_unchanged':len(current_deliverables),'active_application_business_source_unchanged':True,'allowed_active_changes':code_changes,'maintained_markdown_links_checked':checked,'broken_maintained_links':bad,'frozen_snapshot_or_vendor_exclusions':excluded,'original_paths_accounted_for':len(basefiles)}
(QA/'archive-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['intentional_text_changes','frozen_snapshot_or_vendor_exclusions']},ensure_ascii=False,indent=2))
