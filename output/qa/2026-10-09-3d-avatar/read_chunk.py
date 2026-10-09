import json,sys
from pathlib import Path
p=Path(__file__).with_name("reading-record.json");r=json.loads(p.read_text())
i=int(sys.argv[1])
for a in sys.argv[2:]:
 n=int(a)
 if n not in r["completed_chunks"]:r["completed_chunks"].append(n)
p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
for s in r["chunks"][i]:
 print("\nFILE",s["path"],"LINES",s["start"],s["end"]);print("".join(Path(s["path"]).read_text().splitlines(keepends=True)[s["start"]-1:s["end"]]),end="")
