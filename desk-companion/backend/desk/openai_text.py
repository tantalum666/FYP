"""Bounded Responses adapter; business tools and approvals remain in the core."""

from .bounded_json import bounded_json_post


class OpenAITextAdapter:
    name = "openai"

    def complete(self, client, config, prompt, content, max_tokens=1600, *, attachment_parts=None):
        user_content = "Return the requested JSON object.\n" + content
        if attachment_parts:
            user_content = [{"type": "input_text", "text": user_content}, *attachment_parts]
        response = bounded_json_post(
            client,
            config.endpoint,
            headers={"Authorization": "Bearer " + config.api_key},
            json_body={
                "model": config.model,
                "instructions": prompt,
                # The provider's JSON-mode preflight checks input messages, not
                # only the separate instructions field, for the format request.
                "input": [{"role": "user", "content": user_content}],
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
