"""Hosted text adapters. A new provider is one class plus a registry entry.

Callers keep using TextAssistant.generate. They do not branch on the vendor.
The fake adapter is an offline demonstration. It never opens a network connection.
"""

import json

from .store import DomainError


class QwenTextAdapter:
    name = "qwen"

    def complete(self, client, config, prompt, content):
        result = client.post(
            config.endpoint,
            headers={"Authorization": "Bearer " + config.api_key},
            json={
                "model": config.model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
                "stream": False,
                "max_tokens": 1600,
                "enable_thinking": False,
            },
        )
        result.raise_for_status()
        body = result.json()
        usage = body.get("usage", {})
        return body["choices"][0]["message"]["content"], usage if isinstance(usage, dict) else {}


class GeminiTextAdapter:
    name = "gemini"

    def complete(self, client, config, prompt, content):
        base = config.endpoint or "https://generativelanguage.googleapis.com/v1beta"
        result = client.post(
            base + "/models/" + config.model + ":generateContent",
            headers={"x-goog-api-key": config.api_key},
            json={
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": [{"role": "user", "parts": [{"text": content}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "maxOutputTokens": 1600,
                },
            },
        )
        result.raise_for_status()
        body = result.json()
        raw = "".join(
            part.get("text", "")
            for part in body["candidates"][0]["content"]["parts"]
            if not part.get("thought")
        )
        usage = body.get("usageMetadata", {})
        return raw, usage if isinstance(usage, dict) else {}


class FakeTextAdapter:
    """Deterministic offline replies for the FYP demonstration. No HTTP."""

    name = "fake"

    def complete(self, client, config, prompt, content):
        del client, config
        return json.dumps(fake_reply(prompt, content), ensure_ascii=False), {}


def fake_reply(prompt, content):
    schema_title = ""
    marker = "Return only JSON matching this schema: "
    if marker in prompt:
        try:
            schema_title = json.loads(prompt.split(marker, 1)[1]).get("title", "")
        except (json.JSONDecodeError, TypeError, AttributeError):
            schema_title = ""
    if schema_title == "FollowUpAdvice":
        return {
            "en": "Review the demo note, then record one sentence of progress.",
            "zh": "先看演示笔记，再记下一句进展。",
        }
    try:
        body = json.loads(content) if content else {}
    except json.JSONDecodeError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    message = str(body.get("user_message") or "")
    folded = message.casefold()
    memories = body.get("memory") if isinstance(body.get("memory"), list) else []
    if "cityu" in folded or "香港城市大学" in message:
        match = next(
            (
                row
                for row in memories
                if isinstance(row, dict)
                and ("CUHK" in str(row.get("body", "")) or "中文大学" in str(row.get("body", "")))
            ),
            None,
        )
        if match and match.get("id") and match.get("version"):
            return {
                "message": "I prepared a correction. It is not saved until you confirm it.",
                "tool": "memory_replace_draft",
                "arguments": {
                    "memory_id": match["id"],
                    "expected_version": match["version"],
                    "body": "The owner studies at CityU.",
                },
            }
        return {
            "message": "No CUHK fact is active, so there is nothing to correct.",
            "tool": "none",
            "arguments": {},
        }
    if "demo note" in folded or "演示笔记" in message:
        return {
            "message": "A note is ready for you to approve. I have not written the file.",
            "tool": "computer_job_draft",
            "arguments": {
                "action": "save_note",
                "title": "FYP demo note",
                "content": "Offline demo note. Approve, then wait for the independent read-back.",
            },
        }
    if "quiet" in folded or "安静" in message:
        return {
            "message": "Quiet hours hold task check-ins until they end. Calendar reminders stay on screen.",
            "tool": "none",
            "arguments": {},
        }
    return {
        "message": "Demo mode is offline. You can correct the CUHK memory, ask about quiet hours, or ask for a demo note.",
        "tool": "none",
        "arguments": {},
    }


ADAPTERS = {
    QwenTextAdapter.name: QwenTextAdapter(),
    GeminiTextAdapter.name: GeminiTextAdapter(),
    FakeTextAdapter.name: FakeTextAdapter(),
}


def text_adapter(provider):
    try:
        return ADAPTERS[provider]
    except KeyError:
        raise DomainError("TEXT_AI_NOT_CONFIGURED", 503) from None
