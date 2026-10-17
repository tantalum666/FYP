import json,sys
from pathlib import Path
qa=Path(__file__).parent
d=json.loads((qa/'reading-inventory.json').read_text())
n=int(sys.argv[1])
print(f"BATCH {n+1}/{len(d['batches'])}")
for part in d['batches'][n]:
 e=d['entries'][part['entry']]
 lines=(Path(e['source'])/e['path']).read_text().splitlines()
 print(f"\nFILE {e['source']}/{e['path']} L{part['start']}-{part['end']} OF {len(lines)}")
 print('\n'.join(lines[part['start']-1:part['end']]))
print(f"END BATCH {n}")
