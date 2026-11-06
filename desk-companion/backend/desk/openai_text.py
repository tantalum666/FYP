"""Bounded Responses adapter; business tools and approvals remain in the core."""

from .bounded_json import bounded_json_post


class OpenAITextAdapter:
    name = "openai"

    def complete(self, client, config, prompt, content, max_tokens=1600):
        response = bounded_json_post(
            client,
            config.endpoint,
            headers={"Authorization": "Bearer " + config.api_key},
            json_body={
                "model": config.model,
                "instructions": prompt,
                "input": [{"role": "user", "content": content}],
                "text": {"format": {"type": "json_object"}},
                "reasoning": {"effort": "low"},
                "max_output_tokens": max_tokens,
                "store": False,
            },
        )
        if response.get("status") != "completed":
            raise ValueError("Incomplete OpenAI response")
        pieces = []
        for item in response.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "refusal":
                    raise ValueError("OpenAI declined the request")
                if part.get("type") == "output_text":
                    pieces.append(part["text"])
        if not pieces:
            raise ValueError("No structured OpenAI response")
        usage = response.get("usage", {})
        return "".join(pieces), usage if isinstance(usage, dict) else {}
