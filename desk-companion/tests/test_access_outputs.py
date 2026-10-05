from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from desk.access import AccessService, PairingClaim, PairingDecision, PairingRequest
from desk.outputs import OutputHeartbeat, OutputReceipt, OutputRequest, OutputService
from desk.store import DomainError, Store


@pytest.fixture
def services(tmp_path):
    clock = [datetime(2026, 10, 2, 12, tzinfo=UTC)]
    store = Store(tmp_path, password="fixture-only", clock=lambda: clock[0])
    return AccessService(store), OutputService(store), clock


def pair(access):
    issued = access.issue("controller", uuid4().hex)
    request = access.request(PairingRequest(code=issued["code"], name="Test phone"))
    claim = PairingClaim(request_id=request["request_id"], secret=request["secret"])
    assert access.claim(claim) == {"state": "pending"}
    access.decide(PairingDecision(request_id=request["request_id"], action="approve"), uuid4().hex)
    return access.claim(claim), claim


def test_pair_requires_approval_and_revoke_invalidates_existing_token(services):
    access, _, _ = services
    result, claim = pair(access)
    assert access.principal(bearer=result["token"])["kind"] == "controller"
    assert access.claim(claim)["token"] == result["token"]  # Lost response can be recovered.
    access.revoke(result["client_id"], uuid4().hex)
    assert access.principal(bearer=result["token"]) is None
    with pytest.raises(DomainError):
        access.claim(claim)


def test_pair_code_is_single_use_and_claim_secret_is_required(services):
    access, _, clock = services
    issued = access.issue("display", uuid4().hex)
    req = access.request(PairingRequest(code=issued["code"], name="Screen"))
    with pytest.raises(DomainError):
        access.request(PairingRequest(code=issued["code"], name="Intruder"))
    with pytest.raises(DomainError):
        access.claim(PairingClaim(request_id=req["request_id"], secret="wrong-secret" * 4))
    clock[0] += timedelta(minutes=6)
    with pytest.raises(DomainError):
        access.decide(PairingDecision(request_id=req["request_id"], action="approve"), uuid4().hex)


def test_display_enrolment_is_repeat_safe_and_has_no_password_in_listing(services):
    access, _, clock = services
    one = access.enrol_display("Screen", "enrol-once")
    assert access.enrol_display("Screen", "enrol-once") == one
    assert len(access.listing()["clients"]) == 1
    assert "token" not in str(access.listing())
    clock[0] += timedelta(days=7)
    assert access.principal(device_token=one["token"])["kind"] == "display"


def test_only_verified_available_named_outputs_are_queued(services):
    _, output, _ = services
    request = OutputRequest(kind="arm", preset="attention")
    with pytest.raises(DomainError, match="HARDWARE_NOT_READY"):
        output.request(request, "offline")
    output.heartbeat(OutputHeartbeat(source="replay", capabilities=["arm"], stopped=False))
    with pytest.raises(DomainError, match="HARDWARE_NOT_READY"):
        output.enable("unverified")
    output.heartbeat(
        OutputHeartbeat(
            source="replay", capabilities=["arm"], hardware_verified=True, stopped=False
        )
    )
    output.enable("enable")
    with pytest.raises(DomainError, match="PRESET_NOT_ALLOWED"):
        output.request(OutputRequest(kind="arm", preset="angle_180"), "arbitrary")
    result = output.request(request, "once")
    assert result["state"] == "queued"
    assert output.request(request, "once") == result
    assert len(output.claim()["commands"]) == 1
    assert output.claim()["commands"] == []
    receipt = output.receipt(
        result["command_id"], OutputReceipt(status="executed", detail="simulation")
    )
    assert receipt["state"] == "simulated"


def test_stop_and_deadline_prevent_delayed_or_replayed_motion(services):
    _, output, clock = services
    output.heartbeat(
        OutputHeartbeat(
            source="replay", capabilities=["arm"], hardware_verified=True, stopped=False
        )
    )
    output.enable("enable")
    one = output.request(OutputRequest(kind="arm", preset="attention"), "one")
    output.claim()
    output.emergency_stop("stop")
    assert not output.claim()["commands"]
    with pytest.raises(DomainError, match="COMMAND_EXPIRED"):
        output.receipt(one["command_id"], OutputReceipt(status="executed", detail="simulation"))
    output.enable("enable-again")
    output.request(OutputRequest(kind="arm", preset="rest"), "two")
    clock[0] += timedelta(seconds=6)
    assert output.claim()["commands"] == []
    assert not output.snapshot()["connected"]


def test_restart_expires_commands_and_latches_stop(services):
    _, output, _ = services
    output.heartbeat(
        OutputHeartbeat(
            source="replay", capabilities=["light"], hardware_verified=True, stopped=False
        )
    )
    output.enable("enable")
    output.request(OutputRequest(kind="light", preset="attention"), "light")
    restarted = OutputService(output.store)
    assert restarted.snapshot()["stopped"]
    assert restarted.history()[0]["state"] == "expired"
