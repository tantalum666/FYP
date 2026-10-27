from pathlib import Path
import json
import httpx

with httpx.Client(base_url='http://127.0.0.1:8831/api',headers={'X-Desk-Request':'1'},trust_env=False) as c:
    assert c.get('/session-mode').json()['local_preview'] is True
    assert c.post('/session/preview').status_code == 200
    events=c.get('/calendar',params={'start':'2026-10-27T16:00:00Z','end':'2026-10-30T16:00:00Z'}).json()['occurrences']
    matches=[e for e in events if e['title']=='Maintenance QA — Shared editor']
    assert len(matches)==1
    event=matches[0]
    assert event['start_local'][:16]=='2026-10-29T14:00' and event['end_local'][:16]=='2026-10-29T15:00'
    assert event['version']==1
    tasks=c.get('/tasks?include_closed=true').json()['tasks']
    task=next(t for t in tasks if t['title']=='UI QA — Prepare demo notes')
    detail=c.get('/tasks/'+task['id']).json()
    assert task['status']=='todo' and task['version']==1
    assert not any('QA update:' in e['note'] or 'QA progress draft' in e['note'] for e in detail['evidence'])
    assert not c.get('/assistant/proposals').json()['proposals']
    workspace=c.get('/workspace').json()
    assert not workspace['voice']['configured'] and not workspace['text_ai']['configured']
    result={'event':{k:event[k] for k in ('title','version','start_local','end_local','visibility','reminder_minutes')},'unique_event':True,'task_version':task['version'],'task_status':task['status'],'cancelled_drafts_not_written':True,'pending_proposals':0,'voice_configured':False,'text_ai_configured':False}
    Path(__file__).with_name('data-readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('Independent readback passed: one shared-editor event; no cancelled task note; providers disabled.')
