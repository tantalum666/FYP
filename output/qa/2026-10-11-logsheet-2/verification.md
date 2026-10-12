# Group 2 Log Sheet No 2 verification

2026-10-11. Local document complete; not submitted.

## Reading and source control

138 project-owned Markdown files, 12,819 lines, 49 emitted and observed batches; every range acknowledged. Full reading completed at 13:43:08+08:00, with no source change during reading. The entry files were reread after compaction and reading resumed at the pending batch. `reading-record.json` contains the inventory, line counts, ranges, exclusions and timestamps. `artifact.md` is generated task evidence and excluded from the project Markdown inventory.

The user supplied v5 and confirmed that the hardware members have prepared a materials purchasing list. `provided_template-source.json` and `previous_log-source.json` preserve absolute locations, bytes and SHA256. The group JSON was read for names / IDs / programme / class; its historical food scope was not used for the new log.

## Content

No 2 covers 28 September to 11 October 2026, continuing the previous explicitly recorded next period. Date is 11 October; proposed next work is 12 to 25 October. Progress I preparation for 26 October comes from the dated project schedule; no current log-upload deadline is asserted.

Named entries preserve the latest software / AI versus hardware split. The hardware list is joint work for member review; no exact line items, personal authorship shares, orders, wiring, assembly or measured performance have been invented. Proposed next hardware checks are identified for member review. AI assistance is declared in the actual v5 Part III; Qwen / Gemini adapters are not presented as services already used in natural-voice trials. Supervisor's Feedback is intentionally blank.

## Authoring and visual QA

Documents skill applied. The edit marker succeeded exactly once immediately before the first DOCX authoring command, expected output count 2. Used the bundled Python and Node. LibreOffice was resolved through the bundled override at `/Users/tantalum/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice`, which uses the bundled headless LibreOffice, not a desktop installation.

- Original render: two pages, one complete school form and one blank tail, both viewed.
- Initial filled render: same visible school layout and blank tail; both viewed. The first-page-only visual impression was corrected when PDF page count was checked.
- Repair: only the required empty paragraph after the table reduced to 1 pt, without changing visible content or table geometry.
- Final render `render-02`: exactly one page, viewed at native resolution. First-page pixels match the initial filled render exactly; all entered text, names, IDs, date, declaration and borders are readable, with no overlap / clipping. Feedback remains blank.
- Canonical `render_docx.py` exported the inspected PDF. The paired final PDF is byte-identical to that export.
- `render_and_diff.py` compared the initial filled file with the retained template; final repair was checked by exact page-one pixel comparison, PDF count and structural invariants.

## Structural and content checks

`document-validation.json` records passing assertions: only `word/document.xml` changed; section / page / table / row / cell geometry retained; all non-fill cells retained; no added controls or tracked revisions; supervisor feedback blank; source and previous-log hashes unchanged; one final page; all required text extractable; all character bounds within the page.

Before / after style, section, fields and controls audits were run. The original uses Times New Roman and direct table-label formatting; those inherited labels are retained. Filled prose is 11 pt, metadata names / IDs 10.5 pt, and remaining metadata / original school labels 12 pt. There are no fields requiring materialisation. An initial wrong CLI flag and unavailable `fitz` check were corrected using each script's actual interface and the already bundled `pypdf` / `pdfplumber`; no dependency was installed.

## Documentation and remaining action

Updated product, root README, inputs README, decision log, handoff and work log; added `planning/2026-10-11/logsheet-2-review.md` and the deterministic builder. Current handoff contains one next step: members review their attribution and proposed plans, then the appropriate person submits according to the current course notice. A1 / E1 / C1 remain preserved and pending direction feedback.

Final local-link, identity, unchanged-original and deliverable checks are recorded in `closeout-validation.json`. App source, current runtime, old school files and character assets were not edited; no app tests were rerun. No Git write, purchase, hardware operation, paid model call, external message, signature, supervisor approval or Moodle submission was performed.
