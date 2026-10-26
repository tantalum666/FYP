#!/usr/bin/env python3
"""Fill the retained school template without rewriting unrelated DOCX parts."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "output/qa/suggestion-2026-09-14"
REFERENCE = QA / "reference.docx"
OUTPUT = ROOT / "output/docx/AY26_ProjectSuggestion_Group 2.docx"
REFERENCE_SHA256 = "7cc26bead5d75b140a3044328bd724ac6e418dc5efaa703084f39b6d363b10d5"
HELPER = Path(
    "/Users/tantalum/.codex/plugins/cache/openai-primary-runtime/documents/"
    "26.909.12148/skills/documents/scripts/docx_ooxml_patch.py"
)

spec = importlib.util.spec_from_file_location("docx_patch_helper", HELPER)
patch_helper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(patch_helper)
NS = patch_helper.NS


def qn(name: str) -> str:
    return patch_helper._qn("w", name)


def text_of(element) -> str:
    return "".join(element.xpath(".//w:t/text()", namespaces=NS))


def set_property(parent, name: str, value: str | None = None):
    element = parent.find(qn(name))
    if element is None:
        element = etree.SubElement(parent, qn(name))
    if value is not None:
        element.set(qn("val"), value)
    return element


def write_paragraph(paragraph, segments: list[tuple[str, bool]]):
    original_rpr = paragraph.find("w:r/w:rPr", NS)
    base = copy.deepcopy(original_rpr) if original_rpr is not None else etree.Element(qn("rPr"))
    for tag in ("i", "iCs", "b", "bCs"):
        for element in base.findall(qn(tag)):
            base.remove(element)
    set_property(base, "color", "333333")
    for child in list(paragraph):
        if child.tag != qn("pPr"):
            paragraph.remove(child)
    for text, bold in segments:
        run = etree.SubElement(paragraph, qn("r"))
        props = copy.deepcopy(base)
        if bold:
            set_property(props, "b")
        run.append(props)
        for index, line in enumerate(text.split("\n")):
            if index:
                etree.SubElement(run, qn("br"))
            if line:
                node = etree.SubElement(run, qn("t"))
                node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                node.text = line


def write_cell(cell, segments: list[tuple[str, bool]]):
    paras = cell.findall(qn("p"))
    assert len(paras) == 1
    write_paragraph(paras[0], segments)


def canonical(element) -> bytes:
    return etree.tostring(element, method="c14n")


def main():
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_SHA256
    assert (QA / "artifact.md").exists()
    group = json.loads((ROOT / "planning/2026-09-14/group-2-details.json").read_text())
    assert group["group_display_name"] == "Group 2"
    assert group["supervisor_verbal_agreement"] is False
    assert [m["planned_contribution_percent"] for m in group["members"]] == [40, 30, 30]

    with ZipFile(REFERENCE) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
        infos = archive.infolist()
    root = etree.fromstring(parts["word/document.xml"])
    body = root.find(qn("body"))
    paras = body.findall(qn("p"))
    tables = body.findall(qn("tbl"))
    assert len(paras) == 17 and len(tables) == 3
    assert text_of(paras[6]) == "2. Problem Statement & Project Objectives"
    assert text_of(paras[15]) == "5. Endorsements & Supervisor Feedback"
    untouched_endorsement = canonical(tables[2])
    original_section = canonical(body.find(qn("sectPr")))

    project_title = "AI and IoT Based Food Replenishment and Waste Reduction System"
    general_values = [
        project_title,
        "Macro (proposed; verbal agreement pending)",
        f'{group["programme"]} / Class {group["class_code"]}',
        "Group 2",
    ]
    for row, value in zip(tables[0].findall(qn("tr")), general_values):
        write_cell(row.findall(qn("tc"))[1], [(value, False)])

    roles = [
        (
            "Project Leader / Backend AI Lead",
            "Requirements, APIs, food recognition, demand forecasting, replenishment and integration tests.",
        ),
        (
            "IoT Hardware / Edge Processing",
            "Sensor integration, Pi acquisition, calibration, filtering, tray events and hardware tests.",
        ),
        (
            "Web Application / UX Developer",
            "Staff dashboard, QR menu and orders, live updates, bilingual UI and usability tests.",
        ),
    ]
    member_rows = tables[1].findall(qn("tr"))
    for i, (member, role_data) in enumerate(zip(group["members"], roles), start=1):
        row = member_rows[i]
        cells = row.findall(qn("tc"))
        role, responsibility = role_data
        fields = [str(i), member["name"], member["student_id"], member["email"].replace("@", "@\n")]
        for cell, value in zip(cells[:4], fields):
            write_cell(cell, [(value, False)])
        write_cell(cells[4], [
            (f'{role} ({member["planned_contribution_percent"]}%)\n', True),
            (responsibility, False),
        ])
        trpr = row.find(qn("trPr"))
        if trpr is None:
            trpr = etree.Element(qn("trPr"))
            row.insert(0, trpr)
        set_property(trpr, "cantSplit")
    tables[1].remove(member_rows[4])

    problem = (
        "Buffet and batch-prepared self-service outlets need timely replenishment without excess food "
        "at closing. Visual checks can miss low stock or batches already being prepared, leading to "
        "waiting, duplicate work and leftovers. Customer menus can also show outdated availability.\n"
        "We propose continuous monitoring while trays remain in service, linking measurements, demand "
        "estimates and kitchen progress. Metafoodx and Controliza are commercial references; the prototype "
        "will be evaluated against simple replenishment baselines."
    )
    objectives = [
        "Implement continuous monitoring for up to three serving positions, recording food quantity, "
        "refills and surface temperature and flagging unreliable data.",
        "Develop AI-assisted replenishment recommendations using demand, preparation lead time and work in progress; "
        "compare empty-tray time and leftovers against fixed-threshold and consumption-rate baselines.",
        "Integrate bilingual staff tools and a supplementary QR menu/order interface; evaluate "
        "consistency, interruption recovery and usability.",
    ]
    problem_segments = [("Problem Statement:\n", True), (problem, False), ("\n\nProject Objectives:\n", True)]
    for i, objective in enumerate(objectives, start=1):
        problem_segments.append((f'{i}. {objective}' + ("\n" if i < 3 else ""), False))
    write_paragraph(paras[8], problem_segments)

    scope_segments = [
        ("Key Subsystems / Features:\n", True),
        ("A. Continuous tray monitoring. ", True),
        ("Monitor weight, visual dish identity and surface temperature throughout service; handle tare, "
         "tray movement, refills, occlusion and stale data.\n", False),
        ("B. Replenishment and kitchen tasks. ", True),
        ("Suggest timing and batch quantities using demand, preparation/closing times and work in progress. "
         "Staff confirm or adjust tasks and record completed refills.\n", False),
        ("C. Operations dashboard and evaluation. ", True),
        ("Show alerts and export empty-tray time, refill history, leftovers and disposal/reuse records.\n", False),
        ("D. Supplementary QR menu and ordering. ", True),
        ("Show dish details, availability, completed-order popularity or buffet take-up trends and estimated "
         "waits. Support fast-casual/made-to-order orders, checking pending demand against physical stock.\n", False),
        ("Prototype Scope: ", True),
        ("Six months, one line, up to three positions and 4-6 registered dishes; excludes payments, "
         "delivery, procurement ERP and independent food-safety certification.\n", False),
        ("Expected Users & Roles: ", True),
        ("Staff monitor and refill trays; managers maintain menus/settings and review reports; customers "
         "view menus and submit or track applicable orders.", False),
    ]
    write_paragraph(paras[11], scope_segments)

    technology_segments = [
        ("Development Technologies & Tools:\n", True),
        ("• Hardware: ", True),
        ("Raspberry Pi 5 with load cells and ADC interfaces (such as HX711 or NAU7802), an overhead "
         "camera, surface-temperature sensor, display and LEDs. Assess RGB-D after range and cost tests. "
         "Existing UNO R4 WiFi is optional for acquisition/debugging.\n", False),
        ("• Programming Languages: ", True),
        ("Python, TypeScript, HTML/CSS; C++ only if a microcontroller is used.\n", False),
        ("• Frameworks / Libraries: ", True),
        ("FastAPI, OpenCV, PyTorch for model training, scikit-learn, React and i18next.\n", False),
        ("• Database / Storage: ", True),
        ("PostgreSQL and local measurement/image logs.\n", False),
        ("• Target Platforms: ", True),
        ("Local Linux device and responsive staff/customer web interfaces.\n\n", False),
        ("Special Project Considerations:\n", True),
        ("• Contemporary Technologies: ", True),
        ("IoT sensing, local AI inference and live web updates; optional cloud backup after the local core works.\n", False),
        ("• Environmental-Friendly Solution: ", True),
        ("Evaluate avoidable food surplus; reuse available computing equipment and use replaceable sensing components.\n", False),
        ("• Bilingual / Multi-Language Support: ", True),
        ("English and Traditional Chinese interfaces.\n", False),
        ("• Cross-Border Deployment / Greater China Needs: ", True),
        ("Configurable language, currency and time zone, with local deployment options for later regional adaptation.\n", False),
        ("• Feasibility: ", True),
        ("Confirm camera/ADC compatibility, sampling stability and cost by bench tests. Use controlled service "
         "scenarios initially and arrange a field trial if access becomes available.", False),
    ]
    write_paragraph(paras[14], technology_segments)

    for index in (6, 15):
        ppr = paras[index].find(qn("pPr"))
        set_property(ppr, "pageBreakBefore")
    # The source's blank spacer can overflow after a populated member table and
    # create an empty page before the explicit section-2 break.
    assert text_of(paras[5]) == ""
    body.remove(paras[5])

    assert canonical(tables[2]) == untouched_endorsement
    assert canonical(body.find(qn("sectPr"))) == original_section
    parts["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    settings = etree.fromstring(parts["word/settings.xml"])
    update_fields = set_property(settings, "updateFields", "true")
    settings.remove(update_fields)
    following_settings = {
        "hdrShapeDefaults", "footnotePr", "endnotePr", "compat", "docVars", "rsids",
        "mathPr", "attachedSchema", "themeFontLang", "clrSchemeMapping",
        "doNotIncludeSubdocsInStats", "doNotAutoCompressPictures", "forceUpgrade",
    }
    position = next((i for i, child in enumerate(settings)
                     if etree.QName(child).localname in following_settings), len(settings))
    settings.insert(position, update_fields)
    parts["word/settings.xml"] = etree.tostring(settings, xml_declaration=True, encoding="UTF-8", standalone=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w") as archive:
        for info in infos:
            archive.writestr(info, parts[info.filename])
    with ZipFile(REFERENCE) as before, ZipFile(OUTPUT) as after:
        changed = [name for name in before.namelist() if before.read(name) != after.read(name)]
        assert set(changed) == {"word/document.xml", "word/settings.xml"}
        assert set(before.namelist()) == set(after.namelist())
    extracted = text_of(root)
    for member in group["members"]:
        assert member["name"] in extracted and member["student_id"] in extracted and member["email"] in extracted
    for placeholder in ("[Student", "[Enter", "[Objective", "[Subsystem", "[e.g.", "Group 02", "Group02"):
        assert placeholder not in extracted, placeholder
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "build-validation.json").write_text(json.dumps({
        "output": str(OUTPUT),
        "source_sha256": REFERENCE_SHA256,
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "changed_parts": changed,
        "preserve_only_parts_unchanged": True,
        "endorsements_unchanged": True,
        "page_geometry_unchanged": True,
        "member_count": 3,
        "planned_workloads": [40, 30, 30],
        "supervisor_verbal_agreement": False,
        "visual_validation": "pending",
    }, indent=2) + "\n")
    (QA / "filled-content.json").write_text(json.dumps({
        "title": project_title,
        "problem_statement": problem,
        "objectives": objectives,
        "roles": [{"name": m["name"], "role": r[0], "responsibility": r[1],
                   "planned_workload_percent": m["planned_contribution_percent"]}
                  for m, r in zip(group["members"], roles)],
        "scope": "".join(t for t, _ in scope_segments),
        "technology": "".join(t for t, _ in technology_segments),
    }, ensure_ascii=False, indent=2) + "\n")
    print(OUTPUT)
    print("Preserve-only DOCX parts, endorsement content and page geometry verified.")


if __name__ == "__main__":
    main()
