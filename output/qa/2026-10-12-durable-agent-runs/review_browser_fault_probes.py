"""Synthetic local regression probe: no browser, provider, or network dispatch."""
import hashlib, tempfile
from pathlib import Path
from desk.runtime import Runtime
from desk.store import Store, encode
from desk.schemas import SettingsInput
from desk.browser_jobs import BrowserService
from desk.browser_policy import PublicObservationInput, BrowserJobInput, BrowserApproval, digest, exclusive_write, source_entry, ADAPTER
from desk.browser_supervisor import WorkerOutcome

class FakeSupervisor:
 executable='/fixture/chromium'
 def __init__(self, export=False): self.executions=0; self.export=export
 def readiness(self): return None
 def run(self, payload, directory, checkpoint, on_start, **kw):
  on_start(12345)
  if payload['operation']=='observe':
   checkpoint('read_source')
   data={'source_id':payload['source_id'],'url':source_entry(payload['source_id'])['url'],'title':'Synthetic public fixture','heading':'Fixture','excerpt':'Public fixture paragraph'}
   return WorkerOutcome({**data,'sha256':digest(data),'observed_at':'2026-10-12T15:00:00+00:00'},None,False,True)
  self.executions+=1; checkpoint('open_editor')
  if not self.export: return WorkerOutcome(None,'BROWSER_WORKER_FAILED',True,True)
  intent=payload['intent']; body=intent['content'].encode()
  receipt={'verified':True,'adapter':ADAPTER,'catalog_version':1,'job_id':intent['job_id'],'execution_id':payload['execution_id'],'intent_hash':payload['intent_hash'],'source_sha256':intent['source']['sha256'],'environment_id':intent['environment_id'],'destination':intent['destination'],'document_name':intent['document_name'],'sha256':hashlib.sha256(body).hexdigest(),'byte_count':len(body),'download_count':1,'export_method':'stackedit_ui_markdown_download','browser_version':'synthetic-fixture','sandbox_requested':True,'browser_close_confirmed':True,'network_boundary':'routing_only','data_scope':'public_synthetic_only'}
  exclusive_write(directory,'export.md',body); exclusive_write(directory,'receipt.json',encode(receipt).encode())
  return WorkerOutcome(receipt,'BROWSER_DEADLINE_EXCEEDED',True,False,True)

def setup(root,export=False):
 r=Runtime(Store(root,password='fixture-only')); token=r.store.authenticate('owner','fixture-only'); session=hashlib.sha256(token.encode()).hexdigest()
 fake=FakeSupervisor(export); service=BrowserService(r,fake); service.enabled=True
 o=service.observe(PublicObservationInput(source_id='python_asyncio',public_only=True),'observe',session_hash=session)['observation']
 j=service.prepare(BrowserJobInput(observation_id=o['id'],title='Synthetic public probe',public_only=True),'prepare',session_hash=session)['job']
 service.approve(j['id'],BrowserApproval(expected_version=j['version'],intent_hash=j['intent_hash'],public_only=True),'approve',session_hash=session)
 return r,service,fake,j

with tempfile.TemporaryDirectory() as root:
 r,s,f,j=setup(Path(root))
 for hidden in (True,False):
  with r.store.connection() as c: settings=r.store.settings(c)
  r.store.update_settings(SettingsInput(expected_version=settings['version'],timezone=settings['timezone'],hide_private=hidden),f'hide-{hidden}')
 s.advance_one()
 print({'probe':'hide_show_before_dispatch','synthetic_execution_calls':f.executions,'state':s.detail(j['id'])['state']})
with tempfile.TemporaryDirectory() as root:
 r,s,f,j=setup(Path(root),export=True)
 s.advance_one(); d=s.detail(j['id']); caps=s.capabilities()
 print({'probe':'valid_bytes_unconfirmed_cleanup','state':d['state'],'cleanup_confirmed':d['cleanup_confirmed'],'new_admission_ready':caps['ready'],'note':'Synthetic fixture, no actual browser acceptance'})
