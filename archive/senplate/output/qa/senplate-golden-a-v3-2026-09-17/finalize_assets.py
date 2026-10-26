from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,zipfile,xml.etree.ElementTree as E
from PIL import Image
R=Path('/Users/tantalum/Documents/ChatGPT/FYP');A=R/'output/brand/2026-09-17-senplate-golden-a-v3';Q=R/'output/qa/senplate-golden-a-v3-2026-09-17';now=datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((Q/'protected-before.json').read_text());changed=[x['path'] for x in protected if not (R/x['path']).exists() or sha(R/x['path'])!=x['sha256']]
assert not changed,changed
source_sha='cc98804614d8e0de4e15d1e5dd197550f3bef06a4569cc5c4c3b9f54e2929a61'
assert sha(A/'source-selected-a.png')==sha(Path('/Users/tantalum/Downloads/ChatGPT Image 2026年9月17日 11_43_29.png'))==source_sha
c=json.loads((Q/'golden-ratio-construction.json').read_text());f=json.loads((Q/'figma-geometry.json').read_text());phi=c['phi'];cx=f['dot']['x']+f['dot']['width']/2
actual={'symbol_width_over_height':f['mark']['width']/f['mark']['height'],'portion_width_over_height':f['portion']['width']/f['portion']['height'],'dot_left_over_right':cx/(f['mark']['width']-cx),'dot_diameter_over_gap':f['dot']['width']/f['signatureGap'],'symbol_height_over_stem':f['mark']['height']/f['wordStemHeight']}
assert all(abs(v-phi)<1e-5 for v in actual.values()),actual
assert all(abs(v-phi)<1e-12 for v in c['ratios'].values())
ns='{http://www.w3.org/2000/svg}';svgs=[]
for p in sorted(A.glob('*.svg')):
 root=E.fromstring(p.read_text());paths=root.findall('.//'+ns+'path');tags=[n.tag.rsplit('}',1)[-1] for n in root.iter()]
 assert not set(tags)&{'image','text','script'}
 count=5 if p.name=='construction-grid.svg' else 8 if 'wordmark' in p.name else 3 if '-mark-' in p.name else 11
 assert len(paths)==count,(p.name,len(paths),count)
 svgs.append({'name':p.name,'viewBox':root.attrib['viewBox'],'path_count':len(paths),'sha256':sha(p)})
assert len(svgs)==9
for kind in ['mark','logo']:
 original=(A/f'senplate-{kind}-green.svg').read_text()
 for name,color in [('black','#000000'),('white','#FFFFFF')]:assert (A/f'senplate-{kind}-{name}.svg').read_text()==original.replace('#163F35',color)
def letter_data(p):
 root=E.fromstring(p.read_text());return [(n.attrib['d'],n.attrib.get('transform')) for n in root.findall('.//'+ns+'path')]
assert letter_data(A/'senplate-wordmark-green.svg')==letter_data(R/'output/brand/2026-09-17-senplate-refined-a-v2/senplate-wordmark-green.svg')
pngs=[]
for p in sorted(A.glob('*.png')):
 with Image.open(p) as im:
  im.load();rgba=im.convert('RGBA');alpha=rgba.getchannel('A').getextrema()
  entry={'name':p.name,'size':list(im.size),'alpha_extrema':list(alpha),'sha256':sha(p)}
  if p.name.startswith('app-icon-'):
   assert im.size==(1024,1024) and alpha==(255,255)
   color=(22,63,53) if 'forest' in p.name else (243,241,231) if 'ivory' in p.name else (0,0,0)
   assert rgba.getpixel((0,0))[:3]==color
  elif p.name.startswith('senplate-logo-') or p.name=='senplate-capital-s-comparison.png':assert im.size==(2036,396) and alpha==(0,255)
  elif p.name.startswith('senplate-mark-'):
   last=p.stem.split('-')[-1];size=(int(last),int(last)) if last.isnumeric() else (1280,792)
   assert im.size==size and alpha[0]==0
  elif p.name=='brand-preview.png':assert im.size==(1440,1100)
  elif p.name=='golden-ratio-construction.png':assert im.size==(1440,820)
  elif p.name=='proportions-before-after.png':assert im.size==(1440,760)
  elif p.name=='source-selected-a.png':assert im.size==(1536,1024)
  pngs.append(entry)
assert len(pngs)==17
exports=[{k:v for k,v in x.items() if k!='data'} for x in json.loads((Q/'native-png-exports.json').read_text())]
manifest={'brand':'Senplate','version':'3.0','status':'SELECTED_A_GOLDEN_RATIO_REFINEMENT','updated_at':now,'source_sha256':source_sha,'construction':c,'figma_actual_geometry':f,'actual_ratios':actual,'ratio_absolute_tolerance':1e-5,'word_letter_paths_unchanged_from_v2':True,'capitalization':{'logo':'senplate','ios_display_name_app_name_prose':'Senplate','initial_capital_variant':'comparison only, not selected'},'palette':{'forest':'#163F35','ivory':'#F3F1E7','black':'#000000','white':'#FFFFFF'},'figma':{'file_key':'UyYjnTFGWO0r1lj4uvghGp','logo':'60:2','mark':'60:15','brand_board':'61:2','construction':'62:2','before_after':'63:2','native_png_exports':exports},'svg':svgs,'png':pngs,'limits':['Main dimensions follow phi; all curve points are not claimed to come from a golden spiral.','Phi does not itself prove better aesthetics or recognition.','PNG dimensions are integer-rounded; exact proportions belong to SVG geometry.','No new trademark search, app code or registration.'],'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(A.iterdir()) if p.is_file() and p.name!='manifest.json']}
(A/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
zpath=R/'output/brand/Senplate_Brand_Assets_v3.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(A.iterdir()):
  if p.is_file():z.write(p,'Senplate_Brand_Assets_v3/'+p.name)
with zipfile.ZipFile(zpath) as z:
 assert z.testzip() is None
 assert len(z.namelist())==28
updated=['brand.md','README.md','product.md','handoff.md','decision-log.md','work-log.md','planning/2026-09-16/software-scope-and-architecture.md','planning/2026-09-16/software-mvp-and-acceptance.md','output/brand/2026-09-17-senplate-golden-a-v3/README.md']
(Q/'closeout-validation.json').write_text('{}\n');missing=[]
for rel in updated:
 p=R/rel
 for raw in re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)',p.read_text()):
  target=raw[1:-1] if raw.startswith('<') else raw
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
  target=target.split('#',1)[0]
  if target and not (p.parent/target).exists():missing.append({'file':rel,'target':target})
assert not missing,missing
record=json.loads((Q/'reading-record.json').read_text());record['supplemental_reads'].update({'README.md':'1-18 plus inherited full body','planning/2026-09-16/software-scope-and-architecture.md':'1-13 plus inherited full body','planning/2026-09-16/software-mvp-and-acceptance.md':'1-5 and 94-104 plus inherited full body','output/brand/2026-09-17-senplate-refined-a-v2/README.md':'full'});record['new_authored_markdown']=['output/brand/2026-09-17-senplate-golden-a-v3/README.md'];record['updated_files']=[{'path':p,'lines':len((R/p).read_text().splitlines()),'sha256':sha(R/p)} for p in updated];record['completed_at']=now
(Q/'reading-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
report={'status':'PASS','completed_at':now,'protected_count':len(protected),'protected_changes':changed,'source_preserved':True,'construction_ratios':c['ratios'],'actual_figma_ratios':actual,'actual_phi_absolute_errors':{k:abs(v-phi) for k,v in actual.items()},'ratio_tolerance':1e-5,'word_letter_paths_unchanged':True,'color_variants_same_geometry':True,'svg':svgs,'png':pngs,'visual_checks':['2036px main logo','Golden construction grid and dimensions','V2 vs V3 comparison','Main board with black, white and app icon variants','24,32,64px mark samples'],'missing_local_links':missing,'updated_markdown':updated,'zip':{'path':str(zpath.relative_to(R)),'files':28,'sha256':sha(zpath)},'remaining':['User visual feedback on V3','Independent similarity check for final mark','App UI design and implementation']}
(Q/'closeout-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','actual_ratios':actual,'svg':len(svgs),'png_with_original':len(pngs),'protected':len(protected),'zip_files':28,'missing_links':len(missing)}))
