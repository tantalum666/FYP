"""Synthetic public observation only, with no browser or network."""
import hashlib,tempfile
from pathlib import Path
from desk.runtime import Runtime
from desk.store import Store, DomainError
from desk.browser_jobs import BrowserService
from desk.browser_policy import PublicObservationInput, digest, source_entry
from desk.browser_supervisor import WorkerOutcome
class RestartingSupervisor:
 executable='/fixture/chromium'
 def readiness(self): return None
 def run(self,payload,directory,checkpoint,on_start,**kwargs):
  on_start(12345)
  BrowserService(runtime,self) # New service marks the old in-flight observation failed.
  checkpoint('read_source')
  self.post_restart_dispatch=True
  data={'source_id':payload['source_id'],'url':source_entry(payload['source_id'])['url'],'title':'Synthetic fixture','heading':'Fixture','excerpt':'Public fixture'}
  return WorkerOutcome({**data,'sha256':digest(data),'observed_at':'2026-10-12T15:00:00+00:00'},None,False,True)
with tempfile.TemporaryDirectory() as root:
 runtime=Runtime(Store(Path(root),password='fixture-only'))
 token=runtime.store.authenticate('owner','fixture-only'); session=hashlib.sha256(token.encode()).hexdigest()
 fake=RestartingSupervisor(); fake.post_restart_dispatch=False
 service=BrowserService(runtime,fake); service.enabled=True
 try:
  service.observe(PublicObservationInput(source_id='python_asyncio',public_only=True),'observe',session_hash=session)
  outcome='returned_observation'
 except DomainError as error: outcome=error.code
 with runtime.store.connection() as conn: state=conn.execute('SELECT state FROM browser_observations').fetchone()[0]
 print({'probe':'observation_service_restart','post_restart_dispatch':fake.post_restart_dispatch,'response':outcome,'persisted_state':state})
