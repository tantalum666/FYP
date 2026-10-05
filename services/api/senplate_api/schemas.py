from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ID = Annotated[str, StringConstraints(min_length=1, max_length=80)]
Grams = Annotated[int, Field(strict=True, ge=0, le=5000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=300)


class Decision(Input):
    client_operation_id: ID
    expected_version: int = Field(strict=True, ge=1)
    decision: Literal["accept", "adjust", "reject"]
    accepted_g: Grams | None = None
    reason_code: str | None = Field(default=None, min_length=1, max_length=100)


class TaskAction(Input):
    client_operation_id: ID
    expected_version: int = Field(strict=True, ge=1)
    action: Literal[
        "start", "mark_ready", "begin_replenishment", "confirm_replenishment",
        "request_review", "close_unverified", "cancel",
    ]
    physical_event_id: ID | None = None
    note: str = Field(default="", max_length=500)


class ObservationInput(Input):
    observation_id: ID
    device_id: ID
    session_id: ID
    boot_id: ID
    sequence: int = Field(strict=True, ge=0)
    observed_at: datetime
    gross_g: int = Field(strict=True, ge=-5000, le=10000)
    tare_g: Grams = 500
    net_g: int = Field(strict=True, ge=-5000, le=10000)
    weight_quality: Literal["valid", "unstable", "invalid"] = "valid"
    pan_presence: Literal["present", "absent"] = "present"
    vision_status: Literal["available", "occluded", "unknown", "unavailable"] = "unavailable"
    calibration_version: str = Field(min_length=1, max_length=80)
    binding_revision: int = Field(strict=True, ge=1)


class ObservationBatch(Input):
    observations: list[ObservationInput] = Field(min_length=1, max_length=100)


class Heartbeat(Input):
    session_id: ID
    device_id: ID
    at: datetime


class CreateRun(Input):
    workspace_id: ID
    client_operation_id: ID
    source: Literal["simulated", "replay"] = "simulated"
    food_name: str = Field(default="香草烤鸡", min_length=1, max_length=120)
    food_name_en: str = Field(default="Herb-roasted chicken", min_length=1, max_length=120)
    service_type: Literal["buffet_self_service", "staff_portioned"] = "buffet_self_service"
    initial_g: Grams = 1500


class SimulationAction(Input):
    client_operation_id: ID
    action: Literal[
        "consume", "add", "remove", "unstable", "occlude", "restore",
        "advance", "disconnect", "closing", "rebind", "pause", "resume",
    ]
    amount_g: Grams = 0
    seconds: int = Field(default=0, strict=True, ge=0, le=3600)


class CartLine(Input):
    menu_item_id: ID
    item_version: int = Field(strict=True, ge=1)
    quantity: int = Field(strict=True, ge=1, le=20)


class SubmitOrder(Input):
    client_operation_id: ID
    run_id: ID
    lines: list[CartLine] = Field(min_length=1, max_length=10)


class OrderAction(Input):
    client_operation_id: ID
    expected_version: int = Field(strict=True, ge=1)
    action: Literal["accept", "reject", "cancel", "request_cancel", "approve_cancel",
                    "deny_cancel", "begin_preparation", "confirm_fulfillment", "collect"]
    physical_event_id: ID | None = None
    physical_event_ids: list[ID] = Field(default_factory=list, max_length=30)
    pickup_code: str | None = Field(default=None, pattern=r"^[0-9]{6}$")
    allow_variance: bool = False
    note: str = Field(default="", max_length=500)


class MenuItemAction(Input):
    client_operation_id: ID
    expected_version: int = Field(strict=True, ge=1)
    name_en: str = Field(min_length=1, max_length=120)
    name_zh: str = Field(min_length=1, max_length=120)
    description_en: str = Field(max_length=500)
    description_zh: str = Field(max_length=500)
    allergens_en: str = Field(max_length=200)
    allergens_zh: str = Field(max_length=200)
    price_minor: int = Field(strict=True, ge=0, le=100000)
    published: bool
    enabled: bool
    manual_stock: int = Field(strict=True, ge=0, le=10000)


class ServiceAction(Input):
    client_operation_id: ID
    expected_version: int = Field(strict=True, ge=1)
    service_type: Literal["buffet_self_service", "staff_portioned"]
