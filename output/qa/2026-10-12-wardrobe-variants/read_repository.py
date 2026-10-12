from pathlib import Path
import argparse
import datetime
import json

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("batch", type=int)
parser.add_argument("--ack", type=int, action="append", default=[])
args = parser.parse_args()
plan = json.loads((QA / "reading-plan.json").read_text())
record = json.loads((QA / "reading-record.json").read_text())
by_path = {item["path"]: item for item in record["files"]}
for index in args.ack:
    for item in plan[index]:
        current = by_path[item["path"]]
        span = [item["start"], item["end"]]
        if span not in current["read_ranges"]:
            current["read_ranges"].append(span)
        current["last_read_at"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
record["acknowledged_batches"] = sorted(set(record.get("acknowledged_batches", [])) | set(args.ack))
(QA / "reading-record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
if args.batch < len(plan):
    for item in plan[args.batch]:
        lines = (ROOT / item["path"]).read_text().splitlines(keepends=True)
        print(f"\nFILE {item['path']} LINES {item['start']}-{item['end']} OF {len(lines)}")
        print("".join(lines[item["start"] - 1:item["end"]]), end="\n")
    print(f"\nEND BATCH {args.batch} OF {len(plan)}")
else:
    print(f"Acknowledged {len(record['acknowledged_batches'])} of {len(plan)} batches.")
