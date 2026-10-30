"""Bridge to the shared run-tool registry; approval is intentionally absent."""

import json

from .contracts import ConnectorCall
from .schema import ConnectorError, canonical


class ConnectorToolAdapter:
    effect = True  # Even reads transmit exact arguments and require owner review here.
    schema = ConnectorCall

    def __init__(self, tool_id):
        self.name = tool_id

    def argument_schema(self, runtime):
        schema = self.schema.model_json_schema()
        _, grant = runtime.connectors._resolve(self.name)
        schema["properties"]["arguments"] = json.loads(canonical(grant.input_schema))
        return schema

    def available(self, runtime, run):
        return bool(
            getattr(runtime, "connectors", None)
            and self.name in run.get("connector_tool_ids", [])
            and self.name in runtime.connectors.grants
        )

    def validate(self, runtime, run, arguments):
        value = self.schema.model_validate(arguments).model_dump()
        if not self.available(runtime, run):
            raise ConnectorError("CONNECTOR_TOOL_NOT_GRANTED", 403)
        runtime.connectors.validate_run(run, self.name, value["arguments"])
        return value

    @staticmethod
    def _receipt(item):
        state = {
            "review": "pending",
            "queued": "pending",
            "preflight": "pending",
            "dispatching": "pending",
            "observed_result": "observed",
            "unknown_effect": "unknown",
        }.get(item["state"], "rejected")
        observed = item.get("result")
        return {
            "reference_id": item["id"],
            "state": state,
            "result": {
                "connector_intent_id": item["id"],
                "state": item["state"],
                "code": item["code"],
                "verified": False,
                "review_url": "/api/connectors/intents/" + item["id"],
                "observed_at": item["updated_at"],
                "observation": {
                    key: observed[key]
                    for key in ("sha256", "snapshot_sha256", "is_error", "verified")
                }
                if observed
                else None,
            },
        }

    def dispatch(self, runtime, run, arguments, key, checkpoint):
        value = self.validate(runtime, run, arguments)
        checkpoint()
        item = runtime.connectors.prepare_for_run(
            run, self.name, value["arguments"], key, public_only=value["public_only"]
        )
        checkpoint()
        return self._receipt(item)

    def _lookup(self, runtime, run, arguments, key):
        value = self.schema.model_validate(arguments).model_dump()
        return runtime.connectors.lookup_operation(
            key,
            run_id=run["id"],
            session_hash=run["session_hash"],
            tool_id=self.name,
            arguments=value["arguments"],
        )

    def recover(self, runtime, run, arguments, key):
        item = self._lookup(runtime, run, arguments, key)
        return self._receipt(item) if item else None

    def verify(self, runtime, run, receipt):
        self.validate(runtime, run, receipt["arguments"])
        item = self._lookup(runtime, run, receipt["arguments"], receipt["operation_key"])
        if not item or item["id"] != receipt["reference_id"]:
            return {"state": "unknown", "code": "CONNECTOR_RECEIPT_MISSING"}
        current = self._receipt(item)
        result = {**current["result"], "state": current["state"]}
        observed = item.get("result")
        if current["state"] == "observed" and observed:
            text = "\n".join(observed["text"])
            if observed["structured_content"] is not None:
                text += "\n" + canonical(observed["structured_content"]).decode()
            encoded = text.encode()
            excerpt = encoded[:1800].decode("utf-8", errors="ignore")
            result["evidence"] = {
                "id": "connector:" + current["reference_id"],
                "kind": "connector",
                "record_id": self.name,
                "label": self.name,
                "sha256": observed["sha256"],
                "version": 1,
                "at": item["updated_at"],
                "excerpt": excerpt,
                "coverage": {
                    "scope": "untrusted_tool_response",
                    "truncated": len(encoded) > 1800,
                    "returned_bytes": len(encoded),
                    "excerpt_bytes": len(excerpt.encode()),
                    "independent_outcome_verified": False,
                },
                "statistics": None,
                "provenance": None,
            }
        return result

    def cancel(self, runtime, run, receipt):
        current = self.recover(runtime, run, receipt["arguments"], receipt["operation_key"])
        if current and current["reference_id"] == receipt["reference_id"]:
            runtime.connectors.cancel_internal(current["reference_id"])


def connector_adapters(service):
    return {tool_id: ConnectorToolAdapter(tool_id) for tool_id in service.grants}
