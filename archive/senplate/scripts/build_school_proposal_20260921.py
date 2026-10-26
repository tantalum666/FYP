"""Build the school proposal from its editable English source using bundled dependencies."""
from pathlib import Path
import re
import subprocess
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "planning/2026-09-21/proposal-content.md"
OUT = ROOT / "output/docx/AY26_ProjectProposal_Group 2.docx"
ASSETS = SOURCE.parent
NODE = "/Users/tantalum/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
SHARP = "/Users/tantalum/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp"


def diagram():
    shapes = []
    def box(x, y, text, width=300, height=100):
        shapes.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#F4F4F4" stroke="#545454" stroke-width="2"/>')
        for i, line in enumerate(text):
            ty = y + height / 2 + (i - (len(text)-1)/2) * 31 + 8
            shapes.append(f'<text x="{x+width/2}" y="{ty}" text-anchor="middle" font-family="Arial,sans-serif" font-size="26" fill="#111111">{escape(line)}</text>')
    for x, lines in [(30,["One pan or plate","Load cell and RGB-D"]),(390,["Raspberry Pi 5","Acquisition and vision"]),(750,["Shared services","FastAPI + PostgreSQL"])]:
        box(x,30,lines)
    for x, lines in [(30,["Station touchscreen"]),(390,["Kitchen and","management web"]),(750,["iPhone app","Personal and work roles"])]:
        box(x,230,lines)
    for x1,x2 in [(330,385),(690,745)]:
        shapes.append(f'<path d="M{x1} 80 H{x2}" stroke="#222222" stroke-width="3" fill="none" marker-end="url(#arrow)"/>')
    shapes.append('<path d="M900 138 V190 H180" stroke="#222222" stroke-width="3" fill="none"/>')
    for x in [180,540,900]:
        shapes.append(f'<path d="M{x} 192 V222" stroke="#222222" stroke-width="3" fill="none" marker-end="url(#arrow)"/>')
    shapes.append('<text x="525" y="174" text-anchor="middle" font-family="Arial,sans-serif" font-size="22" fill="#333333">State updates and authorised actions</text>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="355" viewBox="0 0 1080 355"><rect width="1080" height="355" fill="white"/><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="#222222"/></marker></defs>' + ''.join(shapes) + '</svg>'
    (ASSETS/'architecture.svg').write_text(svg)
    javascript = f"const sharp=require({str(SHARP)!r}); sharp(process.argv[1],{{density:240}}).png().toFile(process.argv[2]);"
    subprocess.run([NODE,'-e',javascript,str(ASSETS/'architecture.svg'),str(ASSETS/'architecture.png')],check=True)


def font(run, size=None, bold=False):
    run.font.name = 'Times New Roman'
    run.font.color.rgb = RGBColor(0,0,0)
    if size is not None:
        run.font.size = Pt(size)
    run.bold = bold
    rpr=run._element.get_or_add_rPr()
    rf=rpr.rFonts
    if rf is not None:
        rf.set(qn('w:ascii'),'Times New Roman');rf.set(qn('w:hAnsi'),'Times New Roman')


def hyperlink(paragraph, text, url):
    link=OxmlElement('w:hyperlink')
    link.set(qn('r:id'),paragraph.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    colour=OxmlElement('w:color');colour.set(qn('w:val'),'000000');pr.append(colour)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u)
    r.append(pr);t=OxmlElement('w:t');t.text=text;r.append(t);link.append(r);paragraph._p.append(link)


def inline(paragraph, text, size=None):
    for part in re.split(r'(\*\*.+?\*\*|\[[^\]]+\]\(https?://[^)]+\))',text):
        if not part:
            continue
        match=re.fullmatch(r'\[([^\]]+)\]\((https?://[^)]+)\)',part)
        if match:
            hyperlink(paragraph,match.group(1),match.group(2))
        else:
            bold=part.startswith('**') and part.endswith('**')
            run=paragraph.add_run(part[2:-2] if bold else part)
            font(run,size,bold)


def cell_shade(cell, fill):
    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),fill);cell._tc.get_or_add_tcPr().append(shade)


def make_table(doc, rows, widths=None, size=10.6):
    n=len(rows[0]);table=doc.add_table(rows=0,cols=n)
    table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
    total=6.52
    if widths is None:
        widths=([1.43,2.05,3.04] if n==3 else [0.43,1.35,4.74] if n==3 else [total/n]*n)
    if rows[0][0]=='ID': widths=[0.43,1.37,4.72]
    elif rows[0][0]=='Area':widths=[1.10,2.86,2.56]
    elif rows[0][0]=='Member and share':widths=[1.22,1.55,3.75]
    elif rows[0][0]=='Main risk':widths=[1.56,4.96]
    elif rows[0][0]=='Stage':widths=[1.52,1.47,3.53]
    elif rows[0][0]=='Reference':widths=[1.24,2.53,2.75]
    elif rows[0][0]=='Component':widths=[1.14,2.02,3.36]
    elif rows[0][0]=='Environment':widths=[1.47,1.71,3.34]
    for col,width in zip(table.columns,widths):col.width=Inches(width)
    borders=OxmlElement('w:tblBorders')
    for key in ['top','left','bottom','right','insideH','insideV']:
        edge=OxmlElement('w:'+key);edge.set(qn('w:val'),'single');edge.set(qn('w:sz'),'4');edge.set(qn('w:color'),'D9D9D9');borders.append(edge)
    table._tbl.tblPr.append(borders)
    for index, values in enumerate(rows):
        row=table.add_row()
        trpr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trpr.append(cant)
        if index==0:
            repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
        for ci,(cell,value,width) in enumerate(zip(row.cells,values,widths)):
            cell.width=Inches(width);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr();margins=OxmlElement('w:tcMar')
            for side,twips in [('top',85),('bottom',85),('left',105),('right',105)]:
                edge=OxmlElement('w:'+side);edge.set(qn('w:w'),str(twips));edge.set(qn('w:type'),'dxa');margins.append(edge)
            tcpr.append(margins)
            if index==0:cell_shade(cell,'E7E7E7')
            elif index%2==0:cell_shade(cell,'F7F7F7')
            p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=1.04
            if (rows[0][0]=='ID' and ci==0) or (rows[0][0]=='Member and share' and ci==0):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            inline(p,value.replace('\\n','\n'),size)
            if index==0:
                for r in p.runs:r.bold=True
    after=doc.add_paragraph();after.paragraph_format.space_after=Pt(2);after.paragraph_format.space_before=Pt(0);after.paragraph_format.line_spacing=0.4
    return table


def setup():
    doc=Document();section=doc.sections[0]
    section.page_width=Mm(210);section.page_height=Mm(297)
    section.top_margin=Mm(17);section.bottom_margin=Mm(17)
    section.left_margin=Mm(22);section.right_margin=Mm(22)
    section.header_distance=Mm(7);section.footer_distance=Mm(8)
    styles=doc.styles
    for s in styles:
        for border in list(s._element.iter(qn('w:pBdr'))):
            border.getparent().remove(border)
    for key in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption','List Bullet','List Number']:
        s=styles[key];s.font.name='Times New Roman';s.font.color.rgb=RGBColor(0,0,0)
        rf=s._element.get_or_add_rPr().rFonts
        for attribute in list(rf.attrib):
            if 'theme' in attribute.lower():del rf.attrib[attribute]
        for attribute in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+attribute),'Times New Roman')
        s.paragraph_format.widow_control=True
    normal=styles['Normal'];normal.font.size=Pt(11.5);normal.paragraph_format.line_spacing=1.08;normal.paragraph_format.space_after=Pt(6)
    for name,size,before,after in [('Title',21,0,6),('Subtitle',13,0,9),('Heading 1',14,4,8),('Heading 2',12,8,5)]:
        s=styles[name];s.font.size=Pt(size);s.font.bold=True;s.paragraph_format.space_before=Pt(before);s.paragraph_format.space_after=Pt(after);s.paragraph_format.keep_with_next=True
    styles['Caption'].font.size=Pt(10.2);styles['Caption'].font.italic=True;styles['Caption'].font.bold=False
    styles['Subtitle'].font.italic=False
    for name in ['List Bullet','List Number']:
        styles[name].font.size=Pt(11.5);styles[name].paragraph_format.space_after=Pt(4);styles[name].paragraph_format.line_spacing=1.06
    footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    font(footer.add_run('Group 2  |  Senplate  |  '),9)
    for code in ['PAGE','NUMPAGES']:
        if code=='NUMPAGES':font(footer.add_run(' of '),9)
        field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),code);footer._p.append(field)
    doc.core_properties.title='Senplate Project Proposal'
    doc.core_properties.subject='ITE4116M Final Year Project AY26'
    doc.core_properties.author='Group 2 - Yuan Yuchen, Xu Ziqian, Li Wenhua'
    doc.core_properties.keywords='Senplate, food monitoring, IoT, Group 2, ITE4116M'
    return doc


def identity(doc):
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(6)
    inline(p,'Programme: Higher Diploma in AI and Smart Technology (IT114124)',11)
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(6)
    inline(p,'Class: AIST-2B    Group 2    Supervisor: Marco',11)
    make_table(doc,[['Student name','Student ID','Planned contribution'],['Yuan Yuchen (Group Leader)','250342840','40%'],['Xu Ziqian','250137555','30%'],['Li Wenhua','250329909','30%']],[3.0,1.65,1.87],10.7)


def signatures(doc):
    rows=[['Signatory','Signature','Date'],['Yuan Yuchen','', ''],['Xu Ziqian','',''],['Li Wenhua','',''],['Supervisor','',''],['Second reader','',''],['External body if applicable','','']]
    table=make_table(doc,rows,[2.52,2.5,1.5],10)
    for row in table.rows[1:]:
        row.height=Mm(9);row.height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST


def new_numbering(doc):
    numbering=doc.part.numbering_part.element
    aid=max([int(n.get(qn('w:abstractNumId'))) for n in numbering.findall(qn('w:abstractNum'))]+[-1])+1
    abstract=OxmlElement('w:abstractNum');abstract.set(qn('w:abstractNumId'),str(aid))
    level=OxmlElement('w:lvl');level.set(qn('w:ilvl'),'0')
    for tag,value in [('start','1'),('numFmt','decimal'),('lvlText','%1.'),('lvlJc','left')]:
        child=OxmlElement('w:'+tag);child.set(qn('w:val'),value);level.append(child)
    pp=OxmlElement('w:pPr');indent=OxmlElement('w:ind');indent.set(qn('w:left'),'360');indent.set(qn('w:hanging'),'360');pp.append(indent);level.append(pp)
    abstract.append(level);numbering.append(abstract)
    nid=max([int(n.get(qn('w:numId'))) for n in numbering.findall(qn('w:num'))]+[0])+1
    num=OxmlElement('w:num');num.set(qn('w:numId'),str(nid))
    ref=OxmlElement('w:abstractNumId');ref.set(qn('w:val'),str(aid));num.append(ref);numbering.append(num)
    return nid


def build():
    diagram();doc=setup()
    for text in ['Hong Kong Institute of Information Technology','Discipline of Information Technology','Final Year Project Systems Development and Administration','ITE4116M   Academic Year 2026/27']:
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(3);font(p.add_run(text),11,text!='ITE4116M   Academic Year 2026/27')
    source=SOURCE.read_text().splitlines();i=0;page=1;list_id=None
    while i<len(source):
        line=source[i].strip()
        if not line:i+=1;continue
        if line=='<!-- pagebreak -->':doc.add_page_break();page+=1;i+=1;continue
        if line=='<!-- identity -->':identity(doc);i+=1;continue
        if line=='<!-- signatures -->':signatures(doc);i+=1;continue
        if line=='<!-- comment-space -->':
            p=doc.add_paragraph();p.paragraph_format.space_after=Pt(15);p.paragraph_format.line_spacing=1;i+=1;continue
        if line.startswith('# '):
            p=doc.add_paragraph(line[2:],style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;i+=1;continue
        if page==1 and line=='AI and IoT Based Food and Nutrition Monitoring System':
            p=doc.add_paragraph(line,style='Subtitle');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;font(p.add_run('Version 1.0    21 September 2026'),9.5);p.paragraph_format.space_after=Pt(8)
            i+=1;continue
        if line.startswith('## '):doc.add_paragraph(line[3:],style='Heading 1');i+=1;continue
        if line.startswith('### '):doc.add_paragraph(line[4:],style='Heading 2');i+=1;continue
        if line.startswith('!['):
            p=doc.add_paragraph();p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1
            image=p.add_run().add_picture(str(ASSETS/'architecture.png'),width=Inches(6.42))
            image._inline.docPr.set('descr','A pan with weight and RGB-D feeds Pi acquisition and shared services, which exchange state and authorised actions with station, kitchen web and iPhone clients.')
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(source) and source[i].strip().startswith('|'):
                values=[v.strip() for v in source[i].strip().strip('|').split('|')]
                if not all(re.fullmatch('[-: ]+',v) for v in values):rows.append(values)
                i+=1
            make_table(doc,rows);continue
        if line.startswith('*Figure'):
            p=doc.add_paragraph(line.strip('*'),style='Caption');i+=1;continue
        number=re.match(r'^(\d+)\. (.+)',line)
        if number:
            if number.group(1)=='1' or list_id is None:list_id=new_numbering(doc)
            p=doc.add_paragraph(style='List Number');np=OxmlElement('w:numPr')
            level=OxmlElement('w:ilvl');level.set(qn('w:val'),'0');np.append(level)
            nid=OxmlElement('w:numId');nid.set(qn('w:val'),str(list_id));np.append(nid);p._p.get_or_add_pPr().append(np)
            inline(p,number.group(2));i+=1;continue
        p=doc.add_paragraph()
        if page==10:
            p.paragraph_format.space_after=Pt(4);p.paragraph_format.line_spacing=1.02
            inline(p,line,10.3)
        else:inline(p,line)
        i+=1
    OUT.parent.mkdir(parents=True,exist_ok=True);doc.save(OUT)
    print(OUT)
    print('Content words:',len(re.findall(r"\b[\w'-]+\b",SOURCE.read_text())))


if __name__=='__main__':build()
