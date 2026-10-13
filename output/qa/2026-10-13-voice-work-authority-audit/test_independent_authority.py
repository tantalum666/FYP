"""Independent synthetic protocol/SQLite authority audit. Never live I/O."""
import hashlib
import json
from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest
from desk.runtime import Runtime
from desk.store import Store, DomainError
from desk.voice import VoiceConfig, GeminiProtocol, QwenAudioProtocol, VOICE_TOOLS
from desk.voice_work import VoiceDraftFreeze
from desk.sources import SourceInput
from desk.agent_run_schemas import RunCreate
from desk.schemas import SettingsInput

@pytest.fixture
def w(tmp_path):
    now = [datetime(2026,10,13,6,tzinfo=UTC)]
    r = Runtime(Store(tmp_path, password='synthetic-only', clock=lambda: now[0]))
    r.voice.config = VoiceConfig('qwen_audio','wss://dashscope.aliyuncs.com/api-ws/v1/realtime','synthetic-model','synthetic-key')
    token = r.store.authenticate('owner','synthetic-only')
    p = dict(kind='owner', session=token)
    source = r.sources.ingest(SourceInput(name='fixture.csv',format='csv'), b'name,value\na,2\n', 'source', session_hash=hashlib.sha256(token.encode()).hexdigest())['source']
    return r,p,source,now

def event(text='RAW_UNSELECTED_MARKER', key='one', seq=1, boundary='provider_final', op='replace'):
    return dict(type='transcript',role='user',text=text,input_key=key,input_sequence=seq,boundary=boundary,input_operation=op)

def draft(w, text='RAW_SELECTED_MARKER'):
    r,p,_,_ = w
    ref=r.voice.work.begin(p)
    s=r.voice.work.observe(ref,event(text))
    d=r.voice.work.freeze(VoiceDraftFreeze(voice_session_ref=ref,input_segment_id=s['input_segment_id'],expected_revision=s['revision']),p)
    return ref,s,d

def payload(w,d,**kw):
    r,p,s,_=w
    return RunCreate(**(dict(goal='REVIEWED_GOAL_ONLY',retain=True,source_ids=[s['id']],scope_revision=r.agent_runs.scope(p)['scope_revision'],voice_origin_ref=d['voice_origin_ref'])|kw))

def test_recovery_expiry_restart_and_one_claim(w):
    r,p,_,now=w
    ref,s,d=draft(w)
    data=payload(w,d)
    created=r.agent_runs.create(data,'same-operation',p)['run']
    r.voice.work.end(ref)
    now[0]+=timedelta(seconds=301)
    r.voice.work.cleanup()
    assert not r.voice.work.drafts
    assert r.agent_runs.create(data,'same-operation',p)['run']['id']==created['id']
    again=Runtime(Store(r.store.directory, clock=lambda:now[0]))
    assert again.agent_runs.create(data,'same-operation',p)['run']['id']==created['id']
    with pytest.raises(DomainError,match='VOICE_DRAFT_ALREADY_USED'):
        again.agent_runs.create(data,'new-operation',p)
    with pytest.raises(DomainError,match='OPERATION_ID_CONFLICT'):
        again.agent_runs.create(data.model_copy(update={'goal':'changed'}),'same-operation',p)
    assert created['voice_origin']['edited'] is True
    assert 'voice_origin_ref' not in created
    serialized='\n'.join(file.read_bytes().decode('utf-8',errors='ignore') for file in r.store.directory.rglob('*') if file.is_file())
    assert 'RAW_SELECTED_MARKER' not in serialized
    assert 'REVIEWED_GOAL_ONLY' in serialized

def test_parallel_different_operations_claim_once(w):
    r,p,_,_=w
    _,_,d=draft(w)
    data=payload(w,d)
    def create(key):
        try: return r.agent_runs.create(data,key,p)['run']['id']
        except DomainError as e: return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(create,['parallel-a','parallel-b']))
    assert results.count('VOICE_DRAFT_ALREADY_USED')==1
    with r.store.connection() as c:
        assert c.execute('select count(*) from agent_runs').fetchone()[0]==1
        assert c.execute('select count(*) from agent_voice_origins').fetchone()[0]==1

def test_final_dedupe_contradiction_frozen_snapshot(w):
    r,p,_,_=w
    ref,s,d=draft(w)
    assert r.voice.work.observe(ref,event('RAW_SELECTED_MARKER',seq=2)) is None
    bad=r.voice.work.observe(ref,event('contradiction',seq=3))
    assert bad['eligible'] is False
    assert r.voice.work.observe(ref,event('tail',seq=4)) is None
    assert r.voice.work.drafts[d['voice_origin_ref']]['text']=='RAW_SELECTED_MARKER'
    assert r.voice.work.observe(ref,event('stale',key='new',seq=2)) is None

def test_unicode_overflow_never_tail_and_total_bound(w):
    r,p,_,_=w
    ref=r.voice.work.begin(p)
    for n in range(8):
        value=r.voice.work.observe(ref,event('界'*4000,key=str(n),seq=n+1))
    state=r.voice.work.sessions[ref]
    assert len(state['segments'])<=8 and r.voice.work._size(state)<=32768
    bad=r.voice.work.observe(ref,event('x'*4001,key='overflow',seq=9))
    assert bad['reason']=='VOICE_INPUT_TOO_LARGE' and bad['text']==''
    assert r.voice.work.observe(ref,event('tail',key='overflow',seq=10,op='append')) is None

def test_only_user_input_and_no_pre_retention_plaintext(w):
    r,p,_,_=w
    ref=r.voice.work.begin(p)
    for ev in [event()|{'role':'assistant'},event()|{'type':'tool'},event()|{'boundary':'invented'},event()|{'input_sequence':True}]:
        assert r.voice.work.observe(ref,ev) is None
    r.voice.work.observe(ref,event('RAW_UNSELECTED_MARKER'))
    selected=r.voice.work.observe(ref,event('RAW_SELECTED_MARKER',key='selected',seq=2))
    d=r.voice.work.freeze(VoiceDraftFreeze(voice_session_ref=ref,input_segment_id=selected['input_segment_id'],expected_revision=1),p)
    serialized='\n'.join(file.read_bytes().decode('utf-8',errors='ignore') for file in r.store.directory.rglob('*') if file.is_file())
    assert 'RAW_UNSELECTED_MARKER' not in serialized and d['text'] not in serialized
    assert not any(t['name'] in {'work_start','work_approve','run_create','memory_create_draft'} for t in VOICE_TOOLS)

@pytest.mark.parametrize('principal',[{'kind':'owner'},{'kind':'owner','session':'invented'},{'kind':'controller','session':'invented'},{'kind':'agent','session':'invented'}])
def test_fake_principals_denied(w,principal):
    r,p,_,_=w
    ref,s,d=draft(w)
    with pytest.raises(DomainError):
        r.voice.work.freeze(VoiceDraftFreeze(voice_session_ref=ref,input_segment_id=s['input_segment_id'],expected_revision=1),principal)
    assert r.voice.work.begin(principal) is None

def test_cross_session_hide_show_and_model_change(w):
    r,p,_,_=w
    ref,s,d=draft(w)
    other={'kind':'owner','session':r.store.authenticate('owner','synthetic-only')}
    with pytest.raises(DomainError,match='VOICE_CONTEXT_CHANGED'):
        r.voice.work.freeze(VoiceDraftFreeze(voice_session_ref=ref,input_segment_id=s['input_segment_id'],expected_revision=1),other)
    r.voice.config.model='changed-model'
    r.voice.work.cleanup()
    assert not r.voice.work.drafts and not r.voice.work.sessions

def test_gemini_finality_is_never_assistant_completion():
    protocol=GeminiProtocol()
    events=protocol.events({'serverContent':{'inputTranscription':{'text':'partial'},'turnComplete':True}})
    input_event=next(e for e in events if e['type']=='transcript')
    assert input_event['boundary']=='unfinalized' and input_event['final'] is False
    second=protocol.events({'serverContent':{'inputTranscription':{'text':'next'}}})[0]
    assert second['input_key']!=input_event['input_key']

def test_privacy_toctou_independent(w,monkeypatch):
    r,p,_,_=w
    _,_,d=draft(w)
    data=payload(w,d)
    original=r.agent_runs._authorize
    def hide(run):
        original(run)
        with r.store.connection() as c: setting=r.store.settings(c)
        r.store.update_settings(SettingsInput(expected_version=setting['version'],timezone=setting['timezone'],hide_private=True),'race-hide')
    monkeypatch.setattr(r.agent_runs,'_authorize',hide)
    with pytest.raises(DomainError,match='PRIVATE_CONTEXT_HIDDEN'):
        r.agent_runs.create(data,'race',p)
    with r.store.connection() as c:
        assert c.execute('select count(*) from agent_runs').fetchone()[0]==0
        assert c.execute('select count(*) from agent_voice_origins').fetchone()[0]==0

def test_freeze_retry_does_not_extend_ttl_and_disconnect_is_independent(w):
    r,p,_,now=w
    ref,s,d=draft(w)
    data=payload(w,d)
    run=r.agent_runs.create(data,'ttl',p)['run']
    now[0]+=timedelta(seconds=299)
    repeated=r.voice.work.freeze(VoiceDraftFreeze(voice_session_ref=ref,input_segment_id=s['input_segment_id'],expected_revision=1),p)
    assert repeated['expires_at']==d['expires_at']
    r.voice.work.end(ref)
    assert r.agent_runs.detail(run['id'],p)['run']['state']=='queued'
    now[0]+=timedelta(seconds=1)
    r.voice.work.cleanup()
    assert not r.voice.work.sessions and not r.voice.work.drafts
    assert r.agent_runs.detail(run['id'],p)['run']['state']=='queued'

def test_expired_uncommitted_draft_does_not_fall_back(w):
    r,p,_,now=w
    ref,s,d=draft(w)
    data=payload(w,d)
    r.voice.work.end(ref)
    now[0]+=timedelta(seconds=300)
    with pytest.raises(DomainError,match='VOICE_DRAFT_EXPIRED'):
        r.agent_runs.create(data,'uncommitted-expired',p)
    with r.store.connection() as c:
        assert c.execute('select count(*) from agent_runs').fetchone()[0]==0
        assert c.execute('select count(*) from agent_run_operations').fetchone()[0]==0

def test_failed_save_rolls_back_claim_and_allows_same_operation(w,monkeypatch):
    r,p,_,_=w
    _,_,d=draft(w)
    data=payload(w,d)
    original=r.agent_runs._save
    def fail(*a,**kw): raise RuntimeError('synthetic precommit failure')
    monkeypatch.setattr(r.agent_runs,'_save',fail)
    with pytest.raises(RuntimeError): r.agent_runs.create(data,'failed-commit',p)
    with r.store.connection() as c:
        for table in ['agent_runs','agent_voice_origins','agent_run_operations']:
            assert c.execute('select count(*) from '+table).fetchone()[0]==0
    monkeypatch.setattr(r.agent_runs,'_save',original)
    assert r.agent_runs.create(data,'failed-commit',p)['run']['state']=='queued'

def test_strict_retention_and_origin_metadata_rejected(w):
    from pydantic import ValidationError
    _,_,d=draft(w)
    for bad in [1,1.0,'true','1',False,None]:
        with pytest.raises(ValidationError): payload(w,d,retain=bad)
    with pytest.raises(ValidationError): payload(w,d,voice_origin={'provider':'invented'})

def test_ledger_end_failure_cannot_strand_voice_slot(w,monkeypatch):
    import asyncio
    import sqlite3
    import time
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'desk-companion'/'tests'))
    from test_voice_context import Provider, Socket
    r,p,_,_=w
    def failure(ref): raise sqlite3.OperationalError('synthetic ledger cleanup DB failure')
    monkeypatch.setattr(r.voice.work,'end',failure)
    async def scenario():
        provider=Provider()
        socket=Socket()
        r.voice.connector=lambda *a,**kw:provider
        r.voice.active,r.voice.started=True,time.monotonic()
        try:
            await asyncio.wait_for(r.voice.run(socket,p,'en'),4)
        except sqlite3.OperationalError:
            pass
        assert r.voice.active is False, 'Ledger cleanup failure stranded active voice slot'
        assert socket.closed is True, 'Ledger cleanup failure skipped socket close'
    asyncio.run(scenario())

def test_origin_metadata_never_enters_planner_payload(w):
    from desk.agent_planner import _decision_context
    r,p,_,_=w
    _,_,d=draft(w)
    view=r.agent_runs.create(payload(w,d),'model-payload-isolation',p)['run']
    with r.store.connection() as c: retained=r.agent_runs._get(c,view['id'])
    context,schemas=_decision_context(r,retained)
    encoded=json.dumps(context)
    assert 'voice_origin' not in encoded
    assert d['voice_origin_ref'] not in encoded
    assert 'RAW_SELECTED_MARKER' not in encoded
    assert 'synthetic-model' not in encoded
    assert context['goal']=='REVIEWED_GOAL_ONLY'

def test_wall_clock_rollback_cannot_extend_transient_ttl(w,monkeypatch):
    import time
    elapsed=[1000.0]
    monkeypatch.setattr(time,'monotonic',lambda:elapsed[0])
    r,p,_,now=w
    ref,s,d=draft(w)
    r.voice.work.end(ref)
    now[0]-=timedelta(hours=1)
    elapsed[0]+=301
    r.voice.work.cleanup()
    assert d['voice_origin_ref'] not in r.voice.work.drafts, 'Clock rollback extended volatile retention past 300 seconds'

def test_malformed_surrogate_rejected_before_segment_mutation(w):
    r,p,_,_=w
    ref=r.voice.work.begin(p)
    first=r.voice.work.observe(ref,event('valid',boundary='unfinalized',op='append'))
    state=r.voice.work.sessions[ref]
    previous_sequence=state['sequence']
    previous_segments=dict(state['segments'])
    result=r.voice.work.observe(ref,event('\ud800',seq=2,boundary='unfinalized',op='append'))
    assert result is None
    assert state['sequence']==previous_sequence and state['segments']==previous_segments
