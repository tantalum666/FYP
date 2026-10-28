import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

from desk.text_ai import TextConfig
from desk.text_providers import text_adapter

ROOT = Path(__file__).resolve().parents[1]


def load_smoke():
    path = ROOT / "scripts" / "smoke_text_provider.py"
    spec = importlib.util.spec_from_file_location("smoke_text_provider", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_script_exits_without_a_provider_call():
    env = {key: value for key, value in os.environ.items() if not key.startswith("DESK_")}
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "smoke_text_provider.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert "smoke skipped" in result.stdout
    assert "smoke ok" not in result.stdout


def test_partial_arming_never_returns_a_cap():
    smoke = load_smoke()
    armed = {
        "DESK_SMOKE_TEXT": "1",
        "DESK_TEXT_PROVIDER": "qwen",
        "DESK_TEXT_MODEL": "qwen-test",
        "DESK_TEXT_API_KEY": "not-sent",
        "DESK_TEXT_ENDPOINT": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
    }
    assert smoke.readiness(armed) is None
    assert smoke.readiness({**armed, "DESK_SMOKE_MAX_TOKENS": "0"}) is None
    assert smoke.readiness({**armed, "DESK_SMOKE_MAX_TOKENS": "65"}) is None
    assert smoke.readiness({**armed, "DESK_SMOKE_MAX_TOKENS": "32"}) == 32
    assert smoke.run({**armed, "DESK_SMOKE_MAX_TOKENS": "1000"}) == 0


def test_armed_path_passes_the_cap_to_a_stub_instead_of_the_network():
    smoke = load_smoke()
    seen = []

    def caller(config, cap):
        seen.append((config.provider, cap, config.api_key))
        return '{"ok":true}', {}

    env = {
        "DESK_SMOKE_TEXT": "1",
        "DESK_TEXT_PROVIDER": "gemini",
        "DESK_TEXT_MODEL": "gemini-test",
        "DESK_TEXT_API_KEY": "not-sent",
        "DESK_SMOKE_MAX_TOKENS": "8",
    }
    assert smoke.run(env, caller) == 0
    assert seen == [("gemini", 8, "not-sent")]


def test_adapters_can_send_a_smaller_cap_than_the_product_default():
    seen = []

    def response(request):
        if "dashscope" in request.url.host:
            seen.append(json.loads(request.content)["max_tokens"])
            return httpx.Response(
                200, json={"choices": [{"message": {"content": "{}"}}], "usage": {}}
            )
        seen.append(json.loads(request.content)["generationConfig"]["maxOutputTokens"])
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}], "usageMetadata": {}},
        )

    qwen = TextConfig(
        provider="qwen",
        model="qwen-test",
        endpoint="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        api_key="fixture-key",
    )
    gemini = TextConfig(provider="gemini", model="gemini-test", api_key="fixture-key")
    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        text_adapter("qwen").complete(client, qwen, "p", "c", max_tokens=8)
        text_adapter("gemini").complete(client, gemini, "p", "c", max_tokens=8)
    assert seen == [8, 8]


def test_workflow_does_not_invoke_the_smoke_script():
    workflow = ROOT.parent / ".github" / "workflows" / "desk-companion.yml"
    if not workflow.exists():
        return
    text = workflow.read_text(encoding="utf-8")
    assert "smoke_text_provider" not in text
    assert "DESK_SMOKE_TEXT" not in text
