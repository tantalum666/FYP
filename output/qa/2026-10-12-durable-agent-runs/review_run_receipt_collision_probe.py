"""Synthetic local SQLite effect-key collision; no external side effects."""
import hashlib,tempfile
from pathlib import Path
from datetime import UTC,datetime,timedelta
from desk.runtime import Runtime
from desk.store import Store
from desk.sources import SourceInput
from desk.agent_run_schemas import RunCreate
clock=[datetime(2026,10,12,15,tzinfo=UTC)]
with tempfile.TemporaryDirectory() as directory:
 r=Runtime(Store(Path(directory),password='fixture-only',clock=lambda:clock[0]))
 token=r.store.authenticate('owner','fixture-only'); owner={'kind':'owner','session':token}; session=hashlib.sha256(token.encode()).hexdigest()
 source=r.sources.ingest(SourceInput(name='fixture.txt',format='text'),b'Selected fixture\n','source',session_hash=session)['source']
 run=r.agent_runs.create(RunCreate(goal='Create exact requested task',retain=True,source_ids=[source['id']],mutation_requests=[{'tool':'task_create_draft','arguments':{'title':'Requested exact title'}}],scope_revision=r.agent_runs.scope(owner)['scope_revision']),'run',owner)['run']
 prior=[]; original=r.agent_runs._dispatch_effect
 def collide(value):
  prior.append(r.assistant.tool('task_create_draft',{'title':'Different prior draft'},value['pending_effect']['key'])['proposal'])
  return original(value)
 r.agent_runs._dispatch_effect=collide
 for _ in range(12):
  r.agent_runs.advance_one(); clock[0]+=timedelta(seconds=2)
  d=r.agent_runs.detail(run['id'],owner)['run']
  if d['state'] in ('waiting_review','blocked'): break
 other=prior[0]
 print({'unrelated_draft_still_pending':any(p['id']==other['id'] for p in r.assistant.proposals()),'unrelated_draft_classified_as_run':r.agent_runs.is_run_proposal(other['id'])})
 print({'probe':'reserved_effect_key_collision','state':d['state'],'reason':d['state_reason'],'adopted_different_draft':other['id'] in d['proposal_ids']})
 if d['state']=='waiting_review':
  r.assistant.decide(other['id'],'confirm','fixture-confirm')
  for _ in range(12):
   r.agent_runs.advance_one(); clock[0]+=timedelta(seconds=2)
   d=r.agent_runs.detail(run['id'],owner)['run']
   if d['state'] in ('succeeded','partial','blocked'): break
  print({'terminal':d['state'],'saved_titles':[x['title'] for x in r.tasks.listing()['tasks']]})
