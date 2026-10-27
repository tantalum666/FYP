"""Hosted text adapters. A new provider is one class plus a registry entry.

Callers keep using TextAssistant.generate. They do not branch on the vendor.
"""

from .store import DomainError


class QwenTextAdapter:
    name = "qwen"

    def complete(self, client, config, prompt, content, max_tokens=1600):
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
                "max_tokens": max_tokens,
                "enable_thinking": False,
            },
        )
        result.raise_for_status()
        body = result.json()
        usage = body.get("usage", {})
        return body["choices"][0]["message"]["content"], usage if isinstance(usage, dict) else {}


class GeminiTextAdapter:
    name = "gemini"

    def complete(self, client, config, prompt, content, max_tokens=1600):
        base = config.endpoint or "https://generativelanguage.googleapis.com/v1beta"
        result = client.post(
            base + "/models/" + config.model + ":generateContent",
            headers={"x-goog-api-key": config.api_key},
            json={
                "systemInstruction": {"parts": [{"text": prompt}]},
                "contents": [{"role": "user", "parts": [{"text": content}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "maxOutputTokens": max_tokens,
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


ADAPTERS = {
    QwenTextAdapter.name: QwenTextAdapter(),
    GeminiTextAdapter.name: GeminiTextAdapter(),
}


def text_adapter(provider):
    try:
        return ADAPTERS[provider]
    except KeyError:
        raise DomainError("TEXT_AI_NOT_CONFIGURED", 503) from None
