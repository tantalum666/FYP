from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,zipfile,xml.etree.ElementTree as E
from PIL import Image
R=Path('/Users/tantalum/Documents/ChatGPT/FYP'); A=R/'output/brand/2026-09-17-senplate-refined-a-v2'; Q=R/'output/qa/senplate-refined-a-v2-2026-09-17'
now=datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((Q/'protected-before.json').read_text());changed=[x['path'] for x in protected if not (R/x['path']).exists() or sha(R/x['path'])!=x['sha256']]
assert not changed,changed
source_sha='cc98804614d8e0de4e15d1e5dd197550f3bef06a4569cc5c4c3b9f54e2929a61'
assert sha(A/'source-selected-a.png')==source_sha
svgs=[]
for f in sorted(A.glob('*.svg')):
 n=E.fromstring(f.read_text());paths=n.findall('.//{http://www.w3.org/2000/svg}path');tags=[x.tag.rsplit('}',1)[-1] for x in n.iter()]
 assert not set(tags)&{'image','script','text'}
 expected=8 if 'wordmark' in f.name else 3 if '-mark-' in f.name else 11
 assert len(paths)==expected,(f.name,len(paths))
 svgs.append({'name':f.name,'paths':len(paths),'path_commands':sum(len(re.findall('[MLHVQCZ]',p.attrib['d'])) for p in paths),'viewBox':n.attrib['viewBox']})
assert len(svgs)==8
for kind in ['mark','logo']:
 green=(A/f'senplate-{kind}-green.svg').read_text()
 for name,color in [('black','#000000'),('white','#FFFFFF')]:assert (A/f'senplate-{kind}-{name}.svg').read_text()==green.replace('#163F35',color)
old=E.fromstring((R/'output/brand/2026-09-17-senplate-selected-a/senplate-mark-green.svg').read_text())
old_commands=sum(len(re.findall('[MLHVQCZ]',p.attrib['d'])) for p in old.findall('.//{http://www.w3.org/2000/svg}path'))
new_commands=next(x['path_commands'] for x in svgs if x['name']=='senplate-mark-green.svg')
assert new_commands<old_commands
pngs=[]
for f in sorted(A.glob('*.png')):
 with Image.open(f) as im:
  im.load();rgba=im.convert('RGBA');alpha=rgba.getchannel('A').getextrema();entry={'name':f.name,'size':list(im.size),'alpha_extrema':list(alpha),'sha256':sha(f)}
  if f.name.startswith('app-icon-'):
   assert im.size==(1024,1024) and alpha==(255,255)
   color=(22,63,53) if 'forest' in f.name else (243,241,231) if 'ivory' in f.name else (0,0,0)
   assert rgba.getpixel((0,0))[:3]==color
  elif f.name.startswith('senplate-logo-') or f.name=='senplate-capital-s-comparison.png':assert im.size==(2056,340) and alpha==(0,255)
  elif f.name.startswith('senplate-mark-'):
   last=f.stem.split('-')[-1];size=(int(last),int(last)) if last.isnumeric() else (1300,680)
   assert im.size==size and alpha[0]==0
  elif f.name=='brand-preview.png':assert im.size==(1440,1100)
  elif f.name=='capitalization-comparison.png':assert im.size==(1440,760)
  elif f.name=='edge-comparison.png':assert im.size==(1440,480)
  elif f.name=='source-selected-a.png':assert im.size==(1536,1024)
  pngs.append(entry)
assert len(pngs)==17
nodes=[{k:v for k,v in x.items() if k!='data'} for x in json.loads((Q/'native-png-exports.json').read_text())]
manifest={'brand':'Senplate','version':'2.0','updated_at':now,'status':'SELECTED_A_REFINED_LOWERCASE','source_sha256':source_sha,'source_preserved':True,'supersedes':'V1 rough auto-trace, retained separately','capitalization':{'logo':'senplate','prose_app_name':'Senplate','initial_capital':'comparison only, not selected'},'construction':json.loads((Q/'vector-construction.json').read_text()),'font':{'original_family':None,'method':'custom reconstructed letter paths based on selected structure','font_substitution':False},'palette':{'forest':'#163F35','ivory':'#F3F1E7','black':'#000000','white':'#FFFFFF'},'figma':{'file_key':'UyYjnTFGWO0r1lj4uvghGp','brand_board':'55:2','logo':'53:2','mark':'53:15','case_comparison':'56:2','edge_comparison':'57:25','native_png_exports':nodes},'svg':svgs,'png':pngs,'caveats':['24px has a thin rim; recommend 32px minimum, prefer 48px or larger.','PNG has finite resolution; use SVG for scaling.','No fresh trademark search or original font provenance determination.','No app implementation.'],'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(A.iterdir()) if p.is_file() and p.name!='manifest.json']}
(A/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
zpath=R/'output/brand/Senplate_Brand_Assets_v2.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(A.iterdir()):
  if p.is_file():z.write(p,'Senplate_Brand_Assets_v2/'+p.name)
with zipfile.ZipFile(zpath) as z:
 assert z.testzip() is None
 assert len(z.namelist())==27
updated=['brand.md','README.md','product.md','handoff.md','decision-log.md','work-log.md','planning/2026-09-16/software-scope-and-architecture.md','planning/2026-09-16/software-mvp-and-acceptance.md','output/brand/2026-09-17-senplate-refined-a-v2/README.md']
(Q/'closeout-validation.json').write_text('{}\n');missing=[]
for rel in updated:
 p=R/rel
 for raw in re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)',p.read_text()):
  target=raw[1:-1] if raw.startswith('<') else raw
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
  target=target.split('#',1)[0]
  if target and not (p.parent/target).exists():missing.append({'file':rel,'target':target})
assert not missing,missing
record=json.loads((Q/'reading-record.json').read_text());record['supplemental_reads'].update({'README.md':'1-20 plus prior full read','planning/2026-09-16/software-scope-and-architecture.md':'1-15 plus prior full read','planning/2026-09-16/software-mvp-and-acceptance.md':'1-5,94-105 plus prior full read'});record['authored_new_markdown']=['output/brand/2026-09-17-senplate-refined-a-v2/README.md'];record['updated_files']=[{'path':p,'lines':len((R/p).read_text().splitlines()),'sha256':sha(R/p)} for p in updated];record['completed_at']=now
(Q/'reading-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
report={'status':'PASS','completed_at':now,'protected_count':len(protected),'protected_changes':changed,'source_preserved':True,'svg':svgs,'png':pngs,'all_color_variants_same_geometry':True,'mark_commands_v1':old_commands,'mark_commands_v2':new_commands,'command_count_note':'Simplification evidence only, not a standalone smoothness test.','visual_review':['2056px lowercase and initial capital logo','V1 vs V2 edge closeup: old irregularities removed','Main board, black, reverse, icons','24,32,64px original size'],'missing_local_links':missing,'updated_markdown':updated,'zip':{'path':str(zpath.relative_to(R)),'files':27,'sha256':sha(zpath)},'remaining':['User can select initial-capital variant; default remains lowercase.','Fresh final-symbol similarity check','UI design and implementation']}
(Q/'closeout-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','svg':len(svgs),'png_with_original':len(pngs),'protected':len(protected),'mark_commands':[old_commands,new_commands],'zip_files':27,'missing_links':len(missing)}))
