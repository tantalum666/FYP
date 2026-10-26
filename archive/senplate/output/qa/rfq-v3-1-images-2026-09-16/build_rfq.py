from pathlib import Path
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path('/Users/tantalum/Documents/ChatGPT/FYP')
SOURCE = ROOT / 'planning/2026-09-15/hardware-fabrication-enquiry-v3-1-images.md'
OUT = ROOT / 'output/docx/Group 2_Hardware RFQ_v3.1_Images.docx'
doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(.65)
section.bottom_margin = Inches(.65)
section.left_margin = Inches(.72)
section.right_margin = Inches(.72)
section.footer_distance = Inches(.28)
WIDTH = 8.5 - 1.44

def set_font(obj, size=None, bold=None, color='000000'):
    obj.font.name = 'Arial'
    obj.font.color.rgb = RGBColor.from_string(color)
    if size is not None: obj.font.size = Pt(size)
    if bold is not None: obj.font.bold = bold
    if hasattr(obj, '_element'):
        rpr = obj._element.get_or_add_rPr()
        rf = rpr.find(qn('w:rFonts'))
        if rf is None:
            rf = OxmlElement('w:rFonts'); rpr.insert(0, rf)
        for key in ('ascii', 'hAnsi', 'cs'): rf.set(qn('w:'+key), 'Arial')
        rf.set(qn('w:eastAsia'), 'Arial Unicode MS')
        for key in ('asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme'):
            rf.attrib.pop(qn('w:'+key), None)

for name in ('Normal','Body Text','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption'):
    sty = doc.styles[name]
    set_font(sty, 10.5)
    sty.paragraph_format.space_after = Pt(6)
    sty.paragraph_format.line_spacing = Pt(16)
    ppr = sty.element.get_or_add_pPr()
    for tag in ('w:pBdr','w:shd'):
        for e in list(ppr.findall(qn(tag))): ppr.remove(e)
doc.styles['Title'].font.size = Pt(22)
doc.styles['Title'].font.bold = True
doc.styles['Title'].paragraph_format.space_after = Pt(8)
doc.styles['Title'].paragraph_format.line_spacing = 1.1
doc.styles['Heading 1'].font.size = Pt(15.5)
doc.styles['Heading 1'].font.bold = True
doc.styles['Heading 1'].paragraph_format.space_before = Pt(6)
doc.styles['Heading 1'].paragraph_format.space_after = Pt(8)
doc.styles['Heading 1'].paragraph_format.keep_with_next = True
doc.styles['Heading 2'].font.size = Pt(11.5)
doc.styles['Heading 2'].font.bold = True
doc.styles['Heading 2'].paragraph_format.space_before = Pt(8)
doc.styles['Heading 2'].paragraph_format.space_after = Pt(5)
doc.styles['Heading 2'].paragraph_format.keep_with_next = True
doc.styles['Caption'].font.size = Pt(9)
doc.styles['Caption'].font.color.rgb = RGBColor.from_string('444444')
doc.styles['Caption'].paragraph_format.space_after = Pt(8)
doc.styles['Caption'].paragraph_format.line_spacing = 1.1

doc.core_properties.title = '食物持续监测设备硬件制作询价'
doc.core_properties.subject = 'Group 2 一台食物持续监测硬件整机制作与装配'
doc.core_properties.author = 'Group 2'
doc.core_properties.last_modified_by = 'Group 2'
doc.core_properties.comments = ''
doc.core_properties.keywords = 'Group 2, RFQ, hardware, continuous monitoring'
upd = OxmlElement('w:updateFields'); upd.set(qn('w:val'),'true'); doc.settings.element.append(upd)

footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
def field(p, code):
    r = p.add_run(); set_font(r, 8.5, color='666666')
    f = OxmlElement('w:fldSimple'); f.set(qn('w:instr'), code)
    p._p.append(f)
r = footer.add_run('Group 2  |  RFQ V3.1  |  '); set_font(r, 8.5, color='666666')
field(footer, 'PAGE')
r = footer.add_run(' / '); set_font(r, 8.5, color='666666')
field(footer, 'NUMPAGES')

TOKEN = re.compile(r'(\*\*.*?\*\*|\[[^\]]+\]\([^\)]+\))')
def inline(p, text, size=10.5, bold=False, color='000000'):
    for chunk in TOKEN.split(text):
        if not chunk: continue
        if chunk.startswith('**'):
            r=p.add_run(chunk[2:-2]); set_font(r,size,True,color)
        elif chunk.startswith('[') and '](' in chunk:
            m=re.match(r'\[([^\]]+)\]\(([^\)]+)\)',chunk)
            label,url=m.groups()
            h=OxmlElement('w:hyperlink'); h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
            r=OxmlElement('w:r'); rp=OxmlElement('w:rPr')
            rf=OxmlElement('w:rFonts'); rf.set(qn('w:ascii'),'Arial'); rf.set(qn('w:hAnsi'),'Arial'); rf.set(qn('w:eastAsia'),'Arial Unicode MS'); rp.append(rf)
            c=OxmlElement('w:color'); c.set(qn('w:val'),'1D465E'); rp.append(c)
            s=OxmlElement('w:sz'); s.set(qn('w:val'),str(int(size*2))); rp.append(s)
            r.append(rp); t=OxmlElement('w:t'); t.text=label; r.append(t); h.append(r); p._p.append(h)
        else:
            r=p.add_run(chunk); set_font(r,size,bold,color)

table_specs=[]
def table(rows):
    header=rows[0]; n=len(header)
    if n==2: ratios=[.17,.83]
    elif n==5: ratios=[.30,.075,.10,.10,.425]
    elif header[0]=='场景': ratios=[.18,.33,.49]
    elif header[0]=='项目': ratios=[.19,.49,.32]
    elif header[0]=='数据或接口': ratios=[.17,.42,.41]
    else: ratios=[.09,.48,.43]
    widths=[WIDTH*r for r in ratios]
    t=doc.add_table(rows=1,cols=n); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    pr=t._tbl.tblPr
    bd=OxmlElement('w:tblBorders')
    for name in ('top','left','bottom','right','insideH','insideV'):
        e=OxmlElement('w:'+name); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); bd.append(e)
    pr.append(bd)
    for i,w in enumerate(widths): t.columns[i].width=Inches(w)
    for rowidx,vals in enumerate(rows):
        cells=t.rows[0].cells if rowidx==0 else t.add_row().cells
        trpr=cells[0]._tc.getparent().get_or_add_trPr()
        nosplit=OxmlElement('w:cantSplit'); trpr.append(nosplit)
        if rowidx==0:
            rep=OxmlElement('w:tblHeader'); trpr.append(rep)
        for cidx,(cell,value,w) in enumerate(zip(cells,vals,widths)):
            cell.width=Inches(w); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr()
            shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'353535' if rowidx==0 else ('F7F7F7' if rowidx%2==0 else 'FFFFFF')); tcpr.append(shade)
            margins=OxmlElement('w:tcMar')
            for side,val in [('top','70'),('bottom','70'),('left','95'),('right','95')]:
                x=OxmlElement('w:'+side); x.set(qn('w:w'),val); x.set(qn('w:type'),'dxa'); margins.append(x)
            tcpr.append(margins)
            p=cell.paragraphs[0]; p.paragraph_format.space_after=Pt(0); p.paragraph_format.space_before=Pt(0); p.paragraph_format.line_spacing=Pt(14)
            p.paragraph_format.keep_with_next=False
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if rowidx==0 or (n==5 and cidx in (1,2,3)) or (header[0]=='编号' and cidx==0) else WD_ALIGN_PARAGRAPH.LEFT
            inline(p,value,9.5 if n==5 else 10,bold=rowidx==0,color='FFFFFF' if rowidx==0 else '000000')
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(3); p.paragraph_format.space_before=Pt(0); p.paragraph_format.line_spacing=1; p.add_run().font.size=Pt(1)
    table_specs.append({'rows':len(rows),'cols':n,'header':header})

lines=SOURCE.read_text().splitlines(); i=0; page=1; next_page=False
while i<len(lines):
    line=lines[i].strip()
    if not line: i+=1; continue
    if line=='<!-- pagebreak -->':
        next_page=True; page+=1; i+=1; continue
    if line=='<!-- image-pair -->':
        pairs=[]; i+=1
        while i<len(lines) and lines[i].strip()!='<!-- /image-pair -->':
            item=lines[i].strip()
            if item.startswith('!['):
                m=re.match(r'!\[([^\]]*)\]\(([^\)]+)\)',item)
                pairs.append({'alt':m.group(1),'src':m.group(2),'caption':''})
            elif item and pairs:
                pairs[-1]['caption']=item
            i+=1
        grid=doc.add_table(rows=1,cols=2); grid.alignment=WD_TABLE_ALIGNMENT.CENTER; grid.autofit=False
        for col in grid.columns: col.width=Inches(WIDTH/2)
        nosplit=OxmlElement('w:cantSplit'); grid.rows[0]._tr.get_or_add_trPr().append(nosplit)
        borders=OxmlElement('w:tblBorders')
        for edge in ('top','left','bottom','right','insideH','insideV'):
            el=OxmlElement('w:'+edge); el.set(qn('w:val'),'nil'); borders.append(el)
        grid._tbl.tblPr.append(borders)
        for cell,item in zip(grid.rows[0].cells,pairs):
            cell.width=Inches(WIDTH/2); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.TOP
            p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.line_spacing=1; p.paragraph_format.space_after=Pt(5)
            pic=p.add_run().add_picture(str(SOURCE.parent/item['src']),width=Inches(3.25)); pic._inline.docPr.set('descr',item['alt']+'。来源图片，仅用于外观参考。')
            cap=cell.add_paragraph(style='Caption'); inline(cap,item['caption'],9,color='444444'); cap.paragraph_format.keep_with_next=False
        i+=1; continue
    if line.startswith('# '):
        p=doc.add_paragraph(style='Title'); inline(p,line[2:],22,True); i+=1; continue
    if line.startswith('## '):
        p=doc.add_paragraph(style='Heading 1'); p.paragraph_format.page_break_before=next_page; next_page=False; inline(p,line[3:],15.5,True); i+=1; continue
    if line.startswith('### '):
        p=doc.add_paragraph(style='Heading 2'); inline(p,line[4:],11.5,True); i+=1; continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            values=[v.strip() for v in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[:\- ]+',v) for v in values): rows.append(values)
            i+=1
        table(rows); continue
    if line.startswith('!['):
        m=re.match(r'!\[([^\]]*)\]\(([^\)]+)\)',line); alt,src=m.groups()
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next=True; p.paragraph_format.space_after=Pt(4)
        p.paragraph_format.line_spacing=1
        pic=p.add_run().add_picture(str(SOURCE.parent/src),width=Inches(6.25))
        pic._inline.docPr.set('descr',alt+'。真实网页截图，仅用于外观参考。')
        i+=1; continue
    caption=bool(re.match(r'^图[0-9]+',line))
    p=doc.add_paragraph(style='Caption' if caption else 'Normal')
    if line.startswith('- '):
        p.paragraph_format.left_indent=Inches(.14); p.paragraph_format.first_line_indent=Inches(-.14)
        line='• '+line[2:]
    if re.match(r'^\d+\. ',line):
        p.paragraph_format.left_indent=Inches(.18); p.paragraph_format.first_line_indent=Inches(-.18)
    if line.startswith('Group 2'):
        inline(p,line,9.5,color='555555')
    else: inline(p,line,9 if caption else 10.5,color='444444' if caption else '000000')
    i+=1

OUT.parent.mkdir(parents=True,exist_ok=True)
doc.save(OUT)
import json
(ROOT/'output/qa/rfq-v3-1-images-2026-09-16/build-info.json').write_text(json.dumps({'output':str(OUT),'source':str(SOURCE),'designed_pages':page,'tables':table_specs,'images':4,'page_size':'Letter portrait','font':'Arial with Arial Unicode MS East Asian'},ensure_ascii=False,indent=2))
print(OUT)
