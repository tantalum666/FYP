"""Hosted text adapters. A new provider is one class plus a registry entry.

Callers keep using TextAssistant.generate. They do not branch on the vendor.
`deltas` yields text pieces. `complete` remains the one-shot fallback.
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


ADAPTERS = {
    QwenTextAdapter.name: QwenTextAdapter(),
    GeminiTextAdapter.name: GeminiTextAdapter(),
}


def text_adapter(provider):
    try:
        return ADAPTERS[provider]
    except KeyError:
        raise DomainError("TEXT_AI_NOT_CONFIGURED", 503) from None
