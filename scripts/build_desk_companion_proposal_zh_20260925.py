"""Build the Group 2 Chinese review draft from its Markdown source."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = "planning/2026-09-25/desk-companion-proposal-zh-review.md"
DEFAULT_OUTPUT = "output/docx/Group 2_DeskCompanion_ProjectProposal_ZH_Review.docx"

FONT_CJK = "Noto Serif CJK SC"
FONT_LATIN = "Noto Serif CJK SC"
BLACK = RGBColor(0, 0, 0)
LIGHT_GRAY = "E9EEF2"
BORDER = "D9D9D9"


def set_font(run, size=12, bold=False, italic=False):
    run.font.name = FONT_LATIN
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = BLACK
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr, name in (
        ("ascii", FONT_LATIN),
        ("hAnsi", FONT_LATIN),
        ("eastAsia", FONT_CJK),
        ("cs", FONT_LATIN),
    ):
        fonts.set(qn(f"w:{attr}"), name)
    return run


def configure_style(style, size, *, bold=False, before=0, after=0, line=1.5):
    style.font.name = FONT_LATIN
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = BLACK
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)
    style.paragraph_format.line_spacing = line
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fonts.attrib.pop(qn(f"w:{attr}"), None)
    fonts.set(qn("w:eastAsia"), FONT_CJK)
    fonts.set(qn("w:ascii"), FONT_LATIN)
    fonts.set(qn("w:hAnsi"), FONT_LATIN)
    ppr = style.element.get_or_add_pPr()
    border = ppr.find(qn("w:pBdr"))
    if border is not None:
        ppr.remove(border)


def set_repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    tag = OxmlElement("w:tblHeader")
    tag.set(qn("w:val"), "true")
    trpr.append(tag)


def set_cell_shading(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = tcpr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcpr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=95, start=105, bottom=95, end=105):
    tcpr = cell._tc.get_or_add_tcPr()
    mar = tcpr.find(qn("w:tcMar"))
    if mar is None:
        mar = OxmlElement("w:tcMar")
        tcpr.append(mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_borders(table):
    tblpr = table._tbl.tblPr
    borders = tblpr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblpr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "4")
        node.set(qn("w:color"), BORDER)


def add_hyperlink(paragraph, url):
    part = paragraph.part
    relationship = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), relationship)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), FONT_LATIN)
    fonts.set(qn("w:hAnsi"), FONT_LATIN)
    props.append(fonts)
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "000000")
    props.append(color)
    run.append(props)
    text = OxmlElement("w:t")
    text.text = url
    run.append(text)
    link.append(run)
    paragraph._p.append(link)


INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|https?://\S+)")


def add_inline(paragraph, value: str, *, size=12):
    pos = 0
    for match in INLINE.finditer(value):
        if match.start() > pos:
            set_font(paragraph.add_run(value[pos: match.start()]), size)
        token = match.group(0)
        if token.startswith("**"):
            set_font(paragraph.add_run(token[2:-2]), size, bold=True)
        elif token.startswith("*"):
            set_font(paragraph.add_run(token[1:-1]), size, italic=True)
        elif token.startswith("http"):
            add_hyperlink(paragraph, token)
        pos = match.end()
    if pos < len(value):
        set_font(paragraph.add_run(value[pos:]), size)


def add_table(doc, rows):
    columns = len(rows[0])
    table = doc.add_table(rows=0, cols=columns)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_borders(table)
    headers = rows[0]
    if columns == 4:
        widths = [1.36, 0.95, 2.55, 0.91]
    elif columns == 3:
        widths = [1.34, 1.33, 3.1]
    elif columns == 2:
        widths = [1.44, 4.33]
    else:
        widths = [5.77 / columns] * columns
    for row_index, row_values in enumerate(rows):
        row = table.add_row()
        if row_index == 0:
            set_repeat_header(row)
        for col_index, cell_value in enumerate(row_values):
            cell = row.cells[col_index]
            cell.width = Inches(widths[col_index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if row_index == 0:
                set_cell_shading(cell, LIGHT_GRAY)
            elif row_index % 2 == 0:
                set_cell_shading(cell, "F8FAFB")
            para = cell.paragraphs[0]
            para.style = "Table Text"
            if col_index == columns - 1 and columns == 4:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_inline(para, cell_value, size=10.5)
            if row_index == 0:
                for run in para.runs:
                    run.font.bold = True
    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(3)
    return table


def add_page_field(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, end):
        run = OxmlElement("w:r")
        run.append(node)
        paragraph._p.append(run)


def configure_section(section):
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.5)
    section.right_margin = Inches(1.0)
    section.header_distance = Inches(0.5)
    section.footer_distance = Inches(0.5)


def parse_table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        value = lines[i].strip()
        cells = [cell.strip() for cell in value.strip("|").split("|")]
        if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            rows.append(cells)
        i += 1
    return rows, i


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = (ROOT / args.source).resolve()
    output = (ROOT / args.output).resolve()
    lines = source.read_text(encoding="utf-8").splitlines()
    doc = Document()
    configure_section(doc.sections[0])
    configure_style(doc.styles["Normal"], 12, after=7, line=1.5)
    configure_style(doc.styles["Title"], 21, bold=True, after=17, line=1.2)
    configure_style(doc.styles["Heading 1"], 15, bold=True, before=13, after=8, line=1.2)
    configure_style(doc.styles["Heading 2"], 12.5, bold=True, before=10, after=6, line=1.2)
    if "Table Text" not in doc.styles:
        from docx.enum.style import WD_STYLE_TYPE
        doc.styles.add_style("Table Text", WD_STYLE_TYPE.PARAGRAPH)
    configure_style(doc.styles["Table Text"], 10.5, after=0, line=1.15)

    on_cover = True
    in_references = False
    i = 0
    while i < len(lines):
        value = lines[i].rstrip()
        if not value:
            i += 1
            continue
        if value.startswith("# "):
            para = doc.add_paragraph(style="Title")
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_inline(para, value[2:], size=21)
            i += 1
            continue
        if value.startswith("## "):
            if on_cover:
                section = doc.add_section(WD_SECTION.NEW_PAGE)
                configure_section(section)
                section.footer.is_linked_to_previous = False
                add_page_field(section.footer.paragraphs[0])
                sectpr = section._sectPr
                pg = sectpr.find(qn("w:pgNumType"))
                if pg is None:
                    pg = OxmlElement("w:pgNumType")
                    sectpr.append(pg)
                pg.set(qn("w:start"), "1")
                on_cover = False
            if value.startswith("## 导师与第二阅卷人意见"):
                doc.add_page_break()
            in_references = value.startswith("## 9 ")
            para = doc.add_paragraph(style="Heading 1")
            para.paragraph_format.keep_with_next = True
            add_inline(para, value[3:], size=15)
            i += 1
            continue
        if value.startswith("### "):
            para = doc.add_paragraph(style="Heading 2")
            para.paragraph_format.keep_with_next = True
            add_inline(para, value[4:], size=12.5)
            i += 1
            continue
        if value.startswith("|"):
            rows, i = parse_table(lines, i)
            add_table(doc, rows)
            continue
        if re.match(r"^\d+\. ", value):
            para = doc.add_paragraph(style="Normal")
            para.paragraph_format.left_indent = Inches(0.28)
            para.paragraph_format.first_line_indent = Inches(-0.28)
            add_inline(para, value, size=12)
            i += 1
            continue
        if value.endswith("  "):
            value = value.rstrip()
        para = doc.add_paragraph(style="Normal")
        if on_cover and value.startswith(("课程：", "专业及班级：", "拟议导师：", "日期：")):
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if in_references:
            para.paragraph_format.line_spacing = 1.1
            para.paragraph_format.space_after = Pt(3)
            add_inline(para, value, size=11)
        else:
            add_inline(para, value, size=12)
        if value.startswith(("导师意见：", "第二阅卷人意见：")):
            for _ in range(3):
                space = doc.add_paragraph(style="Normal")
                space.paragraph_format.space_after = Pt(4)
        i += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    print(output)


if __name__ == "__main__":
    main()
