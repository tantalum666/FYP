from typing import Literal

from pydantic import Field

from .schemas import ID, Input


class ConsoleLogin(Input):
    workspace_id: ID | None = None
    setup_key: str = Field(pattern=r"^[A-Za-z0-9_-]{16,200}$")


class MealStart(Input):
    client_operation_id: ID
    expected_run_id: ID | None = None
    mode: Literal["personal", "school"]


class PairApply(Input):
    client_operation_id: ID
    code: str = Field(pattern=r"^SPM-[A-F0-9]{12}$")


class MealAction(Input):
    client_operation_id: ID
    expected_version: int = Field(strict=True, ge=1)
    action: Literal[
        "confirm_empty",
        "approve_pairing",
        "reject_pairing",
        "rotate_code",
        "prepare_portion",
        "confirm_portion",
        "cancel_portion",
        "correct_food",
        "finish_plating",
        "complete",
        "cancel",
    ]
    request_id: ID | None = None
    reference_id: ID | None = None
    portion_id: ID | None = None
    observation_id: ID | None = None
    remaining_reason: (
        Literal["not_measured", "pan_removed", "unreliable", "contents_changed"] | None
    ) = None
    note: str = Field(default="", max_length=500)


class ConsoleSimulation(Input):
    client_operation_id: ID
    run_id: ID
    action: Literal["set", "unstable", "remove", "advance"]
    weight_g: int = Field(default=0, strict=True, ge=0, le=5000)
    seconds: int = Field(default=1, strict=True, ge=1, le=3600)
