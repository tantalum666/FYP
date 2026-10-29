import json

import pytest

from scripts.app_workflow_reference import FIXTURE, quote_results, reference


def test_baseline_then_infeasible_correction_then_changed_solution():
    result = reference()
    initial = result["phases"]["initial"]["budget"]["selected"]
    assert (initial["supplier"], initial["total_hkd"]) == ("Aster", "809.60")
    assert result["phases"]["revision"]["budget"]["selected"] is None
    assert result["phases"]["revision"]["budget"]["clarification_required"]
    final = result["phases"]["clarified"]["budget"]["selected"]
    assert (final["supplier"], final["total_hkd"]) == ("Delta", "669.24")
    assert (final["booklets_purchased"], final["delivered_hkd"], final["reserve_hkd"]) == (
        50,
        "608.40",
        "60.84",
    )


def test_current_delivery_and_item_only_discount_control_eligibility():
    data = reference()["phases"]["clarified"]["budget"]["quotes"]
    cedar = next(r for r in data if r["supplier"] == "Cedar")
    assert cedar["quote_id"] == "C-2" and cedar["exclusions"] == ["late_delivery"]
    assert cedar["total_hkd"] == "583.00"
    birch = next(r for r in data if r["supplier"] == "Birch")
    assert birch["delivered_hkd"] == "613.80" and birch["total_hkd"] == "675.18"


def test_newer_status_and_meeting_override_do_not_duplicate_or_revive_work():
    data = reference()["tasks"]
    assert (data["unique_tasks"], data["remaining_count"], data["remaining_hours"]) == (
        9,
        7,
        "14.5",
    )
    states = {t["id"]: t for t in data["tasks"]}
    assert states["T02"]["status"] == "in_progress"
    assert states["T04"]["status"] == "completed" and states["T04"]["remaining_hours"] == "0"
    assert states["T07"]["remaining_hours"] == "1.5"


def test_rehearsals_respect_calendar_collision_and_user_correction():
    phases = reference()["phases"]
    initial = phases["initial"]["rehearsals"]
    final = phases["clarified"]["rehearsals"]
    assert [x["start"] for x in initial] == [
        "2026-11-03T16:15:00+08:00",
        "2026-11-04T15:15:00+08:00",
    ]
    assert [x["start"] for x in final] == ["2026-11-03T16:15:00+08:00", "2026-11-05T15:15:00+08:00"]
    assert final[0] == initial[0]


def test_small_fx_variation_changes_winner_without_hardcoding():
    case = json.loads((FIXTURE / "controller/case.json").read_text())
    quotes = json.loads((FIXTURE / "controller/quotes.json").read_text())
    varied = quote_results(case, quotes, {"HKD": "1.00", "USD": "7.90"}, "clarified")
    assert varied["selected"]["supplier"] == "Birch"
    with pytest.raises(ValueError, match="MISSING_FX_RATE"):
        quote_results(case, quotes, {"HKD": "1.00"}, "clarified")


def test_reference_calculation_never_claims_an_application_or_agent_pass():
    data = reference()
    assert data["reference_only"] is True
    assert data["application_execution"] == "not_run"
    assert data["candidate_submission"] == "not_evaluated"
