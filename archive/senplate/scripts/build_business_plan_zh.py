"""Build the Chinese business plan from the reviewable Markdown source."""
from pathlib import Path
import re
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'planning/2026-09-16/business-plan-zh.md'
OUT = ROOT / 'output/docx/Group 2_Senplate_商业计划书_中文版_V1.docx'
QA = ROOT / 'output/qa/2026-09-16-chinese-business-plan'
doc = Document()
s = doc.sections[0]
s.page_width = Inches(8.5)
s.page_height = Inches(11)
s.top_margin = Inches(.66)
s.bottom_margin = Inches(.65)
s.left_margin = Inches(.73)
s.right_margin = Inches(.73)
s.footer_distance = Inches(.28)
WIDTH = 7.04

def font(obj, size=None, bold=None, color='000000'):
    obj.font.name = 'Arial'
    obj.font.color.rgb = RGBColor.from_string(color)
    if size is not None:
        obj.font.size = Pt(size)
    if bold is not None:
        obj.font.bold = bold
    rp = obj._element.get_or_add_rPr()
    rf = rp.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rp.insert(0, rf)
    for attr in ('ascii', 'hAnsi', 'cs'):
        rf.set(qn('w:' + attr), 'Arial')
    rf.set(qn('w:eastAsia'), 'Arial Unicode MS')
    for attr in ('asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme'):
        rf.attrib.pop(qn('w:' + attr), None)

for name in ('Normal','Body Text','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption'):
    st = doc.styles[name]
    font(st, 11)
    pf = st.paragraph_format
    pf.space_after = Pt(8)
    pf.line_spacing = Pt(17)
    pf.widow_control = True
    ppr = st.element.get_or_add_pPr()
    for tag in ('w:pBdr','w:shd'):
        for item in list(ppr.findall(qn(tag))):
            ppr.remove(item)

font(doc.styles['Title'], 26, True)
doc.styles['Title'].paragraph_format.line_spacing = 1.2
doc.styles['Title'].paragraph_format.space_before = Pt(20)
doc.styles['Title'].paragraph_format.space_after = Pt(18)
font(doc.styles['Subtitle'], 12.5)
doc.styles['Subtitle'].paragraph_format.line_spacing = 1.25
font(doc.styles['Heading 1'], 18, True)
doc.styles['Heading 1'].paragraph_format.line_spacing = 1.2
doc.styles['Heading 1'].paragraph_format.space_after = Pt(14)
doc.styles['Heading 1'].paragraph_format.keep_with_next = True
font(doc.styles['Heading 2'], 12.5, True)
doc.styles['Heading 2'].paragraph_format.space_before = Pt(8)
doc.styles['Heading 2'].paragraph_format.space_after = Pt(7)
doc.styles['Heading 2'].paragraph_format.keep_with_next = True

doc.core_properties.title = 'Senplate 食物与营养监测系统商业计划书'
doc.core_properties.subject = 'Group 2 中文商业计划书 机构供餐 学校配餐与成年个人餐食记录'
doc.core_properties.author = 'Group 2'
doc.core_properties.last_modified_by = 'Group 2'
doc.core_properties.keywords = 'Group 2, 商业计划书, 食物监测, 补餐, 营养记录'
doc.core_properties.comments = ''

footer = s.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
footer.paragraph_format.space_after = Pt(0)
rr = footer.add_run('Group 2  |  商业计划书  |  ')
font(rr, 8.5, color='555555')
for instr, tail in [('PAGE', ' / '), ('NUMPAGES', '')]:
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), instr)
    footer._p.append(fld)
    rr = footer.add_run(tail)
    font(rr, 8.5, color='555555')

TOKEN = re.compile(r'(\*\*.*?\*\*|\[[^\]]+\]\([^\)]+\))')
def inline(p, text, size=None, bold=False, color='000000'):
    for chunk in TOKEN.split(text):
        if not chunk:
            continue
        if chunk.startswith('**'):
            font(p.add_run(chunk[2:-2]), size, True, color)
        elif chunk.startswith('[') and '](' in chunk:
            label, url = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', chunk).groups()
            h = OxmlElement('w:hyperlink')
            h.set(qn('r:id'), p.part.relate_to(url, RT.HYPERLINK, is_external=True))
            rr = OxmlElement('w:r')
            rp = OxmlElement('w:rPr')
            ff = OxmlElement('w:rFonts')
            ff.set(qn('w:ascii'), 'Arial')
            ff.set(qn('w:hAnsi'), 'Arial')
            ff.set(qn('w:eastAsia'), 'Arial Unicode MS')
            rp.append(ff)
            cc = OxmlElement('w:color'); cc.set(qn('w:val'), '245269'); rp.append(cc)
            zz = OxmlElement('w:sz'); zz.set(qn('w:val'),str(round((size or 11)*2))); rp.append(zz)
            rr.append(rp)
            tt = OxmlElement('w:t'); tt.text = label; rr.append(tt)
            h.append(rr); p._p.append(h)
        else:
            font(p.add_run(chunk), size, bold, color)

specs = []
def add_table(rows):
    header = rows[0]
    n = len(header)
    ratios = {
        '商业要素': [.18,.82],
        '客户分组': [.20,.38,.42],
        '同一核心的配置': [.16,.43,.41],
        '组成': [.22,.39,.39],
        '替代方案': [.20,.40,.40],
        '阶段或项目': [.22,.22,.56],
        '环节': [.16,.44,.40],
        '指标': [.19,.36,.45],
        '阶段': [.17,.45,.38],
        '成员': [.24,.16,.60],
        '单盘位交付项目': [.73,.27],
        '客户情景': [.16,.23,.17,.27,.17],
        '项目 HKD 另有注明除外': [.40,.20,.20,.20],
        '用途': [.36,.19,.45],
        '关键风险': [.27,.24,.49],
        '变化条件': [.40,.23,.37],
        '假设': [.30,.30,.40],
    }.get(header[0], [1/n]*n)
    assert len(ratios) == n
    widths = [WIDTH*r for r in ratios]
    t = doc.add_table(rows=1, cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    borders = OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        e = OxmlElement('w:'+edge)
        e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9')
        borders.append(e)
    t._tbl.tblPr.append(borders)
    for col,w in zip(t.columns,widths): col.width = Inches(w)
    numeric_table = header[0] in ('单盘位交付项目','客户情景','项目 HKD 另有注明除外')
    for ridx, vals in enumerate(rows):
        assert len(vals) == n, vals
        cells = t.rows[0].cells if ridx == 0 else t.add_row().cells
        trp = cells[0]._tc.getparent().get_or_add_trPr()
        trp.append(OxmlElement('w:cantSplit'))
        if ridx == 0: trp.append(OxmlElement('w:tblHeader'))
        for cidx,(c,v,w) in enumerate(zip(cells,vals,widths)):
            c.width = Inches(w)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = c._tc.get_or_add_tcPr()
            shade=OxmlElement('w:shd')
            shade.set(qn('w:fill'), '244956' if ridx == 0 else ('F2F6F7' if ridx%2==0 else 'FFFFFF'))
            pr.append(shade)
            pad=OxmlElement('w:tcMar')
            for edge,val in [('top',65),('bottom',65),('left',100),('right',100)]:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),str(val));e.set(qn('w:type'),'dxa');pad.append(e)
            pr.append(pad)
            p=c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = Pt(14.2)
            p.paragraph_format.keep_with_next = False
            if ridx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif numeric_table and cidx > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif (header[0] in ('成员','用途','变化条件','阶段或项目') and cidx==1):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            inline(p,v,10.3,ridx==0,'FFFFFF' if ridx==0 else '000000')
    spacer=doc.add_paragraph()
    spacer.paragraph_format.space_after=Pt(3)
    spacer.paragraph_format.space_before=Pt(0)
    spacer.paragraph_format.line_spacing=Pt(2)
    font(spacer.add_run(''),2)
    specs.append({'rows':len(rows),'columns':n,'header':header,'width_ratios':ratios})

lines = SOURCE.read_text().splitlines()
i = 0
page = 1
next_page = False
while i < len(lines):
    line=lines[i].strip()
    if not line:
        i+=1;continue
    if line=='<!-- pagebreak -->':
        page+=1;next_page=True;i+=1;continue
    if line.startswith('# '):
        p=doc.add_paragraph(style='Title')
        inline(p,'Senplate 食物与营养监测系统\n商业计划书',26,True)
    elif line.startswith('## '):
        p=doc.add_paragraph(style='Heading 1')
        p.paragraph_format.page_break_before=next_page;next_page=False
        inline(p,line[3:],18,True)
    elif line.startswith('### '):
        p=doc.add_paragraph(style='Heading 2');inline(p,line[4:],12.5,True)
    elif line.startswith('|'):
        rows=[]
        while i < len(lines) and lines[i].strip().startswith('|'):
            vals=[v.strip() for v in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[-: ]+',v) for v in vals):rows.append(vals)
            i+=1
        add_table(rows)
        continue
    else:
        p=doc.add_paragraph()
        if page==1 and line.startswith('Group 2'):
            p.paragraph_format.space_after=Pt(12);inline(p,line,10.5)
        elif page==1 and line.startswith('AI and'):
            p.paragraph_format.space_after=Pt(16);inline(p,line,11.5)
        elif page==1 and line.startswith('面向'):
            p.paragraph_format.space_after=Pt(16);inline(p,line,13,True)
        elif page==1 and line.startswith('阅读导航'):
            p.paragraph_format.space_before=Pt(10);inline(p,line,9.5,color='444444')
        else:
            inline(p,line,11)
    i+=1

OUT.parent.mkdir(parents=True,exist_ok=True)
QA.mkdir(parents=True,exist_ok=True)
doc.save(OUT)
(QA/'build-info.json').write_text(json.dumps({'source':str(SOURCE),'output':str(OUT),'designed_pages':page,'tables':specs,'font':'Arial and Arial Unicode MS','page_size':'Letter portrait'},ensure_ascii=False,indent=2))
print(str(OUT))
print(f'Designed pages: {page}; tables: {len(specs)}')
