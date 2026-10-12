"""Check the filled school form, its PDF and retained originals."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from lxml import etree as E
from PIL import Image, ImageChops
from pypdf import PdfReader
import json
import re
import shutil
import pdfplumber

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
DOCX = ROOT / 'output/submission/2026-10-11/AY26_Logsheet_No2_Group 2_YuanYuchen_250342840.docx'
PDF = DOCX.with_suffix('.pdf')
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
checks = {}

shutil.copyfile(QA / 'render-02' / PDF.name, PDF)
for kind in ('provided_template', 'previous_log'):
    source = json.loads((QA / f'{kind}-source.json').read_text())
    checks[f'{kind}_unchanged'] = sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256']
with ZipFile(QA / 'template-reference.docx') as za, ZipFile(DOCX) as zb:
    a, b = (E.fromstring(z.read('word/document.xml')) for z in (za, zb))
    checks['changed_parts'] = [n for n in za.namelist() if za.read(n) != zb.read(n)]
    ar, br = (r.xpath('//w:body/w:tbl/w:tr', namespaces=NS) for r in (a, b))
    fill = {(0, 1), (0, 3), (0, 5), (1, 1), (1, 3), (7, 1), (7, 3), (10, 2)}
    fill |= {(i, 1) for i in list(range(3, 7)) + list(range(10, 14))}
    fill |= {(i, 3) for i in range(3, 7)}
    checks['unchanged_other_cells'] = all(
        E.tostring(x) == E.tostring(y)
        for i, (xrow, yrow) in enumerate(zip(ar, br))
        for j, (x, y) in enumerate(zip(xrow.findall('w:tc', NS), yrow.findall('w:tc', NS)))
        if (i, j) not in fill
    )
    checks['school_geometry_unchanged'] = all(
        [E.tostring(n) for n in a.xpath(x, namespaces=NS)] ==
        [E.tostring(n) for n in b.xpath(x, namespaces=NS)]
        for x in ('//w:sectPr', '//w:tblPr', '//w:tblGrid', '//w:trPr', '//w:tcPr')
    )
    checks['blank_feedback'] = not br[14].findall('w:tc', NS)[1].xpath('.//w:t/text()', namespaces=NS)
    checks['no_revisions_or_controls'] = not b.xpath('//w:ins|//w:del|//w:sdt', namespaces=NS)
content = json.loads((QA / 'content.json').read_text())
reader = PdfReader(PDF)
text = '\n'.join(p.extract_text() or '' for p in reader.pages)
(QA / 'final-pdf-text.txt').write_text(text)
normalise = lambda s: re.sub(r'\s+', '', s)
required = content['work'] + content['plan'] + content['ai_purposes']
required += [content['pending'], content['other'], content['date'],
             'Yuan Yuchen / Xu Ziqian / Li Wenhua', '250342840 / 250137555 / 250329909',
             'Project ID: Group 2', 'Log Sheet No.: 2']
checks['pdf_missing_text'] = [s for s in required if normalise(s) not in normalise(text)]
checks['pdf_page_count'] = len(reader.pages)
checks['pdf_size_points'] = [float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height)]
with pdfplumber.open(PDF) as pdf:
    chars = [c for page in pdf.pages for c in page.chars if c['text'].strip()]
    checks['pdf_visible_font_sizes'] = sorted({round(c['size'], 2) for c in chars})
    checks['text_inside_page'] = all(
        0 <= c['x0'] < c['x1'] <= page.width and 0 <= c['top'] < c['bottom'] <= page.height
        for page in pdf.pages for c in page.chars if c['text'].strip()
    )
first = Image.open(QA / 'render-01/page-1.png').convert('RGB')
final = Image.open(QA / 'render-02/page-1.png').convert('RGB')
checks['visible_page_unchanged_after_blank_tail_fix'] = first.size == final.size and ImageChops.difference(first, final).getbbox() is None
checks['render_pages'] = [p.name for p in (QA / 'render-02').glob('page-*.png')]
checks['outputs'] = [
    {'path': str(p.resolve()), 'bytes': p.stat().st_size, 'sha256': sha256(p.read_bytes()).hexdigest()}
    for p in (DOCX, PDF)
]
checks['visual_review'] = {
    'image': 'render-02/page-1.png', 'pages': [1],
    'result': 'PASS: metadata, named entries and AI declaration readable; no clipping or overlaps; feedback blank.',
    'original_pages': 'Two rendered pages: one form and one blank trailing page, both inspected.',
    'iteration': 'Only the required empty paragraph after the table was reduced to 1 pt; visible form page unchanged.'
}
assert checks['provided_template_unchanged'] and checks['previous_log_unchanged']
assert checks['changed_parts'] == ['word/document.xml']
assert checks['unchanged_other_cells'] and checks['school_geometry_unchanged']
assert checks['blank_feedback'] and checks['no_revisions_or_controls']
assert checks['pdf_page_count'] == 1 and checks['render_pages'] == ['page-1.png']
assert checks['text_inside_page'] and not checks['pdf_missing_text'], checks['pdf_missing_text']
assert checks['visible_page_unchanged_after_blank_tail_fix']
(QA / 'document-validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(checks, ensure_ascii=False, indent=2))
