"""Fill the retained school log-sheet template without rebuilding its package."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from copy import deepcopy
import json
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/tantalum/Downloads/Final Year Project - Log Sheet (Bi-weekly) v4 AY26.docx')
OUT = ROOT / 'output/submission/2026-09-28'
QA = ROOT / 'output/qa/logsheet-proposal-2026-09-28'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}

CONTENT = {
    'work': [
        'Prepared the food-monitoring requirements and prototype with AI assistance. Reviewed simulated replenishment, ordering and meal-recording workflows and their software test evidence.',
        'Discussed camera cost and mixed-dish nutrient accuracy with Marco. Reviewed the team\'s alternative concepts and changed the direction to a desk companion.',
        'Defined continuous posture monitoring, specific feedback and rechecking as core functions, alongside calendar management and voice interaction. Prepared two Chinese proposal drafts with AI assistance.',
        'Compared voice services and AVA-style display options. Prioritised Qwen for evaluation and documented unresolved camera placement, display control and Raspberry Pi performance.'
    ],
    'plan': [
        'Complete the revised proposal with the group, review it with Marco, and submit the required English DOCX and PDF by 29 September.',
        'Define posture labels and personal-calibration rules. Prepare a consented capture protocol and compare single-frame thresholds with continuous-time detection.',
        'Start the calendar and posture software on the existing Mac; define the permitted voice commands and record actual module ownership.',
        'Confirm camera, audio, display and actuator interfaces. Verify programmable display control before finalising the enclosure or selecting a hologram module.'
    ],
    'pending': 'First log sheet; no previous recorded plan. New-device assembly, posture accuracy, voice API integration and display-control latency remain untested.',
    'other': 'Next period: 28 September to 11 October 2026. Submit one team log; trace each member\'s contributions, AI assistance, sources and test results.',
    'research': [
        'Legacy food prototype: 55 backend tests passed using simulated inputs.',
        'Supervisor feedback questioned camera cost and mixed-dish nutrient accuracy.',
        'Team concept review identified calendar and posture-feedback requirements.',
        'New desk-device accuracy, audio and display performance: not yet measured.'
    ],
    'discoveries': 'Legacy software tests validate the old workflow only. Images and total weight cannot guarantee precise mixed-dish nutrients. The revised concept needs separate evidence for posture detection, feedback, speech and display control.',
    'remark': 'Period: 14-27 Sep 2026. Members: Yuan Yuchen (250342840), Xu Ziqian (250137555), Li Wenhua (250329909). Yuan represents Group 2 in the header. AI assisted research, drafting, prototype code and checks. The group changed direction on 25 Sep; new hardware remains untested.'
}

def set_paragraph(p, text, size=11, align='left'):
    ppr = p.find('w:pPr', NS)
    saved = deepcopy(ppr) if ppr is not None else E.Element(f'{{{W}}}pPr')
    for child in list(p):
        p.remove(child)
    p.append(saved)
    for tag in ('spacing', 'jc', 'snapToGrid'):
        for node in saved.findall(f'w:{tag}', NS):
            saved.remove(node)
    spacing = E.SubElement(saved, f'{{{W}}}spacing')
    spacing.set(f'{{{W}}}before', '0'); spacing.set(f'{{{W}}}after', '0')
    spacing.set(f'{{{W}}}line', str(int((size + 2) * 20)))
    spacing.set(f'{{{W}}}lineRule', 'exact')
    E.SubElement(saved, f'{{{W}}}snapToGrid').set(f'{{{W}}}val', '0')
    E.SubElement(saved, f'{{{W}}}jc').set(f'{{{W}}}val', align)
    for i, line in enumerate(text.split('\n')):
        r = E.SubElement(p, f'{{{W}}}r')
        rpr = E.SubElement(r, f'{{{W}}}rPr')
        fonts = E.SubElement(rpr, f'{{{W}}}rFonts')
        for a in ('ascii','hAnsi','cs'): fonts.set(f'{{{W}}}{a}', 'Times New Roman')
        E.SubElement(rpr, f'{{{W}}}sz').set(f'{{{W}}}val', str(int(size*2)))
        E.SubElement(rpr, f'{{{W}}}color').set(f'{{{W}}}val', '000000')
        if i: E.SubElement(r, f'{{{W}}}br')
        E.SubElement(r, f'{{{W}}}t').text = line

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / 'AY26_Logsheet_Group 2_YuanYuchen_250342840.docx'
    with ZipFile(SOURCE) as src:
        root = E.fromstring(src.read('word/document.xml'))
        table = root.find('.//w:body/w:tbl', NS)
        rows = table.findall('w:tr', NS)
        def cell(row, col, text, size=11, align='left'):
            tc = rows[row].findall('w:tc', NS)[col]
            ps = tc.findall('w:p', NS)
            for extra in ps[1:]: tc.remove(extra)
            set_paragraph(ps[0], text, size, align)
        cell(0,1,'IT114124 / AIST-2B',12)
        cell(0,3,'Yuan Yuchen (Group Leader)',11)
        cell(0,5,'28 September 2026',12,'center')
        cell(1,1,'Marco',12); cell(1,3,'250342840',12)
        for i in range(4):
            cell(i+3,1,CONTENT['work'][i]); cell(i+3,3,CONTENT['plan'][i])
            cell(i+10,1,CONTENT['research'][i])
        cell(7,1,CONTENT['pending']); cell(7,3,CONTENT['other'])
        cell(10,2,CONTENT['discoveries']); cell(14,1,CONTENT['remark'])
        for box in root.xpath('//w:txbxContent',namespaces=NS):
            text=''.join(box.xpath('.//w:t/text()',namespaces=NS))
            if text.startswith('Project ID'):
                set_paragraph(box.find('w:p',NS),'Project ID: Group 2',12)
            elif text.startswith('Log Sheet No.'):
                set_paragraph(box.find('w:p',NS),'Log Sheet No.: 1',12)
        # Word requires a trailing paragraph after the table. Keep it on page one.
        for p in root.xpath('//w:body/w:tbl/following-sibling::w:p', namespaces=NS):
            if not ''.join(p.xpath('.//w:t/text()', namespaces=NS)).strip():
                set_paragraph(p, '', 1)
                ppr = p.find('w:pPr', NS)
                for old in ppr.findall('w:rPr', NS): ppr.remove(old)
                rpr = E.SubElement(ppr, f'{{{W}}}rPr')
                E.SubElement(rpr, f'{{{W}}}sz').set(f'{{{W}}}val', '2')
                E.SubElement(rpr, f'{{{W}}}szCs').set(f'{{{W}}}val', '2')
        data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        with ZipFile(dest,'w') as out:
            for item in src.infolist(): out.writestr(item,data if item.filename=='word/document.xml' else src.read(item.filename))
    with ZipFile(SOURCE) as a, ZipFile(dest) as b:
        changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert changed==['word/document.xml'], changed
    (QA/'logsheet-content.json').write_text(json.dumps(CONTENT,ensure_ascii=False,indent=2)+'\n')
    (QA/'logsheet-package-check.json').write_text(json.dumps({'source_sha256':sha256(SOURCE.read_bytes()).hexdigest(),'output':str(dest),'changed_parts':changed},indent=2)+'\n')
    print(dest)

if __name__=='__main__': main()
