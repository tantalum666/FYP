import pathlib,json,datetime,sys,hashlib
qa=pathlib.Path(__file__).parent
r=json.loads((qa/'reading-record.json').read_text()); chunks=json.loads((qa/'read-chunks.json').read_text())
statepath=qa/'read-state.json';state=json.loads(statepath.read_text()) if statepath.exists() else {'next':0,'pending':[],'acknowledged':[]}
if '--ack' in sys.argv:
 for i in state['pending']:
  c=chunks[i];next(x for x in r['files'] if x['path']==c['path'])['read_ranges'].append([c['start'],c['end']]);state['acknowledged'].append(i)
 state['pending']=[]
size=0
while state['next']<len(chunks):
 i=state['next'];c=chunks[i];lines=pathlib.Path(c['path']).read_text().splitlines(keepends=True);body=''.join(lines[c['start']-1:c['end']])
 if size+len(body)>19000 and size:break
 print(f"\nFILE {c['path']} L{c['start']}-{c['end']} CHUNK {i}\n");print(body,end='');size+=len(body);state['pending'].append(i);state['next']+=1
statepath.write_text(json.dumps(state,ensure_ascii=False,indent=2));(qa/'reading-record.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
print(f"\nREAD_PROGRESS {state['next']}/{len(chunks)} printed; {len(state['acknowledged'])} acknowledged")
