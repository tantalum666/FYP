from pathlib import Path
from datetime import datetime,timezone
from math import sin,cos,pi,hypot
import hashlib,json,re,zipfile,xml.etree.ElementTree as E
import numpy as np
from PIL import Image
R=Path('/Users/tantalum/Documents/ChatGPT/FYP');A=R/'output/brand/2026-09-17-senplate-ellipse-a-v4';Q=R/'output/qa/senplate-ellipse-a-v4-2026-09-17';now=datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((Q/'protected-before.json').read_text());changed=[x['path'] for x in protected if not (R/x['path']).exists() or sha(R/x['path'])!=x['sha256']]
assert not changed,changed
source_sha='cc98804614d8e0de4e15d1e5dd197550f3bef06a4569cc5c4c3b9f54e2929a61'
assert sha(A/'source-selected-a.png')==sha(Path('/Users/tantalum/Downloads/ChatGPT Image 2026年9月17日 11_43_29.png'))==source_sha
c=json.loads((Q/'ellipse-construction.json').read_text());phi=c['phi'];d=c['dimensions'];s=c['symmetry']
for key,value in c['ratios'].items():assert abs(value-(phi**2 if key=='outer_ellipse_width_over_height' else phi))<1e-12
assert s['max_mirror_coordinate_error']<1e-10 and s['max_curvature_error']<1e-12
def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def tangent_error(a,b):
 lengths=hypot(*a)*hypot(*b)
 return {'cross_error':abs(a[0]*b[1]-a[1]*b[0])/lengths,'direction_dot':(a[0]*b[0]+a[1]*b[1])/lengths}
rx,ry=d['outer_radii'];irx,iry=d['inner_radii'];tl,tr=[x*pi/180 for x in d['outer_cap_angles_degrees']]
ol,orr=d['outer_endpoints'];il,ir=d['inner_endpoints'];cp1,cp2=d['right_cap_controls'];lp1,lp2=d['left_cap_controls']
tangents=[tangent_error((rx*sin(tr),-ry*cos(tr)),sub(cp1,orr)),tangent_error(sub(ir,cp2),(-irx*sin(tr),iry*cos(tr))),tangent_error((-irx*sin(tl),iry*cos(tl)),sub(lp1,il)),tangent_error(sub(ol,lp2),(rx*sin(tl),-ry*cos(tl)))]
assert all(t['cross_error']<1e-12 and t['direction_dot']>1-1e-12 for t in tangents),tangents
assert max(abs(lp1[0]+cp2[0]-320),abs(lp1[1]-cp2[1]),abs(lp2[0]+cp1[0]-320),abs(lp2[1]-cp1[1]))<1e-12
ns='{http://www.w3.org/2000/svg}';svgs=[]
for p in sorted(A.glob('*.svg')):
 root=E.fromstring(p.read_text());paths=root.findall('.//'+ns+'path');tags=[x.tag.rsplit('}',1)[-1] for x in root.iter()]
 assert not set(tags)&{'text','image','script'}
 count=1 if p.name=='bowl-only.svg' else 4 if p.name=='ellipse-construction-grid.svg' else 8 if 'wordmark' in p.name else 3 if '-mark-' in p.name else 11
 assert len(paths)==count,(p.name,len(paths),count)
 svgs.append({'name':p.name,'viewBox':root.attrib['viewBox'],'paths':len(paths),'sha256':sha(p)})
assert len(svgs)==10
for kind in ['mark','logo']:
 green=(A/f'senplate-{kind}-green.svg').read_text()
 for name,color in [('black','#000000'),('white','#FFFFFF')]:assert (A/f'senplate-{kind}-{name}.svg').read_text()==green.replace('#163F35',color)
def word_paths(p):return [(n.attrib['d'],n.attrib.get('transform')) for n in E.fromstring(p.read_text()).findall('.//'+ns+'path')]
assert word_paths(A/'senplate-wordmark-green.svg')==word_paths(R/'output/brand/2026-09-17-senplate-refined-a-v2/senplate-wordmark-green.svg')
plate_path=E.fromstring((A/'bowl-only.svg').read_text()).find(ns+'path').attrib['d']
assert re.findall('[MACLQZ]',plate_path)==['M','A','C','A','C','Z']
pngs=[]
for p in sorted(A.glob('*.png')):
 with Image.open(p) as im:
  im.load();rgba=im.convert('RGBA');alpha=rgba.getchannel('A').getextrema()
  entry={'name':p.name,'size':list(im.size),'alpha_extrema':list(alpha),'sha256':sha(p)}
  if p.name.startswith('app-icon-'):
   assert im.size==(1024,1024) and alpha==(255,255)
   color=(22,63,53) if 'forest' in p.name else (243,241,231) if 'ivory' in p.name else (0,0,0)
   assert rgba.getpixel((0,0))[:3]==color
  elif p.name.startswith('senplate-logo-') or p.name=='senplate-capital-s-comparison.png':assert im.size==(2036,360) and alpha==(0,255)
  elif p.name.startswith('senplate-mark-'):
   last=p.stem.split('-')[-1];size=(int(last),int(last)) if last.isnumeric() else (1280,720)
   assert im.size==size and alpha[0]==0
  elif p.name=='brand-preview.png':assert im.size==(1440,1100)
  elif p.name=='ellipse-construction.png':assert im.size==(1440,820)
  elif p.name=='curves-before-after.png':assert im.size==(1440,760)
  elif p.name=='bowl-before-after.png':assert im.size==(1440,500)
  elif p.name=='bowl-only.png':assert im.size==(1280,489)
  elif p.name=='source-selected-a.png':assert im.size==(1536,1024)
  pngs.append(entry)
assert len(pngs)==19
with Image.open(A/'bowl-only.png') as im:alpha=np.array(im.convert('RGBA'))[:,:,3]
flipped=np.fliplr(alpha);delta=np.abs(alpha.astype(float)-flipped.astype(float));partial=((alpha>0)&(alpha<255))|((flipped>0)&(flipped<255))
render={'mean_alpha_absolute_difference':float(delta.mean()),'max_alpha_difference':float(delta.max()),'binary_mask_disagreement_fraction':float(np.mean((alpha>=128)!=(flipped>=128))),'differences_outside_antialiased_edges':int(np.count_nonzero((delta>0)&~partial))}
assert render['binary_mask_disagreement_fraction']<.0005 and render['differences_outside_antialiased_edges']==0,render
exports=[{k:v for k,v in x.items() if k!='data'} for x in json.loads((Q/'native-png-exports.json').read_text())]
manifest={'brand':'Senplate','version':'4.0','status':'A_CONCEPT_CURVE_REPAIR_READY_FOR_FEEDBACK','updated_at':now,'construction':c,'cap_tangent_validation':tangents,'bowl_native_render_mirror_comparison':render,'word_paths_unchanged':True,'source_sha256':source_sha,'capitalization':{'logo':'senplate','ios_display_name_app_name_prose':'Senplate','initial_capital':'comparison only'},'palette':{'forest':'#163F35','ivory':'#F3F1E7','black':'#000000','white':'#FFFFFF'},'figma':{'file_key':'UyYjnTFGWO0r1lj4uvghGp','logo':'68:2','mark':'68:15','bowl':'68:40','brand_board':'69:2','whole_comparison':'70:31','bowl_comparison':'71:2','construction_board':'72:2','native_png_exports':exports},'svg':svgs,'png':pngs,'limits':['Bowl is mirrored; food and dot intentionally remain offset.','Entire symbol outer box is no longer constrained to phi.','PNG has small edge antialiasing differences; not bit-identical under reflection.','Geometry validation is not user aesthetic approval.','No new trademark search or app implementation.'],'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(A.iterdir()) if p.is_file() and p.name!='manifest.json']}
(A/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
zpath=R/'output/brand/Senplate_Brand_Assets_v4.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(A.iterdir()):
  if p.is_file():z.write(p,'Senplate_Brand_Assets_v4/'+p.name)
with zipfile.ZipFile(zpath) as z:
 assert z.testzip() is None
 assert len(z.namelist())==31
updated=['brand.md','README.md','product.md','handoff.md','decision-log.md','work-log.md','planning/2026-09-16/software-scope-and-architecture.md','planning/2026-09-16/software-mvp-and-acceptance.md','output/brand/2026-09-17-senplate-ellipse-a-v4/README.md']
(Q/'closeout-validation.json').write_text('{}\n');missing=[]
for rel in updated:
 p=R/rel
 for raw in re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)',p.read_text()):
  target=raw[1:-1] if raw.startswith('<') else raw
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
  target=target.split('#',1)[0]
  if target and not (p.parent/target).exists():missing.append({'file':rel,'target':target})
assert not missing,missing
record=json.loads((Q/'reading-record.json').read_text());record['supplemental_reads'].update({'README.md':'1-18 plus inherited full body','planning/2026-09-16/software-scope-and-architecture.md':'1-12 plus inherited full body','planning/2026-09-16/software-mvp-and-acceptance.md':'1-5 plus inherited full body','output/brand/2026-09-17-senplate-golden-a-v3/README.md':'full'});record['new_authored_markdown']=['output/brand/2026-09-17-senplate-ellipse-a-v4/README.md'];record['updated_files']=[{'path':p,'lines':len((R/p).read_text().splitlines()),'sha256':sha(R/p)} for p in updated];record['completed_at']=now
(Q/'reading-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
report={'status':'PASS','completed_at':now,'protected_count':len(protected),'protected_changes':changed,'source_preserved':True,'symmetry':s,'cap_tangent_checks':tangents,'native_bowl_render_symmetry':render,'golden_ratios':c['ratios'],'word_paths_unchanged':True,'color_variants_same_geometry':True,'svg':svgs,'png':pngs,'visual_checks':['Main logo enlarged','Bowl-only enlarged comparison','V3 vs V4 complete logo','Ellipse construction','Black, reversed and app icon versions','24,32,64px samples'],'resolved_tool_issue':'First construction script cached a removed node; operation rolled back. Rebuilt after acquiring needed nodes before deletion.','missing_local_links':missing,'updated_markdown':updated,'zip':{'path':str(zpath.relative_to(R)),'files':31,'sha256':sha(zpath)},'remaining':['User visual feedback on V4','Fresh final-symbol similarity check','App UI design and implementation']}
(Q/'closeout-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','symmetry':render,'tangent_max_cross_error':max(x['cross_error'] for x in tangents),'protected':len(protected),'svg':len(svgs),'png_including_original':len(pngs),'zip_files':31,'missing_links':len(missing)}))
