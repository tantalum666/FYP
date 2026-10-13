import json,sys,tempfile
from pathlib import Path
ROOT=Path('/workspace/shared/fyp-agent-20261012')
sys.path[:0]=[str(ROOT/'desk-companion/backend'),str(ROOT/'desk-companion/tests')]
from test_public_captures import world, prepare, approve, cancel, reconcile
with tempfile.TemporaryDirectory() as d:
 w=world.__wrapped__(Path(d)); s=w[4]; p=prepare(w); cid=p['capture']['id']; a=approve(w,p); s.run_one()
 result={'prepare':p,'approve':a,'detail':s.detail(cid,session_hash=w[1]),'list':s.listing(session_hash=w[1]),'reconcile':reconcile(w,cid),'metadata':s.detail(cid,session_hash=w[1],metadata_only=True)}
 q=prepare(w,key='second'); result['cancel']=cancel(w,q['capture']['id'])
 result['requests']=w[5].requests
 (ROOT/'output/qa/2026-10-13-public-capture-interface-audit/wire-fixtures.json').write_text(json.dumps(result,indent=2))
