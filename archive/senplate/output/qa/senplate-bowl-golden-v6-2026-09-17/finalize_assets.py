from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,zipfile,xml.etree.ElementTree as E
from PIL import Image
R=Path('/Users/tantalum/Documents/ChatGPT/FYP');A=R/'output/brand/2026-09-17-senplate-bowl-golden-v6';Q=R/'output/qa/senplate-bowl-golden-v6-2026-09-17';now=datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((Q/'protected-before.json').read_text());changed=[x['path'] for x in protected if not (R/x['path']).exists() or sha(R/x['path'])!=x['sha256']];assert not changed,changed
assert sha(A/'source-v5-concept.png')==sha(R/'output/brand/2026-09-17-senplate-bowl-redesign-v5/bowl-01-concept.png')
target=json.loads((Q/'golden-construction.json').read_text());native=json.loads((Q/'measured-golden-ratios.json').read_text());export=json.loads((Q/'measured-svg-export.json').read_text())
assert max(native['target_dimension_absolute_errors'])<.001 and export['max_dimension_error']<.001
assert max(native['absolute_phi_errors'])<.0001 and max(abs(x-target['phi']) for x in export['successive_ratios'])<.0001
assert native['outer_profile_mirror_max_distance']<.005
(A/'golden-ratios.json').write_text(json.dumps({'design_targets':target,'actual_figma_path_measurements':native,'delivered_svg_measurements':export},ensure_ascii=False,indent=2)+'\n')
svg=[];ns='{http://www.w3.org/2000/svg}'
for p in sorted(A.glob('*.svg')):
 root=E.fromstring(p.read_text());tags=[n.tag.rsplit('}',1)[-1] for n in root.iter()];assert not set(tags)&{'image','text','script','linearGradient','radialGradient'}
 paths=root.findall('.//'+ns+'path');expected=9 if '-logo-' in p.name else 1 if '-symbol-' in p.name else 8
 assert len(paths)==expected,(p.name,len(paths))
 svg.append({'name':p.name,'paths':len(paths),'viewBox':root.attrib['viewBox'],'sha256':sha(p)})
assert len(svg)==7
for kind in ['logo','symbol']:
 s=(A/f'senplate-{kind}-green.svg').read_text()
 for color,hex_value in [('black','#000000'),('white','#FFFFFF')]:assert (A/f'senplate-{kind}-{color}.svg').read_text()==s.replace('#163F35',hex_value)
png=[]
for p in sorted(A.glob('*.png')):
 with Image.open(p) as im:
  im.load();rgba=im.convert('RGBA');alpha=rgba.getchannel('A').getextrema();item={'name':p.name,'size':list(im.size),'alpha_extrema':list(alpha),'bytes':p.stat().st_size,'sha256':sha(p)}
  if p.name=='senplate-preview.png':assert im.size==(1774,887) and rgba.getpixel((0,0))==(243,241,231,255)
  elif p.name=='golden-construction.png':assert im.size==(1600,960)
  elif p.name=='monochrome-and-sizes.png':assert im.size==(1440,580)
  elif p.name=='senplate-logo-green.png':assert im.size==(2400,452) and alpha==(0,255)
  elif p.name=='senplate-symbol-green.png':assert im.size==(960,680) and alpha==(0,255)
  elif p.name.startswith('senplate-symbol-'):
   size=int(p.stem.split('-')[-1]);assert im.size==(size,size) and alpha[0]==0
  elif p.name=='source-v5-concept.png':assert im.size==(1774,887)
  png.append(item)
assert len(png)==9
license_text=(A/'Manrope-OFL.txt').read_text();assert 'SIL OPEN FONT LICENSE Version 1.1' in license_text and 'Manrope Project Authors' in license_text
export_specs=[{k:v for k,v in x.items() if k!='data'} for x in json.loads((Q/'native-png-exports.json').read_text())]
manifest={'brand':'Senplate','version':'6.0','status':'SOLID_BOWL_GOLDEN_VECTOR_COMPLETE_FOR_VISUAL_REVIEW','updated_at':now,'authorization':'User said 开始吧 after proposal to construct and verify golden-ratio vector version.','source_v5_sha256':sha(A/'source-v5-concept.png'),'construction_targets':target,'native_measurement_summary':native,'delivered_svg_measurements':export,'font':{'family':'Manrope','style':'Bold','letter_spacing_percent':-2,'editable_text_font_size':202.841924512786,'ink_height_target':197.77087639996634,'source_image_font_identified':False,'license':'SIL OFL 1.1','license_url':'https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt','license_sha256':sha(A/'Manrope-OFL.txt'),'font_binary_bundled':False},'palette':{'green':'#163F35','ivory':'#F3F1E7','black':'#000000','white':'#FFFFFF'},'figma':{'file_key':'UyYjnTFGWO0r1lj4uvghGp','page':'76:2','editable_boolean':'77:8','production_symbol':'78:9','signature':'78:10','editable_text':'76:3','outlined_wordmark':'76:6','preview':'79:2','proof':'79:6','construction':'80:2','native_png_exports':export_specs},'svg':svg,'png':png,'boundaries':['Body height excludes foot; total symbol height is about226.625.','Exact targets are rounded slightly by native Boolean/SVG processing.','Visual review is not final user approval or measured recognition accuracy.','No full VI, app code, hardware verification or new trademark screening.'],'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(A.iterdir()) if p.is_file() and p.name!='manifest.json']}
(A/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
zip_path=R/'output/brand/Senplate_Bowl_Golden_Vector_v6.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(A.iterdir()):
  if p.is_file():z.write(p,'Senplate_Bowl_Golden_Vector_v6/'+p.name)
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 assert len(z.namelist())==20,len(z.namelist())
updated=['brand.md','product.md','README.md','handoff.md','decision-log.md','work-log.md','planning/2026-09-17/senplate-bowl-golden-v6.md','planning/2026-09-17/senplate-bowl-redesign-v5.md','planning/2026-09-16/software-scope-and-architecture.md','planning/2026-09-16/software-mvp-and-acceptance.md','output/brand/2026-09-17-senplate-bowl-golden-v6/README.md']
(Q/'closeout-validation.json').write_text('{}\n');missing=[]
for f in updated:
 p=R/f
 for raw in re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)',p.read_text()):
  link=raw[1:-1] if raw.startswith('<') else raw
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):continue
  link=link.split('#',1)[0]
  if link and not (p.parent/link).exists():missing.append({'file':f,'target':link})
assert not missing,missing
reading=json.loads((Q/'reading-record.json').read_text());reading['supplemental_reads'].update({'README.md':'1-17 plus inherited full body','planning/2026-09-16/software-scope-and-architecture.md':'1-12 plus inherited full body','planning/2026-09-16/software-mvp-and-acceptance.md':'1-5 and94-104 plus inherited full body'});reading['new_authored_markdown']=['planning/2026-09-17/senplate-bowl-golden-v6.md','output/brand/2026-09-17-senplate-bowl-golden-v6/README.md'];reading['updated_files']=[{'path':f,'lines':len((R/f).read_text().splitlines()),'sha256':sha(R/f)} for f in updated];reading['completed_at']=now
(Q/'reading-record.json').write_text(json.dumps(reading,ensure_ascii=False,indent=2)+'\n')
report={'status':'PASS','completed_at':now,'protected_count':len(protected),'protected_changes':changed,'source_v5_preserved':True,'svg':svg,'png':png,'same_geometry_across_colors':True,'independent_native_measurement':native,'independent_svg_measurement':export,'font_license_recorded':True,'visual_checks':['Clean main preview','Complete bowl, rim level notch and foot','Actual A-F construction diagram','Black and reversed signatures','32,64,128px samples'],'measurement_checker_fix':'SVG export has separate outlines for8 letters; adjusted the checker to aggregate all letter paths rather than assume one. No art changed for this assumption.','missing_local_links':missing,'updated_markdown':updated,'zip':{'path':str(zip_path.relative_to(R)),'files':20,'sha256':sha(zip_path)},'remaining':['User visual feedback','Final-symbol similarity search','Full VI and app UI']}
(Q/'closeout-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','svg':len(svg),'png_including_reference':len(png),'protected':len(protected),'max_svg_dimension_error':export['max_dimension_error'],'zip_files':20,'missing_links':len(missing)}))
