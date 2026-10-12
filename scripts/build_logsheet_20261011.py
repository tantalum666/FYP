"""Populate the user-supplied v5 school form and preserve its package."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import json

from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/tantalum/Downloads/Final Year Project - Log Sheet (Bi-weekly) v5 AY26.docx')
QA = ROOT / 'output/qa/2026-10-11-logsheet-2'
OUT = ROOT / 'output/submission/2026-10-11'
DEST = OUT / 'AY26_Logsheet_No2_Group 2_YuanYuchen_250342840.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}

CONTENT = {
    'period': '28 September to 11 October 2026',
    'next_period': '12 to 25 October 2026',
    'date': '11 October 2026',
    'work': [
        'Yuan Yuchen: Led AI-assisted development of the Desk Companion calendar, posture and task prototype. Added voice adapters and approved note saving with independent read-back. Local checks passed.',
        'Xu Ziqian: Jointly prepared the materials purchasing list with Li Wenhua for the desk prototype. Purchases, wiring, assembly and hardware test results still need confirmation.',
        'Li Wenhua: Jointly prepared the materials purchasing list with Xu Ziqian. The list supports the next hardware phase; exact models and interface compatibility still need checking.',
        'Yuan Yuchen: Added a licensed 3D sample and prepared character concepts with AI assistance. Preserved code, research and sources in the private GitHub repository. Custom 3D modelling is pending.'
    ],
    'plan': [
        'Yuan Yuchen: Define one permitted PC task and verify its result. Prepare consented posture evaluation and a short voice comparison once access and a test budget are available.',
        'Xu Ziqian: Check the list against Pi, fixed-camera, audio and power requirements. Confirm exact models, quantities, cables and availability before assembly.',
        'Li Wenhua: Check display, RIG-Arm and mounting requirements against the list. Prepare interface, motion-limit and stop-control checks for the hardware bench.',
        'Group 2: Agree the hardware task split, review individual contributions and prepare the Progress I demonstration. Keep test records and AI-assisted work clearly identified.'
    ],
    'pending': 'Yuan: Real-camera/voice trials and general PC control remain pending. Xu/Li: Procurement, assembly and bench-test status still need confirmation.',
    'other': 'Period: 28 Sep-11 Oct 2026. Next: 12-25 Oct.\nPrepare Progress I for 26 Oct 2026.\nReview member contributions and proposed plans.',
    'ai_purposes': [
        'Requirements, technical research and proposal drafting.',
        'Prototype code, debugging, test cases and review of local results.',
        'UI references and original character concept images; no new 3D model.',
        'Drafting, formatting and checking this bi-weekly team log.'
    ],
    'ai_tools': 'Tasks 1, 2 and 4\nOpenAI ChatGPT / Codex\n\nTask 3\nOpenAI ImageGen\nConcept and UI images only',
    'attribution': 'Hardware purchasing list jointly attributed following the user confirmation. Next hardware checks are proposed for member review. AI assistance is declared.'
}


def q(tag):
    return f'{{{W}}}{tag}'


def paragraph(p, text, size=11, align='left'):
    old = p.find('w:pPr', NS)
    ppr = deepcopy(old) if old is not None else E.Element(q('pPr'))
    for child in list(p):
        p.remove(child)
    p.append(ppr)
    for name in ('spacing', 'jc', 'snapToGrid'):
        for child in ppr.findall(f'w:{name}', NS):
            ppr.remove(child)
    spacing = E.SubElement(ppr, q('spacing'))
    for key, value in {'before': '0', 'after': '0', 'line': str(int((size + 2) * 20)), 'lineRule': 'exact'}.items():
        spacing.set(q(key), value)
    E.SubElement(ppr, q('snapToGrid')).set(q('val'), '0')
    E.SubElement(ppr, q('jc')).set(q('val'), align)
    prefixes = ('Yuan Yuchen:', 'Xu Ziqian:', 'Li Wenhua:', 'Group 2:')
    prefix = next((s for s in prefixes if text.startswith(s)), None)
    chunks = [(prefix, True), (text[len(prefix):], False)] if prefix else [(text, False)]
    for content, bold in chunks:
        r = E.SubElement(p, q('r'))
        rp = E.SubElement(r, q('rPr'))
        fonts = E.SubElement(rp, q('rFonts'))
        for key in ('ascii', 'hAnsi', 'cs'):
            fonts.set(q(key), 'Times New Roman')
        if bold:
            E.SubElement(rp, q('b'))
        for key in ('sz', 'szCs'):
            E.SubElement(rp, q(key)).set(q('val'), str(int(size * 2)))
        E.SubElement(rp, q('color')).set(q('val'), '000000')
        for i, line in enumerate(content.split('\n')):
            if i:
                E.SubElement(r, q('br'))
            t = E.SubElement(r, q('t'))
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            t.text = line


def main():
    QA.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    source_bytes = SOURCE.read_bytes()
    expected = json.loads((QA / 'provided_template-source.json').read_text())['sha256']
    assert sha256(source_bytes).hexdigest() == expected
    (QA / 'template-reference.docx').write_bytes(source_bytes)
    with ZipFile(SOURCE) as src:
        root = E.fromstring(src.read('word/document.xml'))
        original = deepcopy(root)
        rows = root.xpath('//w:body/w:tbl/w:tr', namespaces=NS)
        def cell(i, j, text, size=11, align='left'):
            tc = rows[i].findall('w:tc', NS)[j]
            ps = tc.findall('w:p', NS)
            for extra in ps[1:]:
                tc.remove(extra)
            paragraph(ps[0], text, size, align)
        cell(0, 1, 'IT114124 / AIST-2B', 12)
        cell(0, 3, 'Yuan Yuchen / Xu Ziqian / Li Wenhua', 10.5)
        cell(0, 5, CONTENT['date'], 12, 'center')
        cell(1, 1, 'Marco', 12)
        cell(1, 3, '250342840 / 250137555 / 250329909', 10.5)
        for i in range(4):
            cell(i + 3, 1, CONTENT['work'][i])
            cell(i + 3, 3, CONTENT['plan'][i])
            cell(i + 10, 1, CONTENT['ai_purposes'][i])
        cell(7, 1, CONTENT['pending'])
        cell(7, 3, CONTENT['other'])
        cell(10, 2, CONTENT['ai_tools'])
        for box in root.xpath('//w:txbxContent', namespaces=NS):
            text = ''.join(box.xpath('.//w:t/text()', namespaces=NS))
            if text.startswith('Project ID'):
                paragraph(box.find('w:p', NS), 'Project ID: Group 2', 12)
            elif text.startswith('Log Sheet No.'):
                paragraph(box.find('w:p', NS), 'Log Sheet No.: 2', 12)
        # The original empty paragraph after the full-page table causes a blank
        # second page in LibreOffice. Keep the required paragraph at 1 pt.
        for p in root.xpath('//w:body/w:tbl/following-sibling::w:p', namespaces=NS):
            if not ''.join(p.xpath('.//w:t/text()', namespaces=NS)).strip():
                paragraph(p, '', 1)
                ppr = p.find('w:pPr', NS)
                ppr.find('w:spacing', NS).set(q('line'), '20')
                for old in ppr.findall('w:rPr', NS):
                    ppr.remove(old)
                rp = E.SubElement(ppr, q('rPr'))
                for tag in ('sz', 'szCs'):
                    E.SubElement(rp, q(tag)).set(q('val'), '2')
        # All school geometry and labels stay in place, including blank feedback.
        for xpath in ('//w:sectPr', '//w:tblPr', '//w:tblGrid', '//w:trPr', '//w:tcPr'):
            before = [E.tostring(n) for n in original.xpath(xpath, namespaces=NS)]
            after = [E.tostring(n) for n in root.xpath(xpath, namespaces=NS)]
            assert before == after, xpath
        feedback = rows[14].findall('w:tc', NS)[1]
        assert not ''.join(feedback.xpath('.//w:t/text()', namespaces=NS)).strip()
        for i in (11, 12, 13):
            assert not rows[i].findall('w:tc', NS)[2].xpath('.//w:t/text()', namespaces=NS)
        xml = E.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        with ZipFile(DEST, 'w') as out:
            for item in src.infolist():
                out.writestr(item, xml if item.filename == 'word/document.xml' else src.read(item.filename))
    with ZipFile(SOURCE) as a, ZipFile(DEST) as b:
        assert a.namelist() == b.namelist()
        changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
    assert changed == ['word/document.xml']
    (QA / 'content.json').write_text(json.dumps(CONTENT, ensure_ascii=False, indent=2) + '\n')
    check = {'output': str(DEST), 'source_sha256': expected, 'changed_parts': changed,
             'school_geometry_unchanged': True, 'feedback_intentionally_blank': True,
             'ai_tools_merge_preserved': True}
    (QA / 'package-check.json').write_text(json.dumps(check, indent=2) + '\n')
    print(DEST)


if __name__ == '__main__':
    main()
