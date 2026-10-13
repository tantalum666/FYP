"""Independent offline-only audit probes; no application edits."""
import json
import socket
import sqlite3
from types import SimpleNamespace
import httpx
import pytest
from desk import text_trial_preflight as t
from desk.text_ai import TextAssistant, TextConfig, _DISPATCH_CHECKPOINT
from desk.store import DomainError
Q='https://synthetic.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions'
def preview(provider='gemini'):
    return t.offline_preflight(provider=provider,model='fixture-model',endpoint=Q if provider=='qwen' else '')

@pytest.mark.parametrize('provider',['gemini','qwen'])
def test_payload_is_byte_identical_to_direct_production_generate(provider):
    report=preview(provider)
    store=t._UsageStore()
    seen=[]
    def transport(request):
        seen.append(request.content)
        return httpx.Response(200,json=t._fixture_body(provider))
    try:
        service=TextAssistant(SimpleNamespace(store=store),config=TextConfig(provider,'fixture-model',Q if provider=='qwen' else '',t._FIXTURE_KEY),transport=httpx.MockTransport(transport))
        service.generate(t._SYSTEM,t.synthetic_context(),t.SyntheticTrialPlan,'independent')
        import hashlib
        assert len(seen)==1 and len(seen[0])==report['request']['bytes']
        assert hashlib.sha256(seen[0]).hexdigest()==report['request']['sha256']
        assert json.loads(seen[0])==report['request']['json']
    finally: store.db.close()

@pytest.mark.parametrize('endpoint',[
 Q.replace('https://','http://'),Q.replace('https://','https://person:secret@'),Q.replace('https://','https://@'),Q.replace('.com/','.com:443/'),Q.replace('.com/','.com:/'),Q.replace('.com/','.com.evil.invalid/'),Q.replace('.com/','.com./'),Q+'?key=secret',Q+'#secret',Q.replace('synthetic','%73ynthetic'),Q.replace('synthetic','synthetic\\'),Q.replace('synthetic','synthetic\t'),Q.replace('synthetic','synthétic'),Q.replace('synthetic','nested.synthetic'),Q.replace('/compatible-mode','/../compatible-mode'),Q+'/', 'https://127.0.0.1/compatible-mode/v1/chat/completions','https://[::1]/compatible-mode/v1/chat/completions','https://[broken', None,False,42])
def test_endpoint_never_reaches_capture(monkeypatch,endpoint):
    monkeypatch.setattr(t._OfflineCapture,'__init__',lambda *_: pytest.fail('capture constructed'))
    with pytest.raises(ValueError): t.offline_preflight(provider='qwen',model='fixture',endpoint=endpoint)

@pytest.mark.parametrize('model',['fixture?key=secret','../fixture','fixture\r\nX:secret','fixture/extra','',None,True,'x'*101,'模型',' fixture'])
def test_model_never_reaches_capture(monkeypatch,model):
    monkeypatch.setattr(t._OfflineCapture,'__init__',lambda *_: pytest.fail('capture constructed'))
    with pytest.raises(ValueError): t.offline_preflight(provider='gemini',model=model,endpoint='')

@pytest.mark.parametrize('provider',['gemini','qwen'])
def test_all_network_fallbacks_and_persistent_db_are_forbidden(monkeypatch,provider):
    def denied(*a,**k): pytest.fail('forbidden network/credentials/dispatch')
    for name in ['socket','create_connection','getaddrinfo','gethostbyname']:
        monkeypatch.setattr(socket,name,denied)
    monkeypatch.setattr(httpx.HTTPTransport,'__init__',denied)
    monkeypatch.setattr(TextConfig,'environment',denied)
    monkeypatch.setattr(TextAssistant,'_reply',denied)
    monkeypatch.setattr(TextAssistant,'context',denied)
    connect=sqlite3.connect
    def only_memory(path,*a,**k):
        assert path==':memory:'
        return connect(path,*a,**k)
    monkeypatch.setattr(sqlite3,'connect',only_memory)
    assert preview(provider)['status']=='offline_preflight_passed'

@pytest.mark.parametrize('provider',['gemini','qwen'])
def test_reentrant_capture_has_no_second_response(monkeypatch,provider):
    config=TextConfig(provider,'fixture-model',Q if provider=='qwen' else '')
    capture=t._OfflineCapture(config)
    payload=preview(provider)['request']['json']
    request=httpx.Request('POST',capture.url,json=payload)
    original=t._fixture_body
    calls=[]
    def reenter(p):
        calls.append(p)
        with pytest.raises(ValueError,match='TRIAL_REQUEST_LIMIT'): capture.handle_request(request)
        return original(p)
    monkeypatch.setattr(t,'_fixture_body',reenter)
    capture.handle_request(request)
    assert len(calls)==1 and capture.attempts==2

@pytest.mark.parametrize('tool',['task_change_draft','calendar_create_draft','memory_create','computer_job_draft','none'])
def test_hostile_fixture_plan_fails_without_dispatch(monkeypatch,tool):
    original=t._fixture_body
    def hostile(provider):
        body=original(provider)
        raw=json.loads(body['candidates'][0]['content']['parts'][0]['text'])
        raw['tool']=tool
        body['candidates'][0]['content']['parts'][0]['text']=json.dumps(raw)
        return body
    monkeypatch.setattr(t,'_fixture_body',hostile)
    with pytest.raises(DomainError): preview()
    assert _DISPATCH_CHECKPOINT.get() is None

@pytest.mark.parametrize('flag,value',[('--provider','gemini\nSECRET'),('--model','x?key=SECRET'),('--endpoint','https://owner:SECRET@generativelanguage.googleapis.com/v1beta'),('--api-key','SECRET'),('--live','SECRET'),('--provider','qwen_audio')])
def test_cli_rejected_input_is_not_echoed(flag,value):
    import subprocess,sys
    from pathlib import Path
    script=Path(__file__).resolve().parents[3]/'desk-companion/scripts/check_text_trial.py'
    args=['--provider','gemini','--model','fixture','--endpoint','',flag,value]
    result=subprocess.run([sys.executable,'-I',str(script),*args],env={},capture_output=True,timeout=10)
    assert result.returncode != 0
    assert b'SECRET' not in result.stdout+result.stderr


def test_streamed_response_bound_exactly_then_one_byte_over():
    from desk.text_ai import bounded_json_post,TEXT_RESPONSE_BYTES
    class Stream(httpx.SyncByteStream):
        def __init__(self,extra): self.extra=extra; self.closed=False
        def __iter__(self):
            yield b'{}'+b' '*(TEXT_RESPONSE_BYTES-2)
            if self.extra: yield b' '
        def close(self): self.closed=True
    for extra in [False,True]:
        stream=Stream(extra)
        with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,stream=stream))) as client:
            if extra:
                with pytest.raises(ValueError): bounded_json_post(client,'https://example.invalid',headers={},json_body={})
            else:
                assert bounded_json_post(client,'https://example.invalid',headers={},json_body={})=={}
        assert stream.closed

@pytest.mark.parametrize('provider',['gemini','qwen'])
def test_request_boundary_exactly_then_one_byte_over(provider):
    payload=preview(provider)['request']['json']
    raw=json.dumps(payload).encode()
    assert len(raw)<t.REQUEST_BYTES
    raw+=b' '*(t.REQUEST_BYTES-len(raw))
    config=TextConfig(provider,'fixture-model',Q if provider=='qwen' else '')
    capture=t._OfflineCapture(config)
    capture.handle_request(httpx.Request('POST',capture.url,content=raw))
    assert len(capture.body_bytes)==t.REQUEST_BYTES
    capture=t._OfflineCapture(config)
    with pytest.raises(ValueError,match='TRIAL_REQUEST_SIZE_LIMIT'):
        capture.handle_request(httpx.Request('POST',capture.url,content=raw+b' '))
    assert capture.payload is None
