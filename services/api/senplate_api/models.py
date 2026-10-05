from datetime import datetime
from uuid import uuid4
import secrets

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    activity_version: Mapped[int] = mapped_column(Integer, default=0)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    active_run_id: Mapped[str | None] = mapped_column(String(36))
    menu_code: Mapped[str] = mapped_column(String(32), unique=True,
                                         default=lambda: "SP-" + secrets.token_hex(5).upper())


class Membership(Base):
    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    station_id: Mapped[str] = mapped_column(String(36), unique=True, default=uid)
    device_id: Mapped[str] = mapped_column(String(36), default=uid)
    boot_id: Mapped[str] = mapped_column(String(36), default=uid)
    origin: Mapped[str] = mapped_column(String(20), default="simulated")
    mode: Mapped[str] = mapped_column(String(20), default="foodservice")
    food_name: Mapped[str] = mapped_column(String(120), default="香草烤鸡")
    food_name_en: Mapped[str] = mapped_column(String(120), default="Herb-roasted chicken")
    food_id: Mapped[str] = mapped_column(String(36), default=uid)
    clock_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    measurement_status: Mapped[str] = mapped_column(String(20), default="not_ready")
    vision_status: Mapped[str] = mapped_column(String(20), default="unavailable")
    food_binding: Mapped[str] = mapped_column(String(20), default="confirmed")
    net_g: Mapped[int | None] = mapped_column(Integer)
    last_valid_g: Mapped[int | None] = mapped_column(Integer)
    last_valid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sequence: Mapped[int] = mapped_column(Integer, default=-1)
    binding_revision: Mapped[int] = mapped_column(Integer, default=1)
    snapshot_version: Mapped[int] = mapped_column(Integer, default=0)
    provided_g: Mapped[int] = mapped_column(Integer, default=0)
    removed_g: Mapped[int] = mapped_column(Integer, default=0)
    threshold_g: Mapped[int] = mapped_column(Integer, default=700)
    batch_g: Mapped[int] = mapped_column(Integer, default=1000)
    lead_seconds: Mapped[int] = mapped_column(Integer, default=600)
    state: Mapped[str] = mapped_column(String(20), default="active")
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_method: Mapped[str] = mapped_column(String(30), default="fixed_threshold")
    service_type: Mapped[str] = mapped_column(String(30), default="buffet_self_service")
    order_counter: Mapped[int] = mapped_column(Integer, default=0)
    service_version: Mapped[int] = mapped_column(Integer, default=1)


class MenuItem(Base):
    __tablename__ = "menu_items"
    __table_args__ = (UniqueConstraint("run_id", "slug"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    slug: Mapped[str] = mapped_column(String(40))
    name_en: Mapped[str] = mapped_column(String(120))
    name_zh: Mapped[str] = mapped_column(String(120))
    description_en: Mapped[str] = mapped_column(String(500), default="")
    description_zh: Mapped[str] = mapped_column(String(500), default="")
    allergens_en: Mapped[str] = mapped_column(String(200), default="Not provided. Ask the kitchen.")
    allergens_zh: Mapped[str] = mapped_column(String(200), default="暂无资料，请咨询厨房。")
    price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="HKD")
    stock_source: Mapped[str] = mapped_column(String(20))
    portion_g: Mapped[int | None] = mapped_column(Integer)
    food_id: Mapped[str | None] = mapped_column(String(36))
    binding_revision: Mapped[int | None] = mapped_column(Integer)
    manual_stock: Mapped[int] = mapped_column(Integer, default=0)
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    quote_version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("run_id", "number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24), default="submitted")
    version: Mapped[int] = mapped_column(Integer, default=1)
    total_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="HKD")
    pickup_code: Mapped[str] = mapped_column(String(6), default=lambda: f"{secrets.randbelow(1000000):06d}")
    pickup_failures: Mapped[int] = mapped_column(Integer, default=0)
    pickup_blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    cancellation: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    preparation_sequence: Mapped[int | None] = mapped_column(Integer)
    binding_revision: Mapped[int] = mapped_column(Integer)
    expected_g: Mapped[int] = mapped_column(Integer, default=0)
    actual_g: Mapped[int | None] = mapped_column(Integer)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), unique=True)


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (UniqueConstraint("order_id", "menu_item_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    menu_item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), index=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_zh: Mapped[str] = mapped_column(String(120))
    item_version: Mapped[int] = mapped_column(Integer)
    stock_source: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_minor: Mapped[int] = mapped_column(Integer)
    portion_g: Mapped[int | None] = mapped_column(Integer)
    reserved_g: Mapped[int] = mapped_column(Integer, default=0)
    reserved_portions: Mapped[int] = mapped_column(Integer, default=0)


class OrderHistory(Base):
    __tablename__ = "order_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(500), default="")


class FulfillmentAllocation(Base):
    __tablename__ = "fulfillment_allocations"
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    amount_g: Mapped[int] = mapped_column(Integer)


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (UniqueConstraint("run_id", "boot_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    boot_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    projected: Mapped[bool] = mapped_column(Boolean)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="ux_events_run_sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delta_g: Mapped[int | None] = mapped_column(Integer)
    net_g: Mapped[int | None] = mapped_column(Integer)
    binding_revision: Mapped[int] = mapped_column(Integer)
    observation_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    task_id: Mapped[str | None] = mapped_column(String(36))
    detail: Mapped[str] = mapped_column(String(500), default="")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    binding_revision: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20), default="pending")
    amount_g: Mapped[int] = mapped_column(Integer)
    basis_g: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(80))
    decision_reason: Mapped[str | None] = mapped_column(String(100))


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendations.id"), unique=True)
    binding_revision: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(40), default="planned")
    planned_g: Mapped[int] = mapped_column(Integer)
    actual_added_g: Mapped[int | None] = mapped_column(Integer)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reconciliation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciliation_sequence: Mapped[int | None] = mapped_column(Integer)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), unique=True)
    note: Mapped[str] = mapped_column(String(500), default="")


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (UniqueConstraint("actor_id", "context_id", "key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(String(80))
    context_id: Mapped[str] = mapped_column(String(36))
    key: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConsoleSession(Base):
    __tablename__ = "console_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FoodReference(Base):
    __tablename__ = "food_references"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    snapshot: Mapped[dict] = mapped_column(JSON)


class Meal(Base):
    __tablename__ = "meals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), unique=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    state: Mapped[str] = mapped_column(String(24), default="pairing")
    version: Mapped[int] = mapped_column(Integer, default=1)
    sample_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    plan_snapshot: Mapped[dict | None] = mapped_column(JSON)
    pair_code: Mapped[str | None] = mapped_column(String(24))
    pair_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    pair_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_request_id: Mapped[str | None] = mapped_column(String(36))
    baseline_observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"))
    prepared_reference_id: Mapped[str | None] = mapped_column(ForeignKey("food_references.id"))
    start_observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"))
    served_observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"))
    remaining_observation_id: Mapped[str | None] = mapped_column(ForeignKey("observations.id"))
    remaining_g: Mapped[int | None] = mapped_column(Integer)
    remaining_reason: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PairRequest(Base):
    __tablename__ = "pair_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meal_id: Mapped[str] = mapped_column(ForeignKey("meals.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    state: Mapped[str] = mapped_column(String(24), default="pending")
    check_code: Mapped[str] = mapped_column(String(4))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Portion(Base):
    __tablename__ = "portions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meal_id: Mapped[str] = mapped_column(ForeignKey("meals.id"), index=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("food_references.id"))
    reference_snapshot: Mapped[dict] = mapped_column(JSON)
    amount_g: Mapped[int] = mapped_column(Integer)
    start_observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"))
    end_observation_id: Mapped[str] = mapped_column(ForeignKey("observations.id"), unique=True)
    entry_source: Mapped[str] = mapped_column(String(30), default="confirmed_reference")
    version: Mapped[int] = mapped_column(Integer, default=1)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MealHistory(Base):
    __tablename__ = "meal_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meal_id: Mapped[str] = mapped_column(ForeignKey("meals.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str] = mapped_column(String(80))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(500), default="")
    previous: Mapped[dict | None] = mapped_column(JSON)
