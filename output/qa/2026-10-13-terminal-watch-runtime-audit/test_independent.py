import sys, sqlite3, subprocess, hashlib, json, os
from pathlib import Path
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'desk-companion/tests'),str(ROOT/'desk-companion/backend')]
from test_responsibilities import world, task, create_payload, enroll, control, hide, login
from desk.responsibility_retention import RetentionPreviewRequest, RetentionAction, watch_accounting, TOMBSTONE
from desk.responsibilities import ResponsibilityService, ResponsibilityAction
from desk.store import Store, DomainError

def prep(w, watch, action):
    s=w[0].responsibilities
    with w[0].store.connection() as c: row=s._get(c,watch['id'])
    req=dict(action=action,expected_version=row['version'],expected_retention_version=row['retention_version'])
    p=s.retention_preview(watch['id'],RetentionPreviewRequest(**req),w[1])
    return RetentionAction(**req,preview_id=p['preview_id'],**({'confirm_permanent_removal':True} if action=='purge' else {}))
def apply(w,watch,action,key=None):
    return w[0].responsibilities.retention_action(watch['id'],prep(w,watch,action),key or uuid4().hex,w[1])
def terminal(w):
    return control(w,enroll(w,[task(w)]),'cancel')
def snapshot(store):
    with store.connection() as c:
        return {r[0]:[tuple(x) for x in c.execute('SELECT * FROM '+r[0])] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
def receipts(w, watch, target):
    with w[0].store.connection(write=True) as c:
        n=c.execute('SELECT COUNT(*) FROM responsibility_operations WHERE responsibility_id=?',(watch['id'],)).fetchone()[0]
        for i in range(target-n): c.execute('INSERT INTO responsibility_operations VALUES(?,?,?,?,?)',(uuid4().hex,'a'*64,watch['id'],None,'acknowledge'))

def test_capacity_recovery_concurrent_replay_and_independent_data(world):
    w=world; s=w[0].responsibilities; t=task(w)
    watches=[enroll(w,[t]) for _ in range(20)]
    watch=control(w,watches[0],'cancel'); before=snapshot(w[0].store)
    apply(w,watch,'trash')
    assert len(s.listing(w[1])['responsibilities'])==19
    assert s.listing(w[1])['maintenance_usage']['retained_count']==20
    with pytest.raises(DomainError,match='RESPONSIBILITY_LIMIT'): s.create(create_payload(w,[t]),uuid4().hex,w[1])
    apply(w,watch,'restore'); p=prep(w,watch,'purge'); key=uuid4().hex
    with ThreadPoolExecutor(4) as pool:
        results=list(pool.map(lambda _:s.retention_action(watch['id'],p,key,w[1]),range(8)))
    assert all(r==results[0] for r in results)
    assert s.listing(w[1])['maintenance_usage']['retained_count']==19
    enroll(w,[t]); assert s.listing(w[1])['maintenance_usage']['retained_count']==20
    after=snapshot(w[0].store)
    for name in before:
        if name not in {'state','responsibilities','responsibility_sources','responsibility_reviews','responsibility_operations'}: assert before[name]==after[name],name
    with w[0].store.connection() as c: assert c.execute("SELECT COUNT(*) FROM responsibility_operations WHERE kind='purge'").fetchone()[0]==1

@pytest.mark.parametrize('status',['active','paused','blocked'])
@pytest.mark.parametrize('action',['trash','purge'])
def test_nonterminal_refused(world,status,action):
    watch=enroll(world,[task(world)])
    with world[0].store.connection(write=True) as c: c.execute('UPDATE responsibilities SET status=?',(status,))
    before=snapshot(world[0].store)
    with pytest.raises(DomainError,match='RESPONSIBILITY_NOT_TERMINAL'): prep(world,watch,action)
    assert before==snapshot(world[0].store)

@pytest.mark.parametrize('value',[None,False,1,'true'])
def test_strict_final_confirmation(world,value):
    from pydantic import ValidationError
    watch=terminal(world); p=prep(world,watch,'purge').model_dump()
    p['confirm_permanent_removal']=value
    with pytest.raises(ValidationError): RetentionAction(**p)

@pytest.mark.parametrize('change',['expiry','backward_wall','monotonic','session','personal','settings','inventory','restart','evict'])
def test_preview_fences_and_zero_writes(world,change):
    w=world; s=w[0].responsibilities; watch=terminal(w); p=prep(w,watch,'purge')
    if change=='expiry': w[2][0]+=timedelta(minutes=5)
    elif change=='backward_wall': w[2][0]-=timedelta(seconds=1)
    elif change=='monotonic': s.retention_previews.monotonic=lambda:float('inf')
    elif change=='session': login(w)
    elif change=='personal':
        with w[0].store.connection(write=True) as c:c.execute('UPDATE personal_settings SET epoch=epoch+1')
    elif change=='settings': hide(w,True);hide(w,False)
    elif change=='inventory':
        with w[0].store.connection(write=True) as c:c.execute('UPDATE responsibility_sources SET dirty_generation=dirty_generation+1')
    elif change=='restart': w[0].responsibilities=ResponsibilityService(w[0])
    elif change=='evict':
        for _ in range(32):prep(w,watch,'purge')
    before=snapshot(w[0].store)
    with pytest.raises(DomainError):w[0].responsibilities.retention_action(watch['id'],p,uuid4().hex,w[1])
    assert before==snapshot(w[0].store)

def test_original_keys_survive_dependency_deletion_and_preview_restart(world):
    w=world;s=w[0].responsibilities;t=task(w);payload=create_payload(w,[t]);key=uuid4().hex
    watch=s.create(payload,key,w[1])['responsibility'];watch=control(w,watch,'cancel');p=prep(w,watch,'purge');pk=uuid4().hex
    s.retention_action(watch['id'],p,pk,w[1]);w[0].responsibilities=ResponsibilityService(w[0]);s=w[0].responsibilities
    w[2][0]+=timedelta(minutes=6)
    with w[0].store.connection(write=True) as c:c.execute('DELETE FROM tasks WHERE id=?',(t['id'],))
    before=snapshot(w[0].store)
    assert s.create(payload,key,w[1])['retention_state']=='purged'
    assert s.retention_action(watch['id'],p,pk,w[1])['recorded_success'] is True
    with pytest.raises(DomainError,match='OPERATION_ID_CONFLICT'):s.create(payload.model_copy(update={'title':'different'}),key,w[1])
    with pytest.raises(DomainError,match='OPERATION_ID_CONFLICT'):s.retention_action('other',p,pk,w[1])
    assert before==snapshot(w[0].store)

@pytest.mark.parametrize('count,allowed',[(254,True),(255,False)])
def test_restore_reserved(world,count,allowed):
    w=world;watch=terminal(w);receipts(w,watch,count)
    if not allowed:
        with pytest.raises(DomainError,match='RESPONSIBILITY_OPERATION_LIMIT'):prep(w,watch,'trash')
        return
    apply(w,watch,'trash');apply(w,watch,'restore')
    with w[0].store.connection() as c:assert c.execute('SELECT COUNT(*) FROM responsibility_operations').fetchone()[0]==256
    with pytest.raises(DomainError,match='RESPONSIBILITY_OPERATION_LIMIT'):prep(w,watch,'trash')
    apply(w,watch,'purge')

def test_maximum259(world):
    w=world;watch=enroll(w,[task(w)]);receipts(w,watch,256)
    watch=control(w,watch,'pause');watch=control(w,watch,'cancel');apply(w,watch,'purge')
    with w[0].store.connection() as c:assert c.execute('SELECT COUNT(*) FROM responsibility_operations').fetchone()[0]==259

@pytest.mark.parametrize('corruption',["data='{}'","purged_at=NULL","status='active'","retention_version=0"])
def test_malformed_shell_never_free_capacity(world,corruption):
    w=world;watch=terminal(w);apply(w,watch,'purge')
    with w[0].store.connection(write=True) as c:c.execute('UPDATE responsibilities SET '+corruption)
    with w[0].store.connection() as c:assert watch_accounting(c)['retained_count'] is None
    with pytest.raises(DomainError,match='RESPONSIBILITY_METADATA_UNAVAILABLE'):enroll(w,[task(w)])

def test_hidden_maintenance_rejected_and_safe_stop(world):
    w=world;watch=terminal(w);p=prep(w,watch,'purge');hide(w,True)
    before=snapshot(w[0].store)
    for call in [lambda:w[0].responsibilities.maintenance_listing(w[1]),lambda:w[0].responsibilities.maintenance_detail(watch['id'],w[1]),lambda:w[0].responsibilities.retention_action(watch['id'],p,uuid4().hex,w[1])]:
        with pytest.raises(DomainError,match='PRIVATE_CONTEXT_HIDDEN'):call()
    listing=w[0].responsibilities.listing(w[1]);assert listing['hidden'] and 'title' not in json.dumps(listing)
    assert before==snapshot(w[0].store)

def legacy(store):
    with store.connection(write=True) as c:
        for row in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'responsibility_%'").fetchall(): c.execute('DROP TRIGGER '+row[0])
        for name in ['responsibilities_retained','responsibilities_charged']: c.execute('DROP INDEX '+name)
        for name in ['retention_state','retention_version','trashed_at','restored_at','purged_at']:c.execute('ALTER TABLE responsibilities DROP COLUMN '+name)
        c.execute('PRAGMA user_version=1')

def test_store_legacy_explicit_optin_and_existing_current(world):
    w=world;watch=terminal(w);before=snapshot(w[0].store);legacy(w[0].store);b=snapshot(w[0].store)
    with pytest.raises(DomainError,match='SCHEMA_MIGRATION_REQUIRED'):Store(w[0].store.directory,password='fixture-only')
    assert b==snapshot(w[0].store)
    s=Store(w[0].store.directory,password='fixture-only',allow_watch_retention_migration=True)
    assert before==snapshot(s)
    assert before==snapshot(Store(s.directory,password='fixture-only'))
    with s.connection() as c:
        assert c.execute('PRAGMA user_version').fetchone()[0]==2
        triggers=c.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'responsibility_%'").fetchall()
        assert len(triggers)==5 and all("retention_state='retained'" in r[0] for r in triggers)

@pytest.mark.parametrize('mode',['forward','partial','version0'])
def test_store_refusal_before_bootstrap(world,mode):
    s=world[0].store
    with s.connection(write=True) as c:
        if mode=='forward':c.execute('PRAGMA user_version=999')
        elif mode=='version0':c.execute('PRAGMA user_version=0')
        else:c.execute('ALTER TABLE responsibilities DROP COLUMN restored_at')
    before=snapshot(s);files={p.name:p.read_bytes() for p in s.directory.glob('credentials*')}
    with pytest.raises(DomainError):Store(s.directory,allow_watch_retention_migration=True)
    assert before==snapshot(s)
    assert files=={p.name:p.read_bytes() for p in s.directory.glob('credentials*')}

@pytest.mark.parametrize('step',range(1,26))
def test_migration_process_exit_atomic(world,step):
    s=world[0].store;terminal(world);legacy(s);before=snapshot(s)
    child=''' 
import sys,os
from contextlib import contextmanager
from desk.store import Store
original=Store.connection
class Proxy:
 def __init__(self,c):self.c=c;self.n=0
 def __getattr__(self,n):return getattr(self.c,n)
 def execute(self,sql,*a):
  result=self.c.execute(sql,*a)
  text=sql.lstrip().upper()
  if (text.startswith(('ALTER','CREATE','DROP')) and 'RESPONSIBILIT' in text) or text.startswith('PRAGMA USER_VERSION='):
   self.n+=1
   if self.n==int(sys.argv[2]):os._exit(73)
  return result
@contextmanager
def intercepted(self,write=False):
 with original(self,write=write) as c:yield Proxy(c) if write else c
 if write and int(sys.argv[2])==25:os._exit(73)
Store.connection=intercepted
Store(sys.argv[1],password='fixture-only',allow_watch_retention_migration=True)
'''
    r=subprocess.run([sys.executable,'-c',child,str(s.directory),str(step)],env={**os.environ,'PYTHONPATH':str(ROOT/'desk-companion/backend')},capture_output=True)
    assert r.returncode==73,(r.returncode,r.stderr)
    if step<25:
        assert before==snapshot(s)
        with s.connection() as c:assert c.execute('PRAGMA user_version').fetchone()[0]==1
    else:
        with s.connection() as c:
            assert c.execute('PRAGMA user_version').fetchone()[0]==2
            assert c.execute('SELECT retention_state FROM responsibilities').fetchone()[0]=='retained'


def test_lifetime256_and_original_recovery(world):
    w=world;watch=terminal(w);apply(w,watch,'purge')
    with w[0].store.connection(write=True) as c:
        source=dict(c.execute('SELECT * FROM responsibilities').fetchone());cols=list(source)
        for i in range(255):
            source['id']=uuid4().hex
            c.execute('INSERT INTO responsibilities('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',[source[k] for k in cols])
            c.execute('INSERT INTO responsibility_operations VALUES(?,?,?,?,?)',(uuid4().hex,'b'*64,source['id'],None,'purge'))
    with w[0].store.connection() as c:
        usage=watch_accounting(c);assert usage['lifetime_count']==256 and usage['retained_count']==0
    with pytest.raises(DomainError,match='RESPONSIBILITY_METADATA_LIMIT'):enroll(w,[task(w)])

@pytest.mark.parametrize('flag',[False,True])
def test_cli_missing_runtime_never_creates(tmp_path,flag):
    missing=tmp_path/'missing'
    command=[sys.executable,str(ROOT/'desk-companion/scripts/migrate_watch_retention.py'),'--runtime',str(missing)]
    if flag:command+=['--allow-watch-retention-migration']
    result=subprocess.run(command,capture_output=True)
    assert result.returncode!=0 and not missing.exists()

@pytest.mark.parametrize('step',range(1,7))
def test_purge_process_exit_atomic(world,step):
    w=world;s=w[0].store;watch=terminal(w);before=snapshot(s)
    child='''
import sys,os,json
from contextlib import contextmanager
from datetime import datetime
from desk.store import Store
from desk.runtime import Runtime
from desk.responsibilities import ResponsibilityService
from desk.responsibility_retention import RetentionPreviewRequest,RetentionAction
r=Runtime(Store(sys.argv[1],clock=lambda:datetime.fromisoformat(sys.argv[5]),password='fixture-only'));s=r.store
service=ResponsibilityService(r);owner={'kind':'owner','session':sys.argv[3]}
with s.connection() as c:row=service._get(c,sys.argv[2])
data=dict(action='purge',expected_version=row['version'],expected_retention_version=row['retention_version'])
preview=service.retention_preview(sys.argv[2],RetentionPreviewRequest(**data),owner)
payload=RetentionAction(**data,preview_id=preview['preview_id'],confirm_permanent_removal=True)
original=s.connection
class Proxy:
 def __init__(self,c):self.c=c;self.n=0
 def __getattr__(self,n):return getattr(self.c,n)
 def execute(self,sql,*a):
  result=self.c.execute(sql,*a)
  if sql.lstrip().upper().startswith(('DELETE','UPDATE','INSERT')):
   self.n+=1
   if self.n==int(sys.argv[4]):os._exit(74)
  return result
@contextmanager
def intercepted(write=False):
 with original(write=write) as c:
  yield Proxy(c) if write else c
 if write and int(sys.argv[4])==6:os._exit(74)
s.connection=intercepted
service.retention_action(sys.argv[2],payload,'independent-crash-key',owner)
'''
    r=subprocess.run([sys.executable,'-c',child,str(s.directory),watch['id'],w[1]['session'],str(step),w[2][0].isoformat()],env={**os.environ,'PYTHONPATH':str(ROOT/'desk-companion/backend')},capture_output=True)
    assert r.returncode==74,(r.returncode,r.stderr)
    after=snapshot(s)
    if step<6:assert before==after
    else:
        assert len(after['responsibility_sources'])==0
        assert after['responsibilities'][0][1]==TOMBSTONE
        assert len(after['responsibility_operations'])==len(before['responsibility_operations'])+1
        with s.connection() as c: assert watch_accounting(c)['retained_count']==0

@pytest.mark.parametrize('state',['trashed','purged'])
def test_corrupt_nonretained_status_never_worker_or_trigger(world,state):
    w=world;t=task(w);watch=control(w,enroll(w,[t]),'cancel');apply(w,watch,'trash' if state=='trashed' else 'purge')
    with w[0].store.connection(write=True) as c:
        c.execute("UPDATE responsibilities SET status='active',expires_at='2000-01-01T00:00:00Z'")
        c.execute('UPDATE tasks SET version=version+1 WHERE id=?',(t['id'],))
    before=snapshot(w[0].store)
    assert w[0].responsibilities.advance()==0
    assert before==snapshot(w[0].store)

def test_postcommit_personal_epoch_denial_recovers_original(world,monkeypatch):
    w=world;s=w[0].responsibilities;watch=terminal(w);p=prep(w,watch,'purge');key=uuid4().hex
    original=s._reply
    def changed(*a,**kw):
        with w[0].store.connection(write=True) as c:c.execute('UPDATE personal_settings SET epoch=epoch+1')
        return original(*a,**kw)
    monkeypatch.setattr(s,'_reply',changed)
    with pytest.raises(DomainError,match='RESPONSIBILITY_CONTEXT_CHANGED'):s.retention_action(watch['id'],p,key,w[1])
    monkeypatch.setattr(s,'_reply',original)
    before=snapshot(w[0].store)
    assert s.retention_action(watch['id'],p,key,w[1])['retention_state']=='purged'
    assert before==snapshot(w[0].store)

@pytest.mark.parametrize('table',['owner','settings','state'])
def test_missing_singleton_no_credentials_or_ddl(world,table):
    s=world[0].store
    with s.connection(write=True) as c:c.execute('DELETE FROM '+table)
    before=snapshot(s)
    with pytest.raises(DomainError):Store(s.directory,allow_watch_retention_migration=True)
    assert before==snapshot(s) and not (s.directory/'credentials.json').exists()

@pytest.mark.parametrize('count',[259,260])
def test_malformed_excess_receipts_no_extra_purge(world,count):
    w=world;watch=terminal(w);receipts(w,watch,count);before=snapshot(w[0].store)
    with pytest.raises(DomainError):prep(w,watch,'purge')
    assert before==snapshot(w[0].store)


def test_http_lifecycle_and_current_capacity(tmp_path):
    from fastapi.testclient import TestClient
    from desk.app import create_app
    app=create_app(tmp_path,password='fixture-only',scheduler=False)
    r=app.state.runtime
    with TestClient(app) as client:
        h={'X-Desk-Request':'1'}
        assert client.post('/api/session',headers=h,json={'username':'owner','password':'fixture-only'}).status_code==200
        w=(r,{'kind':'owner','session':client.cookies.get('desk_companion_session')},[r.store.clock()])
        watch=terminal(w);url='/api/responsibilities/'+watch['id'];p=prep(w,watch,'trash')
        before=snapshot(r.store)
        assert client.post(url+'/retention',json=p.model_dump(exclude_unset=True)).status_code==403
        assert client.post(url+'/retention',headers={**h,'Origin':'https://attacker.invalid','X-Operation-Id':'a'},json=p.model_dump(exclude_unset=True)).status_code==403
        assert before==snapshot(r.store)
        response=client.post(url+'/retention',headers={**h,'X-Operation-Id':'trash-api'},json=p.model_dump(exclude_unset=True))
        assert response.status_code==200 and response.json()['retention_state']=='trashed'
        assert client.get(url).status_code==409
        assert client.get(url+'/maintenance').status_code==200
        assert client.get('/api/responsibilities').json()['maintenance_usage']['retained_count']==1
        p=prep(w,watch,'purge');data=p.model_dump(exclude_unset=True)
        for value in [0,1,'true',False,None]:
            response=client.post(url+'/retention',headers={**h,'X-Operation-Id':'purge-api'},json={**data,'confirm_permanent_removal':value})
            assert response.status_code==422
        response=client.post(url+'/retention',headers={**h,'X-Operation-Id':'purge-api'},json=data)
        assert response.status_code==200 and response.json()['retention_state']=='purged'
        assert client.get(url+'/maintenance').status_code==410
        assert client.get('/api/responsibilities').json()['maintenance_usage']['retained_count']==0
        assert client.post(url+'/retention',headers={**h,'X-Operation-Id':'purge-api'},json=data).json()==response.json()
        assert response.headers['cache-control']=='no-store'

@pytest.mark.parametrize('column',['retention_state','retention_version','trashed_at','restored_at','purged_at'])
def test_accounting_never_materializes_unbounded_corrupt_scalars(world,column):
    w=world;enroll(w,[task(w)])
    with w[0].store.connection(write=True) as c:c.execute('UPDATE responsibilities SET '+column+'=?',('x'*1048576,))
    sizes=[]
    class Result:
        def __init__(self,cur):self.cur=cur
        def fetchall(self):
            rows=self.cur.fetchall();sizes.extend(len(v) for row in rows for v in row if isinstance(v,(str,bytes)));return rows
    class Trace:
        def __init__(self,c):self.c=c
        def execute(self,*a):return Result(self.c.execute(*a))
    with w[0].store.connection() as c:usage=watch_accounting(Trace(c))
    assert usage['state']=='unavailable' and usage['retained_count'] is None
    assert max(sizes,default=0)<=100

def test_coherent_wal_backup_and_isolated_intentional_rollback(world,tmp_path):
    w=world;s=w[0].store;watch=terminal(w);legacy(s)
    source=sqlite3.connect(s.path)
    source.execute('PRAGMA wal_autocheckpoint=0')
    source.execute("INSERT INTO records(at,action,event_id,details) VALUES('2026-10-13','backup-fixture',NULL,'{}')")
    source.commit()
    before=snapshot(s)
    backup=tmp_path/'verified-backup.sqlite3'
    target=sqlite3.connect(backup)
    source.backup(target)
    assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert target.execute('PRAGMA user_version').fetchone()[0]==1
    assert target.execute("SELECT COUNT(*) FROM records WHERE action='backup-fixture'").fetchone()[0]==1
    target.close();source.close()
    Store(s.directory,password='fixture-only',allow_watch_retention_migration=True)
    with s.connection(write=True) as c:c.execute("INSERT INTO records(at,action,event_id,details) VALUES('2026-10-13','post-backup-change',NULL,'{}')")
    restored=sqlite3.connect(backup)
    snapshot_copy={r[0]:[tuple(x) for x in restored.execute('SELECT * FROM '+r[0])] for r in restored.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    restored.close()
    assert before==snapshot_copy
    assert before!=snapshot(s) # Restoration is separate and loses later changes; no automatic rollback.

@pytest.mark.parametrize('name',['purge','retention_action','responsibility_purge','maintenance_preview'])
def test_model_and_voice_dispatch_never_authorize_maintenance(world,name):
    import asyncio
    from types import SimpleNamespace
    from desk.agent_tools import validate_tool_call,tool_registry
    from desk.assistant import TOOLS
    from desk.tool_dispatch import ToolDispatcher
    w=world;watch=terminal(w);p=prep(w,watch,'purge');arguments={**p.model_dump(exclude_unset=True),'responsibility_id':watch['id']}
    before=snapshot(w[0].store)
    assert name not in tool_registry(w[0]) and name not in {t['name'] for t in TOOLS}
    with pytest.raises(DomainError,match='RUN_TOOL_NOT_ALLOWED'):validate_tool_call(w[0],{},SimpleNamespace(tool=name,arguments=arguments))
    with pytest.raises(DomainError,match='TOOL_NOT_ALLOWED'):w[0].assistant.tool(name,arguments,'model-fake-confirm',principal=w[1])
    async def dispatch():
        d=ToolDispatcher(w[0],'fixture-session')
        d.submit({'id':'fake-confirm','name':name,'arguments':arguments})
        _,result=await asyncio.wait_for(d.results.get(),3)
        assert result=={'error':'TOOL_NOT_ALLOWED','saved':False}
        await d.close()
    asyncio.run(dispatch())
    assert before==snapshot(w[0].store)

@pytest.mark.parametrize('body',['{broken','{}','x'*1048576],ids=['broken-json','missing-fields','oversized-body'])
def test_hidden_http_stop_survives_corrupt_private_body(tmp_path,body):
    from fastapi.testclient import TestClient
    from desk.app import create_app
    app=create_app(tmp_path,password='fixture-only',scheduler=False);r=app.state.runtime
    with TestClient(app) as client:
        h={'X-Desk-Request':'1'}
        client.post('/api/session',headers=h,json={'username':'owner','password':'fixture-only'})
        w=(r,{'kind':'owner','session':client.cookies.get('desk_companion_session')},[r.store.clock()])
        watch=enroll(w,[task(w)])
        with r.store.connection(write=True) as c:c.execute('UPDATE responsibilities SET data=?',(body,))
        assert client.get('/api/responsibilities').status_code==409
        hide(w,True)
        response=client.get('/api/responsibilities')
        assert response.status_code==200,response.text
        assert 'title' not in response.text and 'task_ids' not in response.text and len(response.content)<5000
        for action in ['pause','cancel']:
            with r.store.connection() as c:version=c.execute('SELECT version FROM responsibilities').fetchone()[0]
            response=client.post('/api/responsibilities/'+watch['id']+'/actions',headers={**h,'X-Operation-Id':action+'-hidden'},json={'action':action,'expected_version':version})
            assert response.status_code==200,response.text
            assert response.json()['responsibility']['status']==('paused' if action=='pause' else 'cancelled')
            assert 'title' not in response.text and 'task_ids' not in response.text
        hide(w,False)
        assert client.get('/api/responsibilities').status_code==409

def test_hidden_stop_never_decodes_private_body(world,monkeypatch):
    import desk.responsibilities as module
    w=world;watch=enroll(w,[task(w)]);hide(w,True)
    def forbidden(*a):raise AssertionError('Hidden stop decoded private body')
    monkeypatch.setattr(module,'decode_body',forbidden)
    s=w[0].responsibilities
    assert s.listing(w[1])['hidden']
    for action in ['pause','cancel']:
        with w[0].store.connection() as c:version=c.execute('SELECT version FROM responsibilities').fetchone()[0]
        result=s.action(watch['id'],ResponsibilityAction(action=action,expected_version=version),action+'-hidden',w[1])
        assert result['responsibility']['hidden'] and 'title' not in result['responsibility']


def test_receipt_corruption_is_not_false_body_count_overflow(world):
    from desk.work_capacity import WorkCapacityService
    w=world;watch=terminal(w);receipts(w,watch,260)
    with w[0].store.connection() as c:
        count=WorkCapacityService._watches(c).count
        assert count.state=='unavailable' and count.used is None and count.remaining is None
