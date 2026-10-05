#!/usr/bin/env python3
"""Create a separate multi-scenario revision while preserving V1 and the form."""

from pathlib import Path
from zipfile import ZipFile
import hashlib
import importlib.util
import json

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'output/qa/suggestion-v2-2026-09-14'
REFERENCE = QA / 'reference-v1.docx'
REFERENCE_SHA256 = 'dbbc4efa0c1a0f6a58041558ff1dbdf52f189fb8608552558c391bf9ec59d3b4'
OUTPUT = ROOT / 'output/docx/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.docx'

spec = importlib.util.spec_from_file_location('fyp_v1_helpers', ROOT / 'scripts/build_suggestion.py')
helpers = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(helpers)
NS = helpers.NS
qn = helpers.qn


def check_v1_preserved():
    saved = json.loads((QA / 'v1-preservation-before.json').read_text())
    for relative in [
        'output/docx/AY26_ProjectSuggestion_Group 2.docx',
        'output/pdf/AY26_ProjectSuggestion_Group 2.pdf',
        'scripts/build_suggestion.py',
    ]:
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == saved[relative]
    assert hashlib.sha256((QA / 'group-details-v1.json').read_bytes()).hexdigest() == saved['planning/2026-09-14/group-2-details.json']


def main():
    check_v1_preserved()
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_SHA256
    assert (QA / 'artifact.md').exists()
    group = json.loads((ROOT / 'planning/2026-09-14/group-2-details.json').read_text())
    assert group['group_display_name'] == 'Group 2'
    assert group['proposed_supervisor'] == 'Marco'
    assert [m['planned_contribution_percent'] for m in group['members']] == [40, 30, 30]

    with ZipFile(REFERENCE) as z:
        infos = z.infolist()
        parts = {n: z.read(n) for n in z.namelist()}
    root = etree.fromstring(parts['word/document.xml'])
    body = root.find(qn('body'))
    paras = body.findall(qn('p'))
    tables = body.findall(qn('tbl'))
    assert len(paras) == 16 and len(tables) == 3
    assert helpers.text_of(paras[7]).startswith('Problem Statement:')
    assert helpers.text_of(paras[10]).startswith('Key Subsystems / Features:')
    assert helpers.text_of(paras[13]).startswith('Development Technologies & Tools:')
    original_endorsement = helpers.canonical(tables[2])
    original_section = helpers.canonical(body.find(qn('sectPr')))
    member_fields = [
        [helpers.canonical(c) for c in row.findall(qn('tc'))[:4]]
        for row in tables[1].findall(qn('tr'))[1:]
    ]

    title = 'AI and IoT Based Food and Nutrition Monitoring System'
    rows = tables[0].findall(qn('tr'))
    helpers.write_cell(rows[0].findall(qn('tc'))[1], [(title, False)])
    helpers.write_cell(rows[1].findall(qn('tc'))[1], [('Marco (revised scope for review)', False)])

    roles = [
        ('Project Leader / Backend AI Lead',
         'Requirements, APIs, food recognition, nutrition estimates, forecasts and integration tests.'),
        ('IoT Hardware / Edge Processing',
         'Sensing hardware, Pi acquisition, container calibration, event detection and reliability tests.'),
        ('Web Application / UX Developer',
         'Scenario dashboards, QR menu/orders, nutrition views, bilingual UI and usability tests.'),
    ]
    for row, member, (role, responsibility) in zip(tables[1].findall(qn('tr'))[1:], group['members'], roles):
        helpers.write_cell(row.findall(qn('tc'))[4], [
            (f'{role} ({member["planned_contribution_percent"]}%)\n', True),
            (responsibility, False),
        ])

    problem = (
        'Foodservice teams, schools and individuals need easier ways to connect food quantity, nutrition '
        'and leftovers. Buffets need timely replenishment, schools need portion and food-group records, '
        'and individuals need less manual meal logging.\n'
        'We propose continuous monitoring while serving containers or meal plates remain on sensing bases. '
        'Food recognition, measured portions and reference nutrition data enable scenario-specific feedback. '
        'Metafoodx and Controliza are design references; benefits will be evaluated in controlled tests.'
    )
    objectives = [
        'Implement shared continuous monitoring of food identity, quantity and leftovers for serving '
        'containers and individual meals.',
        'Provide AI-assisted replenishment and reference-based nutrition feedback for foodservice, '
        'school and personal profiles, with human confirmation.',
        'Compare measurement/nutrition calculations with manual references, and empty-tray time/leftovers '
        'with replenishment baselines; evaluate usability and recovery.',
    ]
    segments = [('Problem Statement:\n', True), (problem, False), ('\n\nProject Objectives:\n', True)]
    segments += [(f'{i}. {t}' + ('\n' if i < 3 else ''), False)
                 for i, t in enumerate(objectives, start=1)]
    helpers.write_paragraph(paras[7], segments)

    scope = [
        ('Key Subsystems / Features:\n', True),
        ('A. Shared continuous sensing. ', True),
        ('Track food quantities, identity, refills and leftovers; handle tare, movement, occlusion and '
         'stale data. Record surface temperature where applicable.\n', False),
        ('B. Nutrition estimates. ', True),
        ('Match portions to registered recipes/food records. Distinguish provided food, leftovers and '
         'confirmed intake estimates; flag uncertain mappings.\n', False),
        ('C. Three application profiles. ', True),
        ('Foodservice: replenishment timing and batch tasks. Schools: compare portions with configured '
         'meal plans and report aggregate leftovers. Personal: adult meal records, estimated nutrients '
         'and food-group feedback.\n', False),
        ('D. Interfaces and feedback. ', True),
        ('Bilingual dashboards, alerts and reports; QR menus retain availability, completed-order popularity '
         'and estimated waits. Basic orders and kitchen status remain available for foodservice.\n', False),
        ('Prototype Scope: ', True),
        ('Six months; three profiles, up to three weighing positions and 4-6 registered foods/recipes. '
         'Test separately weighed items/known recipes and anonymous school example meals.\n', False),
        ('Expected Users & Roles: ', True),
        ('Kitchen teams, primary and secondary school staff, and adult users; students/parents see appropriate menu and '
         'educational summaries.', False),
    ]
    helpers.write_paragraph(paras[10], scope)

    technology = [
        ('Development Technologies & Tools:\n', True),
        ('• Hardware: ', True),
        ('Raspberry Pi 5, load cells with ADC interfaces, overhead camera, surface-temperature sensor '
         'and display/LEDs. Adapt supports for serving containers or meal plates; assess RGB-D by testing. '
         'Existing UNO R4 WiFi is optional.\n', False),
        ('• Programming Languages: ', True),
        ('Python, TypeScript, HTML/CSS; C++ only if a microcontroller is used.\n', False),
        ('• Frameworks / Libraries: ', True),
        ('OpenCV, PyTorch/scikit-learn, FastAPI, React and i18next.\n', False),
        ('• Database / Storage: ', True),
        ('PostgreSQL, local logs, selected USDA FoodData Central records and registered recipes. '
         'Retain source IDs, units and cooking-state/recipe metadata.\n', False),
        ('• Target Platforms: ', True),
        ('Local Linux device and responsive web interfaces with configurable scenario profiles.\n\n', False),
        ('Special Project Considerations:\n', True),
        ('• Contemporary Technologies: ', True),
        ('IoT sensing, AI food recognition and demand estimates, reference-based nutrition calculations '
         'and live feedback; optional cloud backup.\n', False),
        ('• Environmental-Friendly Solution / Social Benefit: ', True),
        ('Support school meal review, personal nutrition awareness and avoidable-waste reduction with '
         'reusable hardware.\n', False),
        ('• Bilingual / Multi-Language Support: ', True),
        ('English and Traditional Chinese interfaces.\n', False),
        ('• Cross-Border Deployment / Greater China Needs: ', True),
        ('Configurable food catalogues, meal plans, currency and time zone; reviewed regional guidance, '
         'such as Hong Kong school-lunch guidelines.\n', False),
        ('• Responsible Use: ', True),
        ('Educational estimates, not diagnosis or prescribed diets. Uncertain mixed meals require '
         'confirmation; school demonstrations use anonymous meals without child health profiles.\n', False),
        ('• Feasibility / Validation: ', True),
        ('Test sensing and nutrition calculations against known portions/manual references; compare '
         'replenishment with fixed-threshold and consumption-rate baselines. Use controlled meals and '
         'adult usability tests; field access is not assumed. Full payment/ERP integration is excluded.', False),
    ]
    helpers.write_paragraph(paras[13], technology)
    helpers.set_property(paras[11].find(qn('pPr')), 'pageBreakBefore')

    assert helpers.canonical(tables[2]) == original_endorsement
    assert helpers.canonical(body.find(qn('sectPr'))) == original_section
    for row, original in zip(tables[1].findall(qn('tr'))[1:], member_fields):
        assert [helpers.canonical(c) for c in row.findall(qn('tc'))[:4]] == original
    parts['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, 'w') as z:
        for info in infos:
            z.writestr(info, parts[info.filename])

    with ZipFile(REFERENCE) as before, ZipFile(OUTPUT) as after:
        changed = [n for n in before.namelist() if before.read(n) != after.read(n)]
        assert changed == ['word/document.xml']
        assert set(before.namelist()) == set(after.namelist())
    text = helpers.text_of(root)
    assert 'Marco (revised scope for review)' in text and 'Macro (' not in text
    for member in group['members']:
        assert member['name'] in text and member['student_id'] in text and member['email'] in text
    check_v1_preserved()
    (QA / 'filled-content.json').write_text(json.dumps({
        'title': title, 'problem_statement': problem, 'objectives': objectives,
        'scope': ''.join(t for t, _ in scope), 'technology': ''.join(t for t, _ in technology),
        'roles': [{'name': m['name'], 'role': r[0], 'responsibility': r[1],
                   'planned_workload_percent': m['planned_contribution_percent']}
                  for m, r in zip(group['members'], roles)],
    }, ensure_ascii=False, indent=2) + '\n')
    (QA / 'build-validation.json').write_text(json.dumps({
        'output': str(OUTPUT), 'source_sha256': REFERENCE_SHA256,
        'output_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        'changed_parts': changed, 'v1_preserved': True, 'member_fields_unchanged': True,
        'endorsements_unchanged': True, 'visual_validation': 'pending',
    }, indent=2) + '\n')
    print(OUTPUT)
    print('V1 deliverables and builder unchanged; only V2 body content changed.')


if __name__ == '__main__':
    main()
