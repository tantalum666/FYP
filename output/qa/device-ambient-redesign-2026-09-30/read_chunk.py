from pathlib import Path
import json,sys
root=Path(__file__).resolve().parents[3]
record_path=Path(__file__).with_name('reading-record.json')
r=json.loads(record_path.read_text());index=int(sys.argv[1]);chunk=r['chunks'][index]
for section in chunk:
    n=section['path'];a=section['start'];b=section['end'];lines=(root/n).read_text().splitlines()
    print(f'FILE {n} LINES {a}-{b} OF {len(lines)}')
    print('\n'.join(lines[a-1:b]))
    for file in r['files']:
        if file['path']==n and [a,b] not in file['read_ranges']:file['read_ranges'].append([a,b])
if index not in r['chunks_delivered']:r['chunks_delivered'].append(index)
record_path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(f'END CHUNK {index}')
