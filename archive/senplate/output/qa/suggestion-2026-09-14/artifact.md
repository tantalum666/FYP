# Project Suggestion Template Contract

## Reference and evidence

- Original: `/Users/tantalum/Downloads/AY26_ProjectSuggestion_GroupX.docx`.
- Retained task copy: `/Users/tantalum/Documents/ChatGPT/FYP/output/qa/suggestion-2026-09-14/reference.docx`.
- SHA-256: `7cc26bead5d75b140a3044328bd724ac6e418dc5efaa703084f39b6d363b10d5`.
- Reference: 3 rendered pages, 1 section; all pages visually inspected in template-reference-render.
- Baseline parts, sizes, hashes: template-package-inventory.json. Section/style/heading/field/control audits are in this directory.

## Page and recurring components

Letter portrait 8.5 x 11 inches; margins 1 inch on all sides; header/footer distances 0.5 inch; one column and one section. Keep the header text and footer PAGE field unchanged. The header/footer parts and their relationships are preserve-only. No first/odd/even-page variation, images, drawings, text boxes, content controls or nonseparator footnotes/endnotes.

The page count may grow as editable fields are completed. Keep the general-information/member block coherent, and keep the endorsement section as a distinct page when content requires it. Page breaks before sections 2 and 5 may be used to preserve readable flow; this does not alter section geometry or the visual design.

## Typography and structure

Preserve all source styles and numbering parts. Normal style ID is a1; default text 11 pt, default spacing 10 pt after and line spacing 1.15. The source mainly uses direct formatting.

- Title block: centered; Calibri; first line 12 pt bold gray 595959, main title 20 pt bold blue 1F497D; preserve academic-year line and all original run treatment.
- Submission guide: 10 pt Calibri, original red/bold label and gray prose; preserve verbatim, with 12 pt before/after and 0.1-inch side indents.
- Numbered section headings: Calibri Light 16 pt bold blue 1F497D; keep-next; 12 pt before, 6 pt after. Preserve text and original direct formatting.
- Instruction prose: Calibri 10 pt italic gray 595959, 0.25-inch left indent, 6 pt after; preserve content.
- Editable narrative slots: Calibri 10.5 pt, 0.25-inch left indent, source paragraph 6 pt before and 12 pt after. Replace placeholder italic/gray with normal dark 333333 text and use bold labels within the slot; retain source font sizes and line spacing.
- General-information entries: Calibri 10.5 pt; member entries 10 pt. Replace placeholder italic/gray with normal dark 333333 text; role label may be bold. Keep original cell padding and table grids.

## Tables

General-information table: 4 rows, 2 columns, grid 3168/6192 twips. Left fill F2F2F2 and blue bold 10.5 pt labels; right fields editable. Member table: header plus four placeholder rows; grid 720/2160/1440/2160/2880 twips. Header blue 1F497D with white bold 10 pt text. Populate three students, remove the unused fourth placeholder row. Preserve table width, cell padding and original border treatment; no generic table redesign. Allow filled rows to grow without clipping. Keep each member row together.

Endorsement table: four rows, grid 3600/5760 twips, gray left cells and original text. Preserve every signature/date blank, the unchecked approval/rejection boxes and all supervisor-only text. This whole table is preserve-only, including its conditional student endorsement wording.

## Editable slot map

Locators refer to word/document.xml, body-direct paragraph/table order (1-based XPath). Verify the original labels and structure before editing.

- `w:body/w:tbl[1]/w:tr[1..4]/w:tc[2]`: title; proposed supervisor with verbal agreement pending; programme/class; Group 2.
- `w:body/w:tbl[2]/w:tr[2..4]/w:tc[1..5]`: serial, name, ID, email, role/responsibility with 40/30/30 planned workload. Delete `w:tr[5]` only.
- `w:body/w:p[9]`: Problem Statement and exactly three objectives.
- `w:body/w:p[12]`: Key Subsystems/Features and Expected Users/Roles, including required secondary menu/orders and a bounded six-month prototype.
- `w:body/w:p[15]`: Development Technologies/Tools and Special Considerations, including hardware, AI/IoT, environment, bilingual and regional configuration.
- `w:body/w:p[7]` and `w:body/w:p[16]`: only controlled pagination properties if required. Content unchanged.
- `w:body/w:p[6]`: empty spacer after the member table may be removed when the explicit section-2 break replaces its spacing; avoids a blank overflow page. It carries no content or field.

All other body content, especially Submission Guide and endorsement table, remains semantically unchanged. No new section is added. The supplied form has no requirement to keep exactly three output pages; more room is preferable to reducing the source text sizes.

## Package preservation and fields

Only word/document.xml and the intentional w:updateFields addition in word/settings.xml are editable. All other parts and relationships must have identical uncompressed bytes and hashes to the retained reference. Core/app properties, customXml, theme, styles, numbering, headers, footer and note parts remain present and unchanged. No macros or external links are added.

No Word desktop field-refresh operation has been performed. Set w:updateFields=true; retain PAGE field semantics. Verify page numbers in the rendered PDF. Do not round-trip the authoring DOCX through LibreOffice save.

## Final fidelity checks

Run reference/final render-and-diff in a new iteration directory; inspect every final page. Re-run section, style, field and control audits; compare preserve-only part inventory; verify all three member mappings and 100% total workload. Check for remaining placeholders only in intentionally untouched endorsement/approval areas. Confirm original and retained-reference hashes are unchanged. Deliver only the checked DOCX and matching PDF; QA records are internal.
