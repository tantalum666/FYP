from desk.voice_presentation import speech_result


def test_speech_title_removes_layout_separators_without_mutating_business_data():
    original = {
        "tasks": [{"id": "same-id", "title": "QA · Offline planner / real print applications"}]
    }
    spoken = speech_result(original)
    assert spoken["tasks"][0]["speech_title"] == "QA, Offline planner, real print applications"
    assert "speech_title" not in original["tasks"][0]
    assert spoken["tasks"][0]["title"] == original["tasks"][0]["title"]
    assert (
        speech_result({"title": "2026/11/16 1/2 budget/report"})["speech_title"]
        == "2026/11/16 1/2 budget/report"
    )
