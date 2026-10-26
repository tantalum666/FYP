from pathlib import Path
from decimal import Decimal
import hashlib,json,re,subprocess
from pypdf import PdfReader
root=Path(__file__).resolve().parents[3]
r=root/'research/2026-10-23-mini-robot-hardware';q=Path(__file__).parent
manifest=json.loads((r/'artifact-manifest.json').read_text())
for f in manifest['files']:
 raw=(r/f['path']).read_bytes()
 assert len(raw)==f['bytes'] and hashlib.sha256(raw).hexdigest()==f['sha256'],f['path']
 assert subprocess.check_output(['git','hash-object',str(r/f['path'])],text=True).strip()==f['git_blob_sha1']
a=json.loads((r/'component-sources.json').read_text());c=json.loads((r/'completeness-checklist.json').read_text())
assert len(a)==len({x['id'] for x in a})==13 and len(c)==22
subtotal=sum(Decimal(x['unit_price_usd'])*x['purchase_packages'] for x in a if x['id'].startswith('D'))
assert subtotal==Decimal('76.89')
pdf=r/'mini_robot_finished_parts_catalog_expanded_20261023.pdf'
assert hashlib.sha256(pdf.read_bytes()).hexdigest()=='4b225e9baa76c0b130891ba5f90557a0f5425ccf6185b9ff5f16f4a985d45182'
doc=PdfReader(pdf)
pages=len(doc.pages)
images=sum(len(p.images) for p in doc.pages)
links=sum(sum(1 for a in p.get('/Annots',[]) if a.get_object().get('/Subtype')=='/Link') for p in doc.pages)
assert (pages,images,links)==(9,13,30),(pages,images,links)
count=0
for p in [*r.glob('*.md'),root/'product.md',root/'handoff.md',root/'decision-log.md',root/'work-log.md']:
 for target in re.findall(r'\]\((<[^>]+>|[^)\n]+)\)',p.read_text()):
  target=target.strip('<>').split('#')[0]
  if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('/'):continue
  from urllib.parse import unquote
  assert (p.parent/unquote(target)).exists(),(str(p),target)
  count+=1
assert not subprocess.check_output(['git','diff','--name-only','origin/main','--','desk-companion/']).strip()
result={'original_head':'8141d374e6e3d476d874310a7fed158a51fc28df','manifest_hashes':'pass','source_records':len(a),'checklist_rows':len(c),'walking_subtotal_usd':str(subtotal),'pdf':{'pages':pages,'images':images,'links':links,'bytes_unchanged':True,'all_pages_visually_checked':True},'relative_links_checked':count,'application_source_unchanged':True,'remote_ci':'No checks or statuses exist for the original PR head; not represented as a pass.'}
(q/'pr17-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
