import json
import time
from pathlib import Path
from desk.public_capture_policy import extract_static_text
from desk.store import DomainError

cases = {
    "spaces": "<p " + " " * 131000 + ">x</p>",
    "complete_attribute": '<p a="' + "x" * 131000 + '">x</p>',
    "unclosed_attribute": '<p>visible</p><p a="' + "x" * 131000,
    "repeated_attributes": "<p" + " a" * 65000 + ">x</p>",
    "slashes": "<p " + "/" * 131000 + ">x</p>",
    "complete_comment": "<!--" + "x" * 131000 + "--><p>x</p>",
    "unclosed_comment": "<p>visible</p><!--" + "x" * 131000,
    "entity": "<p>&" + "x" * 131000 + ";</p>",
    "quote_backtracking": "<p a=" + ("x " * 65000) + '">visible</p>',
    "events": "<b>x</b>" * 16000,
    "plain_output_overflow": "x" * 131072,
}
report = []
for name, s in cases.items():
    start = time.monotonic()
    marks = []
    try:
        output = extract_static_text(
            s.encode(),
            "text/plain" if name == "plain_output_overflow" else "text/html",
            lambda: marks.append(time.monotonic()),
        )
        result = {"accepted": True, "output_bytes": len(output.body)}
    except DomainError as e:
        result = {"accepted": False, "code": e.code}
    end = time.monotonic()
    report.append(
        {
            "case": name,
            "bytes": len(s.encode()),
            "seconds": end - start,
            "checkpoint_count": len(marks),
            "max_checkpoint_gap_seconds": max(
                b - a for a, b in zip([start] + marks, marks + [end])
            ),
            **result,
        }
    )
    print(json.dumps(report[-1]), flush=True)
Path(__file__).with_name("parser-stress.json").write_text(json.dumps(report, indent=2) + "\n")
