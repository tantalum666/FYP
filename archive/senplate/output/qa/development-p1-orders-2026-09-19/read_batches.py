from pathlib import Path
import json,sys,datetime,hashlib
q=Path(__file__).parent;plan=json.loads((q/'reading-plan.json').read_text());path=q/'reading-record.json';r=json.loads(path.read_text())
ack,read=sys.argv[1:3]
for i in [int(x) for x in ack.split(',') if x]:
 if i not in r['read_batches']:
  r['read_batches'].append(i)
  for chunk in plan[i]:
   item=next(f for f in r['files'] if f['file']==chunk['file']);item['read_ranges'].append([chunk['start'],chunk['end']])
if len(r['read_batches'])==len(plan):
 r['completed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r['changes_during_reading']=[f['file'] for f in r['files'] if hashlib.sha256(Path(f['file']).read_bytes()).hexdigest()!=f['sha256']]
path.write_text(json.dumps(r,ensure_ascii=False,indent=2))
for i in [int(x) for x in read.split(',') if x]:
 print('BATCH',i)
 for c in plan[i]:
  print('\nFILE',c['file'],'LINES',c['start'],c['end']);print(c['text'])
