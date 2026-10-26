#!/usr/bin/env python3
"""Step the demo through the same API the future acquisition service will use."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]


def execute(action, amount=0, seconds=0, base="http://127.0.0.1:8799", service_type="buffet_self_service", initial_g=1500):
    config = json.loads((ROOT / ".runtime/config.json").read_text())
    creds = json.loads((ROOT / ".runtime/credentials.json").read_text())
    state_file = ROOT / ".runtime/simulator.json"
    key = str(uuid4())
    with httpx.Client(base_url=base, timeout=15, trust_env=False) as client:
        headers = {"X-Device-Key": config["simulator_key"], "Idempotency-Key": key}
        if action in {"new", "replay"}:
            result = client.post("/v1/dev/runs", headers=headers, json={
                "workspace_id": creds["workspace_id"], "client_operation_id": key,
                "source": "replay" if action == "replay" else "simulated",
                "service_type": service_type, "initial_g": initial_g})
        else:
            if not state_file.exists():
                raise SystemExit("Create a run first with: client.py new")
            state = json.loads(state_file.read_text())
            result = client.post(f"/v1/dev/runs/{state['run_id']}/actions", headers=headers,
                                 json={"action": action, "client_operation_id": key,
                                       "amount_g": amount, "seconds": seconds})
        if result.is_error:
            raise SystemExit(f"{result.status_code}: {result.text}")
        data = result.json()
        if action in {"new", "replay"}:
            state_file.write_text(json.dumps(data, indent=2))
        return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["new", "replay", "consume", "add", "remove", "unstable",
                        "occlude", "restore", "advance", "disconnect", "closing", "rebind", "pause", "resume"])
    parser.add_argument("amount", nargs="?", type=int, default=0)
    parser.add_argument("--seconds", type=int, default=0)
    parser.add_argument("--service", choices=['buffet_self_service', 'staff_portioned'], default='buffet_self_service')
    parser.add_argument("--initial", type=int, default=1500)
    args = parser.parse_args()
    print(json.dumps(execute(args.action, args.amount, args.seconds, service_type=args.service, initial_g=args.initial), indent=2))
