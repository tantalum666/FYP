from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
p=Path(__file__).with_name('full-reading-record.json')
d=json.loads(p.read_text());i=int(sys.argv[1])
if len(sys.argv)>2:
 for previous in [int(v) for v in sys.argv[2].split(',')]:
  if previous in d['completed_chunks']:continue
  d['completed_chunks'].append(previous)
  for part in d['chunks'][previous]:
   f=next(f for f in d['files'] if f['path']==part['path'])
   f['read_ranges'].append([part['start'],part['end']])
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for part in d['chunks'][i]:
 print('\nFILE:',part['path'],'LINES:',str(part['start'])+'-'+str(part['end']))
 lines=(ROOT/part['path']).read_text().splitlines(keepends=True)
 print(''.join(lines[part['start']-1:part['end']]),end='')
