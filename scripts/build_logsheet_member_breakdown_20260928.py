"""Create a named three-member revision of the retained school log form."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import json
from lxml import etree as E
import build_logsheet_20260928 as base

ROOT = Path(__file__).resolve().parents[1]
SOURCE = base.SOURCE
QA = ROOT / 'output/qa/logsheet-members-v2-2026-09-28'
OUT = ROOT / 'output/submission/2026-09-28/member-breakdown-v2'
W, NS = base.W, base.NS

CONTENT = {
    'attribution_status': 'Arranged under planned roles at the group leader request; for member review, not independently verified personal authorship.',
    'work': [
        'Yuan Yuchen: Coordinated the Marco review and change of direction. Consolidated posture-feedback requirements, proposal drafts and the Qwen-first voice shortlist with AI assistance.',
        'Xu Ziqian: Reviewed candidate Pi, camera, audio and display hardware. Compared AVA-style reflection and fan options, noting interface, power and mechanical-arm checks still needed.',
        'Li Wenhua: Organised calendar, recurring-event, privacy, conflict-warning and TimeTable requirements. Outlined posture prompts and daily-record information in the concept.',
        'Shared work: Reviewed the earlier simulated food prototype and mixed-dish nutrition limits. Changed to the desk-companion concept on 25 September for further development.'
    ],
    'plan': [
        'Yuan Yuchen: Complete the English proposal for review and submission by 29 September. Define posture labels, calibration, rechecking, voice tools and the evaluation plan.',
        'Xu Ziqian: Confirm camera view, display control and Pi interfaces. Plan arm power, limits and stop controls; check component availability before finalising the enclosure.',
        'Li Wenhua: Map touchscreen, phone and computer views to shared calendar data. Draft Today, Calendar, Posture and Records interactions and recurrence/conflict test cases.',
        'Shared work: Review this contribution breakdown and the proposal. Agree module interfaces, track sources and AI assistance, and record actual progress for the next team log.'
    ],
    'pending': 'Yuan: posture/voice implementation and accuracy tests pending. Xu: assembly and hardware tests pending. Li: new calendar/interface implementation pending. No earlier log plan.',
    'other': 'Next period: 28 September to 11 October 2026. Submit one group log with named work, findings, pending items and plans for all three members.',
    'research': [
        'Yuan Yuchen: Mixed-dish nutrients could not be measured precisely.',
        'Xu Ziqian: Small displays need verified programmable control.',
        'Li Wenhua: Calendar, posture prompts and records need linked states.',
        'Team: 55 legacy backend tests passed using simulated inputs.'
    ],
    'discoveries': 'The food prototype tests apply only to the retired software. The new scope links continuous posture detection, specific feedback and rechecking with a calendar. Camera placement, display control, voice execution and arm safety need separate tests; none is yet validated.',
    'remark': 'Coverage: 14-27 Sep 2026. Member-review draft: individual attribution is arranged under the planned roles, using existing group records. Confirm attribution before submission. AI assisted research, drafting, prototype code and checks; new hardware remains untested.'
}

def fill(p, text, size=11, align='left'):
    base.set_paragraph(p, text, size, align)
    prefixes = ('Yuan Yuchen:', 'Xu Ziqian:', 'Li Wenhua:', 'Shared work:', 'Team:')
    prefix = next((s for s in prefixes if text.startswith(s)), None)
    if prefix:
        r = p.find('w:r', NS)
        t = r.find('w:t', NS)
        t.text = prefix
        E.SubElement(r.find('w:rPr', NS), f'{{{W}}}b')
        tail = E.SubElement(p, f'{{{W}}}r')
        rp = E.SubElement(tail, f'{{{W}}}rPr')
        fonts = E.SubElement(rp, f'{{{W}}}rFonts')
        for attr in ('ascii', 'hAnsi', 'cs'):
            fonts.set(f'{{{W}}}{attr}', 'Times New Roman')
        E.SubElement(rp, f'{{{W}}}sz').set(f'{{{W}}}val', str(int(size * 2)))
        E.SubElement(rp, f'{{{W}}}color').set(f'{{{W}}}val', '000000')
        t = E.SubElement(tail, f'{{{W}}}t')
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = text[len(prefix):]

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
            for extra in ps[1:]:
                tc.remove(extra)
            fill(ps[0], text, size, align)
        cell(0, 1, 'IT114124 / AIST-2B', 12)
        cell(0, 3, 'Yuan Yuchen / Xu Ziqian / Li Wenhua', 10.5)
        cell(0, 5, '28 September 2026', 12, 'center')
        cell(1, 1, 'Marco', 12)
        cell(1, 3, '250342840 / 250137555 / 250329909', 10.5)
        for i in range(4):
            cell(i + 3, 1, CONTENT['work'][i])
            cell(i + 3, 3, CONTENT['plan'][i])
            cell(i + 10, 1, CONTENT['research'][i])
        cell(7, 1, CONTENT['pending'])
        cell(7, 3, CONTENT['other'])
        cell(10, 2, CONTENT['discoveries'])
        cell(14, 1, CONTENT['remark'])
        for box in root.xpath('//w:txbxContent', namespaces=NS):
            text = ''.join(box.xpath('.//w:t/text()', namespaces=NS))
            if text.startswith('Project ID'):
                fill(box.find('w:p', NS), 'Project ID: Group 2', 12)
            elif text.startswith('Log Sheet No.'):
                fill(box.find('w:p', NS), 'Log Sheet No.: 1', 12)
        for p in root.xpath('//w:body/w:tbl/following-sibling::w:p', namespaces=NS):
            if not ''.join(p.xpath('.//w:t/text()', namespaces=NS)).strip():
                fill(p, '', 1)
                ppr = p.find('w:pPr', NS)
                for old in ppr.findall('w:rPr', NS):
                    ppr.remove(old)
                rp = E.SubElement(ppr, f'{{{W}}}rPr')
                E.SubElement(rp, f'{{{W}}}sz').set(f'{{{W}}}val', '2')
                E.SubElement(rp, f'{{{W}}}szCs').set(f'{{{W}}}val', '2')
        data = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        with ZipFile(dest, 'w') as out:
            for item in src.infolist():
                out.writestr(item, data if item.filename == 'word/document.xml' else src.read(item.filename))
    with ZipFile(SOURCE) as a, ZipFile(dest) as b:
        changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
    assert changed == ['word/document.xml'], changed
    (QA / 'content.json').write_text(json.dumps(CONTENT, ensure_ascii=False, indent=2) + '\n')
    (QA / 'package-check.json').write_text(json.dumps({'source_sha256': sha256(SOURCE.read_bytes()).hexdigest(), 'output': str(dest), 'changed_parts': changed}, indent=2) + '\n')
    print(dest)

if __name__ == '__main__':
    main()
