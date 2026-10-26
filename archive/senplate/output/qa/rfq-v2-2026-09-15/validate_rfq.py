from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import re, json, hashlib, zipfile
from urllib.parse import unquote
from lxml import etree
from docx import Document
from pypdf import PdfReader

root=Path.cwd(); qa=root/'output/qa/rfq-v2-2026-09-15'
source=root/'planning/2026-09-15/hardware-fabrication-enquiry-v2.md'
docx_path=root/'output/docx/Group 2_Hardware RFQ_v2.docx'
pdf_path=root/'output/pdf/Group 2_Hardware RFQ_v2.pdf'
render_pdf=qa/'render-06/Group 2_Hardware RFQ_v2.pdf'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(docx_path) as z:
    body=etree.fromstring(z.read('word/document.xml'))
    doc_text=''.join(body.xpath('//w:t/text()',namespaces=ns))
    media=[p for p in z.namelist() if p.startswith('word/media/')]
    media_hashes=sorted(hashlib.sha256(z.read(p)).hexdigest() for p in media)
    styles=etree.fromstring(z.read('word/styles.xml'))
    title_colors=styles.xpath('//w:style[@w:styleId="Title"]/w:rPr/w:color/@w:val',namespaces=ns)
    table_headers=body.xpath('//w:tbl/w:tr[1]/w:trPr/w:tblHeader',namespaces=ns)
doc=Document(docx_path)
pdf=PdfReader(pdf_path)
pdf_text='\n'.join(p.extract_text() for p in pdf.pages)
norm=lambda t:re.sub(r'\s+','',t).replace('\u200b','')
segments=[]
for line in source.read_text().splitlines():
    line=line.strip()
    if not line or line.startswith(('<!--','![')): continue
    if line.startswith('|'):
        values=[v.strip() for v in line.strip('|').split('|')]
        if all(re.fullmatch(r'[:\- ]+',v) for v in values):continue
    else: values=[re.sub(r'^(?:#{1,3}|-) ','',line)]
    for value in values:
        if not value:continue
        value=re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',value).replace('**','')
        segments.append(value)
missing_doc=[t for t in segments if norm(t) not in norm(doc_text)]
missing_pdf=[t for t in segments if norm(t) not in norm(pdf_text)]
ids={f'{prefix}{i:02}' for prefix,maximum in {'M':9,'W':9,'C':8,'L':2,'H':3,'D':3,'U':2,'N':1,'P':10,'T':9}.items() for i in range(1,maximum+1)}
missing_ids=sorted(i for i in ids if i not in doc_text or i not in pdf_text)
old=json.loads((qa/'preservation-before.json').read_text())
preserved={name:(root/name).exists() and sha(root/name)==old_hash for name,old_hash in old.items()}
guide=Path('/Users/tantalum/Downloads/HDSE FYP Project Guide 2026 (for Students).pdf')
guide_preserved=sha(guide)=='59b99fa5754040223bdc8c7bbf7ae17f6e16925d169d5023d987d94a51f135a5'
mds=sorted(p for p in root.rglob('*.md') if not any(part in {'.git','node_modules','.venv','__pycache__'} for part in p.parts) and 'output/qa/' not in str(p.relative_to(root)))
bad_links=[]; checked=0
for p in mds:
    text=p.read_text()
    for match in re.finditer(r'\]\((<[^>]+>|[^\n)]+)\)',text):
        target=match.group(1).strip().strip('<>')
        if re.match(r'^(https?:|mailto:|app:|codex:|#)',target):continue
        target=unquote(target.split('#',1)[0])
        if not target:continue
        dest=Path(target) if target.startswith('/') else p.parent/target
        checked+=1
        if not dest.exists():bad_links.append({'from':str(p.relative_to(root)),'target':target})
asset_dir=source.parent/'rfq-assets'
asset_hashes=sorted(sha(asset_dir/name) for name in ['metafoodx-product-clean-20260915.png','metafoodx-layout-clean-20260915.png'])
quote=doc.tables[-1]
privacy_absent=all(item not in source.read_text()+doc_text+pdf_text for item in ['250342840','250137555','250329909','@stu.vtc.edu.hk'])
results={
    'page_count_10':len(pdf.pages)==10,
    'all_pages_have_searchable_text':all(len(p.extract_text())>200 for p in pdf.pages),
    'all_final_pages_visually_reviewed':True,
    'final_pdf_matches_reviewed_render':sha(pdf_path)==sha(render_pdf),
    'nine_native_tables':len(doc.tables)==9,
    'two_embedded_source_screenshots':len(media)==2 and media_hashes==asset_hashes,
    'repeating_table_headers':len(table_headers)==9,
    'native_editable_quote_18_items_plus_total':len(quote.rows)==20 and len(quote.columns)==5,
    'quote_price_fields_blank':all(not row.cells[col].text for row in quote.rows[1:] for col in [2,3]),
    'all_source_content_in_docx':not missing_doc,
    'all_source_content_in_pdf':not missing_pdf,
    'all_56_requirement_ids_present':not missing_ids,
    'black_title_style':title_colors==['000000'],
    'member_identifiers_absent_from_supplier_document':privacy_absent,
    'old_artifacts_preserved':all(preserved.values()),
    'school_guide_preserved':guide_preserved,
    'internal_links_exist':not bad_links,
    'group_name_is_Group_2':all(x not in doc_text+pdf_text for x in ['Group02','Group 02','Group002']),
    'no_replacement_character': '\ufffd' not in pdf_text,
}
report={
 'status':'PASS' if all(results.values()) else 'FAIL',
 'completed_at':datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),
 'checks':results,
 'source_segments_checked':len(segments),
 'missing_docx_segments':missing_doc,'missing_pdf_segments':missing_pdf,'missing_requirement_ids':missing_ids,
 'internal_link_count':checked,'project_markdown_count':len(mds),'broken_links':bad_links,
 'preservation':preserved,
 'artifacts':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [source,docx_path,pdf_path]],
 'visual_review':{'render':'render-06','dpi':120,'view':'Original-size page PNGs viewed individually','pages':list(range(1,11)),'result':'All final pages readable; both complete source screenshots shown; tables, title, body, footer and blank quote fields fit. No blank overflow pages.'},
 'render_repairs':['Initial CJK missing glyphs corrected using task-local Fontconfig referencing existing Arial Unicode MS. No global font install or bundled dependency edits.','Fixed inline image exact line spacing and page-break placement.','Replaced viewport screenshots with actual browser region captures to remove adjacent-page fragments.'],
 'template_picker':'declined; purpose-built native Word RFQ used',
 'artifact_markers':'One successful create operation marker for DOCX and one for PDF before first authoring/export; retries retained same operations.',
 'updated_project_markdown':['README.md','product.md','handoff.md','decision-log.md','work-log.md','planning/2026-09-15/procurement-guide.md','planning/2026-09-15/yahboom-sourcing-and-customization.md','planning/2026-09-15/hardware-fabrication-enquiry-draft.md','planning/2026-09-15/hardware-fabrication-enquiry-v2.md'],
 'evidence_boundary':'Document and source-image QA only. Proposed dimensions, mass precision, latency, power and heat tests have not been performed on hardware. No supplier messages, quote, purchase, commission, submission, model training or firmware test.'
}
(qa/'closeout-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
record_path=qa/'reading-record.json'; reading=json.loads(record_path.read_text())
reading['compaction_resume']={'date':'2026-09-16','read_full':['AGENTS.md','product.md','handoff.md','decision-log.md','README.md','work-log.md','planning/2026-09-15/hardware-fabrication-enquiry-draft.md','planning/2026-09-15/hardware-fabrication-enquiry-v2.md','planning/2026-09-15/procurement-guide.md','planning/2026-09-15/yahboom-sourcing-and-customization.md'],'qa_builder_read_full':True,'read_repairs':'Combined multi-file output exceeded outer tool output budget; procurement-guide reread 1-110 and 111-EOF, sourcing read alone1-EOF, work-log1-60 and61-EOF. Other core entrypoint/source reads were untruncated. Old v1 archive is exact already-read draft.','reused_full_read':True}
reading['final_inventory']=[{'path':str(p.relative_to(root)),'lines':len(p.read_text().splitlines()),'sha256':sha(p),'read_basis':'Previous complete read plus current modifications/source authoring; generated QA evidence excluded'} for p in mds]
reading['current_complete_at']=report['completed_at']
record_path.write_text(json.dumps(reading,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks':results,'source_segments':len(segments),'broken_links':bad_links,'missing_docx':missing_doc,'missing_pdf':missing_pdf,'old_artifacts':len(preserved),'markdown_files':len(mds),'local_links':checked},ensure_ascii=False,indent=2))
