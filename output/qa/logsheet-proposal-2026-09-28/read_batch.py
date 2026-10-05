from pathlib import Path
import json,sys
q=Path(__file__).parent
rec=json.loads((q/'reading-record.json').read_text())
idx=int(sys.argv[1])
for entry in rec['batches'][idx]:
 lines=Path(entry['file']).read_text().splitlines()
 print('FILE '+entry['file']+' L'+str(entry['start'])+'-'+str(entry['end']))
 print('\n'.join(lines[entry['start']-1:entry['end']]))
