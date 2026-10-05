from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, zipfile
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path('/Users/tantalum/Documents/ChatGPT/FYP')
ASSETS = ROOT / 'output/brand/2026-09-17-senplate-selected-a'
QA = ROOT / 'output/qa/senplate-selected-a-2026-09-17'
UPDATED = ['brand.md', 'README.md', 'product.md', 'handoff.md', 'decision-log.md', 'work-log.md', 'Senplate_Logo_ImageGen_Brief.md', 'planning/2026-09-17/senplate-logo-measured-plate-r5.md', 'planning/2026-09-16/software-scope-and-architecture.md', 'planning/2026-09-16/software-mvp-and-acceptance.md', 'planning/2026-09-16/logo-reference-calibration.md', 'output/brand/2026-09-17-senplate-selected-a/README.md']
NOW = datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

source = Path('/Users/tantalum/Downloads/ChatGPT Image 2026年9月17日 11_43_29.png')
expected_source = 'cc98804614d8e0de4e15d1e5dd197550f3bef06a4569cc5c4c3b9f54e2929a61'
assert sha(source) == sha(ASSETS / 'source-selected-a.png') == expected_source

protected = json.loads((QA / 'protected-before.json').read_text())
changed_protected = [x['path'] for x in protected if not (ROOT / x['path']).exists() or sha(ROOT / x['path']) != x['sha256']]
assert not changed_protected, changed_protected

svg_checks = []
for path in sorted(ASSETS.glob('*.svg')):
    node = ET.fromstring(path.read_text())
    tags = [x.tag.rsplit('}', 1)[-1] for x in node.iter()]
    assert 'image' not in tags and 'text' not in tags and 'script' not in tags
    paths = node.findall('.//{http://www.w3.org/2000/svg}path')
    count = 8 if 'wordmark' in path.name else 3 if '-mark-' in path.name else 11
    assert len(paths) == count, (path.name, len(paths), count)
    assert all('C' in x.attrib['d'] for x in paths)
    svg_checks.append({'name': path.name, 'viewBox': node.attrib['viewBox'], 'path_count': len(paths), 'external_fonts_or_images': False})
for kind in ['logo', 'mark']:
    green = (ASSETS / f'senplate-{kind}-green.svg').read_text()
    for color_name, color in [('black', '#000000'), ('white', '#FFFFFF')]:
        assert (ASSETS / f'senplate-{kind}-{color_name}.svg').read_text() == green.replace('#163F35', color)

nodes = {'senplate-logo-green.png':'41:2', 'senplate-logo-black.png':'43:27', 'senplate-logo-white.png':'43:52', 'senplate-mark-green.png':'43:77', 'senplate-mark-black.png':'46:2', 'senplate-mark-white.png':'46:9', 'app-icon-forest-1024.png':'44:2', 'app-icon-ivory-1024.png':'44:10', 'app-icon-black-1024.png':'44:18', 'senplate-mark-24.png':'46:16', 'senplate-mark-32.png':'46:24', 'senplate-mark-64.png':'46:32', 'brand-preview.png':'36:6'}
png_checks = []
for path in sorted(ASSETS.glob('*.png')):
    with Image.open(path) as im:
        im.load()
        rgba = im.convert('RGBA')
        alpha = rgba.getchannel('A').getextrema()
        entry = {'name':path.name, 'width':im.width, 'height':im.height, 'alpha_extrema':list(alpha), 'sha256':sha(path)}
        if path.name.startswith('app-icon-'):
            assert im.size == (1024, 1024) and alpha == (255, 255)
            entry['corner_rgb'] = list(rgba.getpixel((0, 0))[:3])
            color = (22,63,53) if 'forest' in path.name else (243,241,231) if 'ivory' in path.name else (0,0,0)
            assert rgba.getpixel((0,0))[:3] == color
        elif path.name.startswith('senplate-logo-'):
            assert im.size == (1600, 265) and alpha == (0, 255)
        elif path.name.startswith('senplate-mark-'):
            last = path.stem.split('-')[-1]
            size = (int(last), int(last)) if last.isnumeric() else (512,268)
            assert im.size == size and alpha[0] == 0
        elif path.name == 'brand-preview.png':
            assert im.size == (1440,1100)
        elif path.name == 'source-selected-a.png':
            assert im.size == (1536,1024)
        png_checks.append(entry)
assert len(svg_checks) == 7 and len(png_checks) == 14

manifest = {
    'brand':'Senplate', 'asset_version':'1.0', 'status':'USER_SELECTED_A_NORMALIZED', 'updated_at':NOW,
    'user_decision':'用这个吧',
    'source':{'filename':source.name, 'project_copy':'source-selected-a.png', 'sha256':expected_source, 'canonical_region':'Upper large green horizontal lockup'},
    'palette':{'forest':'#163F35', 'ivory':'#F3F1E7', 'black':'#000000', 'white':'#FFFFFF'},
    'method':'Source silhouette extraction, edge denoising and cubic path fitting; independent letter paths preserve the selected wordmark. PNGs rendered natively by Figma; source PNG unchanged.',
    'font':{'type':'outlined from selected image', 'family':None, 'substitution':False},
    'figma':{'url':'https://www.figma.com/design/UyYjnTFGWO0r1lj4uvghGp?node-id=36-6', 'file_key':'UyYjnTFGWO0r1lj4uvghGp', 'board':'36:6', 'logo_master':'41:2', 'mark_master':'43:77', 'png_nodes':nodes},
    'svg_checks':svg_checks, 'png_checks':png_checks,
    'usage':{'default_icon':'app-icon-forest-1024.png', 'symbol_min_width_recommendation_px':32, 'preferred_width_px':48, 'small_size_note':'24px rim is too thin for regular use; 32 and 64px visually reviewed.', 'app_icon_sources':'Square opaque PNGs; rounded corners on preview only.'},
    'status_limits':['New symbol has not received a fresh trademark similarity search.', 'Original font family and licensing provenance not identified.', 'Not implemented in an app or deployed.', 'Source board copy and tagline are not approved product copy.'],
    'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(ASSETS.iterdir()) if p.is_file() and p.name != 'manifest.json']
}
(ASSETS / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
archive = ROOT / 'output/brand/Senplate_Brand_Assets_v1.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted(ASSETS.iterdir()):
        if path.is_file() and (path.suffix in ['.svg','.png'] or path.name in ['README.md','manifest.json']):
            z.write(path, 'Senplate_Brand_Assets_v1/'+path.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == 23

report_path = QA / 'closeout-validation.json'
report_path.write_text('{}\n')
missing = []
for relative in UPDATED:
    path = ROOT / relative
    for raw in re.findall(r'!?\[[^\]]*\]\((<[^>]+>|[^)]+)\)', path.read_text()):
        target = raw[1:-1] if raw.startswith('<') else raw
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        target = target.split('#',1)[0]
        if target and not (path.parent / target).exists():
            missing.append({'file':relative,'target':target})
assert not missing, missing

record_path = QA / 'reading-record.json'
record = json.loads(record_path.read_text())
record['compaction_recovery'] = {'AGENTS.md':'full','product.md':'full with end range re-read','handoff.md':'full','decision-log.md':'latest R5 entries plus authored A entry','work-log.md':'latest R5 entries plus authored A entry','README.md':'full','Senplate_Logo_ImageGen_Brief.md':'full','planning/2026-09-17/senplate-logo-measured-plate-r5.md':'full','planning/2026-09-16/logo-reference-calibration.md':'full','planning/2026-09-16/software-scope-and-architecture.md':'1-16 plus inherited full body','planning/2026-09-16/software-mvp-and-acceptance.md':'1-8 and 90-EOF plus inherited full body'}
record['new_authored_files'] = ['brand.md', 'output/brand/2026-09-17-senplate-selected-a/README.md']
record['updated_files'] = [{'path':r,'lines':len((ROOT/r).read_text().splitlines()),'sha256':sha(ROOT/r)} for r in UPDATED]
record['completed_at'] = NOW
record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
report = {'completed_at':NOW, 'status':'PASS', 'source_original_and_copy_match':True, 'source_sha256':expected_source, 'protected_files_count':len(protected), 'protected_files_changed':changed_protected, 'svg_count':len(svg_checks), 'png_count_including_original':len(png_checks), 'svg_geometry_identical_across_colors':True, 'png_checks':png_checks, 'svg_checks':svg_checks, 'visual_review':['final brand board with green, black, white and app icons','24px symbol: thin rim, excluded from regular size recommendation','32px and 64px symbols'], 'missing_local_links':missing, 'updated_markdown':UPDATED, 'zip':{'path':str(archive.relative_to(ROOT)),'files':23,'bytes':archive.stat().st_size,'sha256':sha(archive)}, 'resolved_process_issues':['Noisy initial trace cleaned before delivery.','Compound glyph import lost letters; independent letter paths used.','Image blocks limited to 5 per call; 8 remaining PNGs exported in two batches.','One combined patch rejected duplicate handoff operation without applying; split writes completed.'], 'remaining':['Fresh similarity search for selected A','Original font provenance','UI page design and implementation'], 'not_done':['Trademark registration','External contact','App coding','Hardware validation','Publication']}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','svg':len(svg_checks),'png_including_original':len(png_checks),'protected':len(protected),'links_missing':len(missing),'zip_files':23,'zip_bytes':archive.stat().st_size},ensure_ascii=False))
