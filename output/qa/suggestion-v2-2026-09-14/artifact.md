# Suggestion V2 Template Contract

## Reference

Retained V1: `/Users/tantalum/Documents/ChatGPT/FYP/output/qa/suggestion-v2-2026-09-14/reference-v1.docx`.
Source output: `/Users/tantalum/Documents/ChatGPT/FYP/output/docx/AY26_ProjectSuggestion_Group 2.docx`.
SHA-256: `dbbc4efa0c1a0f6a58041558ff1dbdf52f189fb8608552558c391bf9ec59d3b4`.
V1 has four pages, all inspected in the previous fidelity-02 run and matched to this unchanged hash. Source original template is also preserved. Package inventory: reference-package-inventory.json; V1 preservation hashes: v1-preservation-before.json.

## Preserved design

One Letter portrait section, 8.5 x 11 inches; 1-inch margins; header/footer offsets 0.5 inch. Keep school header, PAGE field, original title block, all numbered section headings and instructions, table grids, cell margins, source fonts, fills and border treatment.

The source uses Normal style a1 with direct formatting: Calibri body, 10.5 pt narrative and general entries, 10 pt member entries; numbered headings Calibri Light 16 pt bold blue 1F497D; member header fill 1F497D and white text; metadata/endorsement left cells F2F2F2. Narrative slots have 0.25-inch left indent, 6 pt before/12 pt after and inherited 1.15 line spacing. Source narrative text is dark 333333 with bold labels. General grid: 3168/6192 twips; member grid: 720/2160/1440/2160/2880; endorsement: 3600/5760. Keep all three member rows together, no fixed heights or font reduction.

V1 contains 16 body-direct paragraphs and 3 tables; no images, drawings, text boxes, content controls or nonseparator notes. Keep all styles, numbering, custom XML, relationships, metadata and header/footer parts byte-identical. Existing settings already have updateFields=true; do not rewrite settings.

## Allowed edits

In word/document.xml only, using zero-based body-direct paragraph indices:

- Table 0 right cells of rows 0 and 1: new broader project title and Marco with revised-scope review status.
- Table 1 last-column cells in member rows 1–3: update responsibility summaries, retaining names/IDs/emails, percentages and roles.
- Paragraph 7: problem statement and exactly three objectives.
- Paragraph 10: shared functions, three application profiles, limited prototype and users.
- Paragraph 13: technical stack, nutrition data, environmental benefit, bilingual/local configuration, and evidence/privacy limits.
- Paragraph 11: pageBreakBefore may be added so section 4 starts on page 3 as in V1, independent of revised text length.

All other body content and the whole endorsement table remain unchanged. The project name is a field within the supplied form, not a replacement for its school title. All signatures, dates and approval/rejection choices stay blank.

## Validation

Build to a separate v2 DOCX and export a matching v2 PDF; do not overwrite V1 files or its builder. Use the bundled renderer and a new reference/final fidelity directory, inspect every final page at original resolution, verify page numbers and no orphan labels or clipped content. Target four pages without reducing fonts. Verify only word/document.xml differs from V1, section/table geometry unchanged, preserved endorsement and all member fields intact. Recheck V1 DOCX/PDF/builder hashes after authoring. The canonical current group JSON may change; its V1 snapshot is preserved separately.
