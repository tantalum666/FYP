"""Render the revised bilingual proposal using the established academic layout."""
from pathlib import Path
import argparse,re
from docx import Document
from docx.shared import Inches,Pt
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT,WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import build_desk_companion_proposal_zh_20260925 as base

ROOT=Path(__file__).resolve().parents[1]

def diagram(lang):
    from PIL import Image,ImageDraw,ImageFont
    import math
    image=Image.new('RGB',(2240,900),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype(str(ROOT/'output/qa/new-proposal-zh-2026-09-25/fonts/NotoSerifCJKsc-Regular.otf'),37)
    labels=(['固定摄像头\n关键点与持续判断','本地日历和SQLite\n事项与提醒状态','本地反馈控制\n校验动作并记录结果','云端Qwen语音\n主机管理音频会话','屏幕、角色与灯光\n计划中的轻载机械臂'] if lang=='zh' else ['Fixed camera\nLandmarks and temporal logic','Local calendar and SQLite\nEvents and reminder state','Local feedback controller\nValidate actions and log results','Qwen cloud voice\nHost manages audio session','Screen, character and lights\nPlanned lightweight arm'])
    pos=[(60,50),(60,435),(800,250),(1540,50),(1540,435)]
    for label,(x,y) in zip(labels,pos):
        draw.rounded_rectangle((x,y,x+600,y+190),radius=12,fill='#F5F7F8',outline='#59636D',width=3)
        draw.multiline_text((x+300,y+95),label,font=font,fill='#202830',anchor='mm',align='center',spacing=12)
    def arrow(a,b):
        draw.line((a,b),fill='#35434D',width=4);angle=math.atan2(b[1]-a[1],b[0]-a[0])
        pts=[b,(b[0]-22*math.cos(angle-.45),b[1]-22*math.sin(angle-.45)),(b[0]-22*math.cos(angle+.45),b[1]-22*math.sin(angle+.45))]
        draw.polygon(pts,fill='#35434D')
    for a,b in [((660,145),(790,315)),((660,530),(790,365)),((1530,145),(1410,315)),((1410,365),(1530,530))]:arrow(a,b)
    loop=[(1840,635),(1840,760),(20,760),(20,145),(50,145)]
    for a,b in zip(loop,loop[1:]):
        length=math.dist(a,b)
        for start in range(0,int(length),24):
            end=min(start+13,length);s=(a[0]+(b[0]-a[0])*start/length,a[1]+(b[1]-a[1])*start/length);e=(a[0]+(b[0]-a[0])*end/length,a[1]+(b[1]-a[1])*end/length);draw.line((s,e),fill='#59636D',width=3)
    arrow((35,145),(55,145))
    draw.text((1120,825),'用户调整后重新观察' if lang=='zh' else 'Observe again after the user responds',font=font,fill='#35434D',anchor='mm')
    path=ROOT/f'planning/2026-09-28/architecture-{lang}.png'
    image.save(path,dpi=(300,300))
    return path

def table(doc,rows):
    cols=len(rows[0]);headers=' '.join(rows[0])
    if cols==4:w=[1.35,.94,2.65,.83]
    elif any(x in headers for x in ('Work period','工作期')):w=[1.13,2.94,1.70]
    elif any(x in headers for x in ('Target','目标与')):w=[.97,3.12,1.68]
    elif any(x in headers for x in ('Component','部件')):w=[1.2,1.87,2.70]
    else:w=[1.28,1.57,2.92] if cols==3 else [1.4,4.37]
    t=doc.add_table(rows=0,cols=cols);t.autofit=False;t.alignment=WD_TABLE_ALIGNMENT.CENTER;base.set_borders(t)
    for j,width in enumerate(w):t.columns[j].width=Inches(width)
    for ri,values in enumerate(rows):
        row=t.add_row();trpr=row._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
        if ri==0:base.set_repeat_header(row)
        for ci,value in enumerate(values):
            c=row.cells[ci];c.width=Inches(w[ci]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            base.set_cell_margins(c,top=80,bottom=80,start=90,end=90)
            if ri==0:base.set_cell_shading(c,'E9EEF2')
            p=c.paragraphs[0];p.style='Table Text'
            base.add_inline(p,value,size=10.5)
            if cols==4 and ci in(1,3):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if ri==0:
                for r in p.runs:r.bold=True
    doc.add_paragraph().paragraph_format.space_after=Pt(0)

def build(lang):
    base.FONT_LATIN='Times New Roman' if lang=='en' else 'Noto Serif CJK SC'
    source=ROOT/('planning/2026-09-28/desk-companion-proposal-en.md' if lang=='en' else 'planning/2026-09-28/desk-companion-proposal-zh-v3.md')
    dest=ROOT/('output/submission/2026-09-28/AY26_ProjectProposal_Group 2.docx' if lang=='en' else 'output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review_v3.docx')
    doc=Document();base.configure_section(doc.sections[0])
    for name,size,bold,after in [('Normal',12,False,6),('Title',20,True,13),('Heading 1',15,True,8),('Heading 2',12.5,True,6)]:
        base.configure_style(doc.styles[name],size,bold=bold,after=after,line=1.0 if name=='Normal' else 1.12)
    from docx.enum.style import WD_STYLE_TYPE
    if 'Table Text' not in doc.styles:doc.styles.add_style('Table Text',WD_STYLE_TYPE.PARAGRAPH)
    base.configure_style(doc.styles['Table Text'],10.5,line=1.05)
    lines=source.read_text().splitlines();i=0;cover=True;refs=False
    while i<len(lines):
        v=lines[i].strip();i+=1
        if not v:continue
        if v=='<!-- body -->':
            sec=doc.add_section(WD_SECTION.NEW_PAGE);base.configure_section(sec);sec.footer.is_linked_to_previous=False;base.add_page_field(sec.footer.paragraphs[0])
            pg=OxmlElement('w:pgNumType');pg.set(qn('w:start'),'1');sec._sectPr.append(pg);cover=False;continue
        if v.startswith('# '):
            title=v[2:].replace(' AI ','\nAI ') if lang=='zh' else v[2:]
            p=doc.add_paragraph(style='Title');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;base.add_inline(p,title,size=20);continue
        if v.startswith('## '):
            title=v[3:];refs=title.startswith('9 ')
            p=doc.add_paragraph(style='Heading 1')
            page_sections=r'^[23569] ' if lang=='zh' else r'^[23568] '
            if re.match(page_sections,title) or title.startswith(('导师与','Supervisor and')):
                p.paragraph_format.page_break_before=True
            base.add_inline(p,title,size=15);continue
        if v.startswith('### '):
            p=doc.add_paragraph(style='Heading 2');base.add_inline(p,v[4:],size=12.5);continue
        if v.startswith('|'):
            rows,j=base.parse_table(lines,i-1);table(doc,rows);i=j;continue
        m=re.match(r'!\[(.*?)\]\((.*?)\)',v)
        if m:
            p=doc.add_paragraph();p.paragraph_format.keep_with_next=True;p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            pic=p.add_run().add_picture(str(source.parent/m.group(2)),width=Inches(5.70));pic._inline.docPr.set('descr',m.group(1));continue
        p=doc.add_paragraph(style='Normal')
        if cover and not v.startswith(('The proposed','本项目')):p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        if re.match(r'^(?:(?:Table|Figure) \d+ |[表图]\d+ )',v):
            p.paragraph_format.keep_with_next=v.startswith(('Table','表'));base.add_inline(p,v,size=10.5);continue
        if re.match(r'^\d+\. ',v):p.paragraph_format.left_indent=Inches(.2);p.paragraph_format.first_line_indent=Inches(-.2)
        base.add_inline(p,v,size=11 if refs else 12)
        if v.startswith(('导师意见：','第二阅卷人意见：','Supervisor comments:','Second reader comments:')):
            for _ in range(3):doc.add_paragraph()
    doc.core_properties.title='AI Desktop Calendar with Continuous Posture Monitoring and Feedback'
    doc.core_properties.author='Group 2'
    dest.parent.mkdir(parents=True,exist_ok=True);doc.save(dest);print(dest)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--lang',choices=['zh','en','both'],default='both');a=parser.parse_args()
    for lang in (['zh','en'] if a.lang=='both' else [a.lang]):diagram(lang);build(lang)
