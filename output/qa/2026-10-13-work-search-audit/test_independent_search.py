"""Independent boundary tests; synthetic metadata, real isolated SQLite, no services."""
import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import pytest
from desk.store import Store, DomainError, encode
from desk.runtime import Runtime
from desk.work_search import WorkSearchService, WorkSearchInput

@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026,10,13,tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password='audit-fixture', clock=lambda: clock[0]))
    token = runtime.store.authenticate('owner','audit-fixture')
    return runtime, hashlib.sha256(token.encode()).hexdigest(), clock

def run(world, n, goal='Find Alpha', **fields):
    r,s,_=world
    rid=f'{n:032x}'
    data=dict(goal=goal,mode='deterministic',plan_revision=1,source_ids=[],artifact_ids=[],current_artifact_ids=[],**fields)
    with r.store.connection(write=True) as c:
        c.execute('INSERT INTO agent_runs VALUES(?,?,1,1,NULL,?,?,?)',(rid,'paused',s,encode(data),'2026-10-12T00:00:00Z'))
    return rid

def file(world,n,kind='artifacts',**fields):
    r,_,_=world
    fid=f'{n:032x}'
    data=dict(display_name='Alpha.md',format='markdown',byte_count=6,created_at='2026-10-13T00:00:00Z')
    data.update(fields)
    with r.store.connection(write=True) as c:
        c.execute('INSERT INTO private_files VALUES(?,?,?,?,?,?,NULL)',(fid,kind,f'audit/{fid}','x',encode(data),'verified'))
    return fid

def search(world,**kw):
    return WorkSearchService(world[0]).search(WorkSearchInput(**kw),session_hash=world[1])

@pytest.mark.parametrize('query',['ＡＬＰＨＡ','alpha','Alpha'])
def test_unicode_rank_and_full_corpus(world,query):
    strong=run(world,1,'Alpha')
    for i in range(2,101): run(world,i,'Alpha weak')
    assert search(world,query=query)['items'][0]['id']==strong
    first=search(world,query=query,limit=50)
    second=search(world,query=query,limit=50,offset=50,snapshot=first['snapshot'])
    assert len(set(i['id'] for i in first['items']+second['items']))==100

@pytest.mark.parametrize('current,history,expected',[(None,True,'unknown'),([],True,'earlier'),('bad',True,'unknown'),('self',False,'current'),([],False,'unknown')])
def test_exact_membership(world,current,history,expected):
    rid=run(world,1)
    aid=file(world,2,run_id=rid)
    with world[0].store.connection(write=True) as c:
        d=json.loads(c.execute('SELECT data FROM agent_runs WHERE id=?',(rid,)).fetchone()[0])
        d['current_artifact_ids']=[aid] if current=='self' else current
        d['artifact_ids']=[aid] if history else []
        c.execute('UPDATE agent_runs SET data=? WHERE id=?',(encode(d),rid))
    assert search(world,kind='artifact')['items'][0]['output_membership']==expected

@pytest.mark.parametrize('change,code',[('hide','PRIVATE_CONTEXT_HIDDEN'),('hide_show','WORK_SEARCH_PRIVACY_CHANGED'),('revoke','OWNER_SIGN_IN_REQUIRED'),('expire','OWNER_SIGN_IN_REQUIRED'),('epoch','WORK_SEARCH_PRIVACY_CHANGED')])
def test_delayed_privacy(world,change,code):
    run(world,1)
    service=WorkSearchService(world[0]); original=service._corpus
    def delay(rows):
        out=original(rows)
        with world[0].store.connection(write=True) as c:
            if change=='hide': c.execute("UPDATE settings SET data=?,version=version+1",(encode({'timezone':'UTC','hide_private':True}),))
            if change=='hide_show': c.execute('UPDATE settings SET version=version+2')
            if change=='revoke': c.execute('DELETE FROM sessions')
            if change=='epoch': c.execute('UPDATE personal_settings SET epoch=epoch+1')
        if change=='expire': world[2][0]+=timedelta(days=1)
        return out
    service._corpus=delay
    with pytest.raises(DomainError) as e: service.search(WorkSearchInput(),session_hash=world[1])
    assert e.value.code==code

def test_snapshot_change_and_unrelated_private_projection(world):
    rid=run(world,1)
    first=search(world)
    with world[0].store.connection(write=True) as c:
        d=json.loads(c.execute('SELECT data FROM agent_runs WHERE id=?',(rid,)).fetchone()[0])
        d.update(report='PRIVATE_REPORT',memory='PRIVATE_MEMORY',tool_results={'private':'SECRET'})
        c.execute('UPDATE agent_runs SET data=? WHERE id=?',(encode(d),rid))
    unchanged=search(world)
    assert unchanged==first
    with world[0].store.connection(write=True) as c:
        d['goal']='Changed Alpha';c.execute('UPDATE agent_runs SET data=? WHERE id=?',(encode(d),rid))
    with pytest.raises(DomainError) as e: search(world,snapshot=first['snapshot'])
    assert e.value.code=='WORK_SEARCH_CHANGED'

def test_sql_projection_no_body_no_writes(world,monkeypatch):
    run(world,1,report='DO_NOT_READ_REPORT',tool_results={'body':'DO_NOT_READ_TOOLS'})
    file(world,2,content='DO_NOT_READ_BODY',host_path='/private/secret')
    store=world[0].store; original=store.connection; traced=[]
    @contextmanager
    def observed(write=False):
        assert not write
        with original() as c:
            c.set_trace_callback(traced.append)
            yield c
    monkeypatch.setattr(store,'connection',observed)
    def forbidden(*a,**kw): raise AssertionError('file or model effect')
    monkeypatch.setattr(world[0].sources,'read',forbidden)
    monkeypatch.setattr(world[0].artifacts,'detail',forbidden)
    monkeypatch.setattr(world[0].artifacts,'reconcile',forbidden)
    result=search(world)
    assert 'DO_NOT_READ' not in json.dumps(result)
    assert not any(q.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','REPLACE')) for q in traced)
    assert all('SELECT *' not in q for q in traced if 'FROM agent_runs' in q or 'FROM private_files' in q)
    assert any("data -> '$.goal'" in q for q in traced)

def test_chinese_injection_literal(world):
    run(world,1,'中文 搜索 Alpha')
    assert search(world,query='中文 alpha')['total']==1
    assert search(world,query="' OR 1=1 --")['total']==0

def test_capacity_fail_closed(world):
    for n in range(101): run(world,n)
    with pytest.raises(DomainError) as e: search(world,kind='source')
    assert e.value.code=='WORK_SEARCH_CAPACITY_EXCEEDED'

def test_all_six_hundred_records_are_pageable(world):
    for n in range(100): run(world,n)
    for n in range(100,200): file(world,n,'sources')
    for n in range(200,600): file(world,n)
    first=search(world,limit=50)
    found=first['items']
    for offset in range(50,600,50):
        result=search(world,limit=50,offset=offset,snapshot=first['snapshot'])
        assert result['total']==600
        found+=result['items']
    assert len({(x['kind'],x['id']) for x in found})==600
    assert result['next_offset'] is None

@pytest.mark.parametrize('raw,status',[(None,'unlinked'),('missing-parent','unknown'),('/private/path','unknown')])
def test_missing_parent_never_invents_relationship(world,raw,status):
    file(world,2,run_id=raw)
    result=search(world)['items'][0]
    assert result['output_membership']==status
    assert result['current_linked_goal'] is None
    assert '/private/path' not in json.dumps(result)

def test_boolean_metadata_does_not_masquerade_as_integer(world):
    run(world,1)
    aid=file(world,2,byte_count=True)
    result=search(world,query=aid)['items'][0]
    assert result['byte_count'] is None

def test_real_route_cookie_origin_header_no_operation_receipt(tmp_path):
    from desk.app import create_app
    from fastapi.testclient import TestClient
    app=create_app(tmp_path,password='audit-fixture',scheduler=False,connector_configs=())
    client=TestClient(app)
    route='/api/work/search'
    assert client.post(route,json={}).status_code==403
    assert client.post(route,json={},headers={'X-Desk-Request':'1'}).status_code==403
    token=app.state.store.authenticate('owner','audit-fixture')
    client.cookies.set('desk_companion_session',token)
    assert client.post(route,json={},headers={'X-Desk-Request':'1','Origin':'https://untrusted.example'}).status_code==403
    response=client.post(route,json={},headers={'X-Desk-Request':'1'})
    assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    assert response.json()['total']==0
    with app.state.store.connection() as c:
        assert c.execute('SELECT count(*) FROM operations').fetchone()[0]==0
    assert client.post(route,json={'offset':1},headers={'X-Desk-Request':'1'}).status_code==422
    client.close()
