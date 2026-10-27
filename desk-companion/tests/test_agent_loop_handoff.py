"""The handoff note names the extension points that exist in this tree."""

from pathlib import Path


def test_agent_loop_handoff_names_the_live_extension_points():
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "agent-loop-handoff.md").read_text(encoding="utf-8")
    for needle in (
        "AgentLoop",
        "execute_tool()",
        "CAPABILITIES",
        "pack_conversation",
        "voice_context_note",
        "apply_voice_event",
        "scripts/tool_eval.py",
        "deltas()",
    ):
        assert needle in text
    assert "PR #4" in text
    assert "记忆命中" in text
    assert "说话时看不到排序后的记忆" not in text
    assert text.index("语音不跑有界多步循环") < text.index("字符预算没有罩住真正送出的提示")
