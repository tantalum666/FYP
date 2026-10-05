import argparse,json
from pathlib import Path
p=Path(__file__).with_name("reading-record.json")
r=json.loads(p.read_text())
a=argparse.ArgumentParser();a.add_argument("index",type=int);a.add_argument("--ack",type=int,nargs="*");args=a.parse_args()
for i in args.ack or []:
 if i not in r["completed_chunks"]:r["completed_chunks"].append(i)
p.write_text(json.dumps(r,ensure_ascii=False,indent=2))
print("CHUNK",args.index)
for s in r["chunks"][args.index]:
 print("\nFILE",s["path"],"LINES",s["start"],s["end"])
 print("".join(Path(s["path"]).read_text().splitlines(keepends=True)[s["start"]-1:s["end"]]),end="")
