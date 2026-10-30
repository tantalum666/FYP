"""Hosted text adapters. A new provider is one class plus a registry entry.

Callers keep using TextAssistant.generate. They do not branch on the vendor.
The fake adapter is an offline demonstration. It never opens a network connection.
`deltas` yields text pieces. `complete` remains the one-shot fallback.
"""

import json

from .store import DomainError
from .bounded_json import bounded_json_post


class QwenTextAdapter:
    name = "qwen"

    def complete(self, client, config, prompt, content, max_tokens=1600):
        body = bounded_json_post(
            client,
            config.endpoint,
            headers={"Authorization": "Bearer " + config.api_key},
            json_body={
                "model": config.model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
                "stream": False,
                "max_tokens": max_tokens,
                "enable_thinking": False,
            },
        )
        usage = body.get("usage", {})
        return body["choices"][0]["message"]["content"], usage if isinstance(usage, dict) else {}

    def deltas(self, client, config, prompt, content):
        """Yield text pieces from the DashScope stream. Usage lands in the box."""
        box: dict = {}
        payload = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
            "response_format": {"type": "json_object"},
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": 1600,
            "enable_thinking": False,
        }

        def iterate():
            with client.stream(
                "POST",
                config.endpoint,
                headers={"Authorization": "Bearer " + config.api_key},
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    piece, usage = _qwen_line(line)
                    if usage:
                        box.clear()
                        box.update(usage)
                    if piece:
                        yield piece

        return iterate(), box


class GeminiTextAdapter:
    name = "gemini"

    def complete(self, client, config, prompt, content, max_tokens=1600):
        base = config.endpoint or "https://generativelanguage.googleapis.com/v1beta"
        body = bounded_json_post(
            client,
            base + "/models/" + config.model + ":generateContent",
            headers={"x-goog-api-key": config.api_key},
            json_body={
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": [{"role": "user", "parts": [{"text": content}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "maxOutputTokens": max_tokens,
                },
            },
        )
        raw = "".join(
            part.get("text", "")
            for part in body["candidates"][0]["content"]["parts"]
            if not part.get("thought")
        )
        usage = body.get("usageMetadata", {})
        return raw, usage if isinstance(usage, dict) else {}

    def deltas(self, client, config, prompt, content):
        """Yield text pieces from streamGenerateContent. Thoughts are skipped."""
        box: dict = {}
        base = config.endpoint or "https://generativelanguage.googleapis.com/v1beta"
        url = base + "/models/" + config.model + ":streamGenerateContent?alt=sse"
        payload = {
            "systemInstruction": {"parts": [{"text": prompt}]},
            "contents": [{"role": "user", "parts": [{"text": content}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": 1600,
            },
        }

        def iterate():
            with client.stream(
                "POST", url, headers={"x-goog-api-key": config.api_key}, json=payload
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    piece, usage = _gemini_line(line)
                    if usage:
                        box.clear()
                        box.update(usage)
                    if piece:
                        yield piece

        return iterate(), box


def _data(line: str) -> str | None:
    text = line.strip()
    if not text.startswith("data:"):
        return None
    data = text[5:].strip()
    if not data or data == "[DONE]":
        return None
    return data


def _qwen_line(line: str) -> tuple[str, dict]:
    data = _data(line)
    if data is None:
        return "", {}
    body = json.loads(data)
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    choices = body.get("choices") or []
    delta = choices[0].get("delta", {}) if choices else {}
    piece = delta.get("content") if isinstance(delta, dict) else ""
    return piece if isinstance(piece, str) else "", usage


def _gemini_line(line: str) -> tuple[str, dict]:
    data = _data(line)
    if data is None:
        return "", {}
    body = json.loads(data)
    usage = body.get("usageMetadata") if isinstance(body.get("usageMetadata"), dict) else {}
    candidates = body.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    piece = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and not part.get("thought") and isinstance(part.get("text"), str)
    )
    return piece, usage


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
