"""One-service ordering: reservation, physical fulfillment and collection are separate."""

from datetime import timedelta
import io
import re
import secrets
from typing import Annotated

from fastapi import Depends, Header, Response
import segno
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .availability import has_fulfillment_window, has_open_orders, reserved_grams, reserved_portions
from .domain import (
    DomainError,
    digest,
    event,
    event_view,
    iso,
    operation_cached,
    refresh_recommendation,
    remember,
    tasks_for,
    usable,
    utcnow,
)
from .models import (
    Event,
    FulfillmentAllocation,
    MenuItem,
    Observation,
    Order,
    OrderHistory,
    OrderLine,
    Run,
    User,
    Workspace,
    uid,
)
from .schemas import MenuItemAction, OrderAction, ServiceAction, SubmitOrder


def seed_menu(db, run):
    if run.mode != "foodservice":
        return
    if db.scalar(select(MenuItem.id).where(MenuItem.run_id == run.id).limit(1)):
        return
    db.add_all(
        [
            MenuItem(
                run_id=run.id,
                slug="chicken",
                name_en=run.food_name_en,
                name_zh=run.food_name,
                description_en="Roasted with herbs. A standard portion is 100 g.",
                description_zh="香草烤制，标准份量为100克。",
                price_minor=2400,
                stock_source="measured",
                portion_g=100,
                food_id=run.food_id,
                binding_revision=run.binding_revision,
                updated_at=utcnow(),
            ),
            MenuItem(
                run_id=run.id,
                slug="salad",
                name_en="Garden salad",
                name_zh="田园沙拉",
                description_en="A fresh side salad, portioned by the kitchen.",
                description_zh="厨房按份准备的新鲜配菜沙拉。",
                price_minor=1800,
                stock_source="manual",
                manual_stock=12,
                updated_at=utcnow(),
            ),
            MenuItem(
                run_id=run.id,
                slug="soup",
                name_en="Tomato soup",
                name_zh="番茄汤",
                description_en="A warming bowl, available by the serving.",
                description_zh="按碗供应的暖心番茄汤。",
                price_minor=1600,
                stock_source="manual",
                manual_stock=20,
                updated_at=utcnow(),
            ),
        ]
    )
    db.flush()


def lines_for(db, order):
    return list(
        db.scalars(select(OrderLine).where(OrderLine.order_id == order.id).order_by(OrderLine.id))
    )


def item_availability(db, item, run):
    reserved = reserved_portions(db, item.id)
    measured = item.stock_source == "measured"
    bound = not measured or (
        item.food_id == run.food_id and item.binding_revision == run.binding_revision
    )
    reliable = not measured or (bound and usable(run))
    grams = max(0, (run.net_g or 0) - reserved_grams(db, run.id)) if measured and reliable else None
    remaining = (
        (grams // item.portion_g if grams is not None else None)
        if measured
        else max(0, item.manual_stock - reserved)
    )
    self_service = measured and run.service_type == "buffet_self_service"
    service_open = run.mode == "foodservice" and run.state == "active" and run.clock_at < run.closes_at and not run.paused
    status = (
        "unavailable"
        if not item.enabled or not item.published or not service_open
        else "unknown"
        if not reliable
        else "out_of_stock"
        if remaining == 0
        else "low"
        if remaining <= 3
        else "available"
    )
    return {
        "available_portions": remaining,
        "available_g": grams,
        "reserved_portions": reserved,
        "status": status,
        "orderable": not self_service and status in {"available", "low"},
        "service_type": "buffet_self_service" if self_service else "staff_portioned",
        "updated_at": iso(run.observed_at if measured else item.updated_at),
    }


def item_view(db, item, run, manage=False):
    sales = (
        db.scalar(
            select(func.coalesce(func.sum(OrderLine.quantity), 0))
            .join(Order)
            .where(
                Order.run_id == run.id,
                Order.state == "collected",
                OrderLine.menu_item_id == item.id,
            )
        )
        or 0
    )
    result = {
        "id": item.id,
        "slug": item.slug,
        "name_en": item.name_en,
        "name_zh": item.name_zh,
        "description_en": item.description_en,
        "description_zh": item.description_zh,
        "allergens_en": item.allergens_en,
        "allergens_zh": item.allergens_zh,
        "price_minor": item.price_minor,
        "currency": item.currency,
        "version": item.version,
        "quote_version": item.quote_version,
        "stock_source": item.stock_source,
        "portion_g": item.portion_g,
        "data_origin": run.origin,
        "completed_portions": sales,
        **item_availability(db, item, run),
    }
    if manage:
        result.update(
            manual_stock=item.manual_stock, published=item.published, enabled=item.enabled
        )
    return result


def menu_view(db, ws, run, manage=False):
    query = select(MenuItem).where(MenuItem.run_id == run.id).order_by(MenuItem.slug)
    if not manage:
        query = query.where(MenuItem.published.is_(True))
    items = [item_view(db, item, run, manage) for item in db.scalars(query)]
    best = max((i["completed_portions"] for i in items), default=0)
    for item in items:
        item["popular"] = best > 0 and item["completed_portions"] == best
    return {
        "workspace_id": ws.id,
        "name_en": "Demo dining room",
        "name_zh": ws.name,
        "menu_code": ws.menu_code,
        "run_id": run.id,
        "data_origin": run.origin,
        "service_type": run.service_type,
        "service_version": run.service_version,
        "service_ends_at": iso(run.closes_at),
        "service_open": run.mode == "foodservice" and run.state == "active" and not run.paused and run.clock_at < run.closes_at,
        "popularity_window": "current_service_collected_portions",
        "snapshot_version": run.snapshot_version,
        "items": items,
    }


def eligible_fulfillment_events(db, order, run):
    if (
        order.state != "preparing"
        or not order.expected_g
        or order.preparation_sequence is None
        or order.binding_revision != run.binding_revision
    ):
        return []
    used = select(FulfillmentAllocation.event_id)
    return list(
        db.scalars(
            select(Event)
            .join(Observation, Event.observation_id == Observation.id)
            .where(
                Event.run_id == run.id,
                Event.kind == "food_removed",
                Event.delta_g < 0,
                Event.binding_revision == order.binding_revision,
                Observation.sequence > order.preparation_sequence,
                Observation.projected.is_(True),
                Event.id.not_in(used),
            )
            .order_by(Event.sequence.desc())
        )
    )


def order_view(db, order, personal=False):
    run = db.get(Run, order.run_id)
    owner = db.get(User, order.assignee_id) if order.assignee_id else None
    lines = lines_for(db, order)
    history = db.scalars(
        select(OrderHistory)
        .where(OrderHistory.order_id == order.id)
        .order_by(OrderHistory.sequence)
    )
    return {
        "id": order.id,
        "number": f"{order.number:03d}",
        "run_id": order.run_id,
        "workspace_id": order.workspace_id,
        "workspace_name_en": "Demo dining room",
        "workspace_name_zh": db.get(Workspace, order.workspace_id).name,
        "state": order.state,
        "version": order.version,
        "data_origin": run.origin,
        "total_minor": order.total_minor,
        "currency": order.currency,
        "created_at": iso(order.created_at),
        "updated_at": iso(order.updated_at),
        "cancellation": order.cancellation,
        "note": order.note,
        "assignee_id": order.assignee_id,
        "assignee_name": owner.name if owner else None,
        "expected_g": order.expected_g,
        "actual_g": order.actual_g,
        "pickup_code": order.pickup_code if personal and order.state == "ready" else None,
        "payment_status": "pay_at_counter_not_verified",
        "reserved_g": sum(line.reserved_g for line in lines),
        "lines": [
            {
                "id": line.id,
                "menu_item_id": line.menu_item_id,
                "name_en": line.name_en,
                "name_zh": line.name_zh,
                "quantity": line.quantity,
                "unit_price_minor": line.unit_price_minor,
                "portion_g": line.portion_g,
                "stock_source": line.stock_source,
            }
            for line in lines
        ],
        "history": [
            {"id": e.id, "action": e.action, "at": iso(e.at), "note": e.note} for e in history
        ],
        "eligible_events": []
        if personal
        else [event_view(e, run.origin) for e in eligible_fulfillment_events(db, order, run)],
    }


def record_change(db, order, run, action, actor, note=""):
    order.updated_at = utcnow()
    db.add(
        OrderHistory(
            order_id=order.id,
            sequence=order.version,
            action=action,
            actor_id=actor.id,
            at=order.updated_at,
            note=note,
        )
    )
    db.execute(
        update(User)
        .where(User.id == order.owner_id)
        .values(activity_version=User.activity_version + 1)
    )
    event(db, run, "order_" + action, actor=actor.id, detail=order.id)
    db.flush()
    refresh_recommendation(db, run)


def validate_sale(db, item, run, quantity, accepting=False):
    available = item_availability(db, item, run)
    if not available["orderable"]:
        raise DomainError("ITEM_NOT_ORDERABLE")
    if accepting and quantity > available["available_portions"]:
        raise DomainError("INSUFFICIENT_SUPPLY")
    if not accepting and quantity > available["available_portions"]:
        raise DomainError("INSUFFICIENT_SUPPLY")


def submit_order(db, run, actor, data):
    if run.mode != "foodservice":
        raise DomainError("ORDERING_UNAVAILABLE")
    if run.id != data.run_id:
        raise DomainError("SESSION_CHANGED")
    if len({line.menu_item_id for line in data.lines}) != len(data.lines):
        raise DomainError("DUPLICATE_MENU_ITEM", 422)
    items, total, expected = [], 0, 0
    for line in data.lines:
        item = db.get(MenuItem, line.menu_item_id)
        if not item or item.run_id != run.id:
            raise DomainError("MENU_CHANGED")
        if item.quote_version != line.item_version:
            raise DomainError("MENU_CHANGED")
        validate_sale(db, item, run, line.quantity)
        total += item.price_minor * line.quantity
        expected += (item.portion_g or 0) * line.quantity if item.stock_source == "measured" else 0
        items.append((item, line))
    run.order_counter += 1
    order = Order(
        id=uid(),
        run_id=run.id,
        workspace_id=run.workspace_id,
        owner_id=actor.id,
        number=run.order_counter,
        state="submitted",
        version=1,
        total_minor=total,
        binding_revision=run.binding_revision,
        expected_g=expected,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(order)
    db.flush()
    for item, line in items:
        db.add(
            OrderLine(
                order_id=order.id,
                menu_item_id=item.id,
                name_en=item.name_en,
                name_zh=item.name_zh,
                item_version=item.quote_version,
                stock_source=item.stock_source,
                quantity=line.quantity,
                unit_price_minor=item.price_minor,
                portion_g=item.portion_g,
            )
        )
    record_change(db, order, run, "submitted", actor)
    return order


def act_order(db, order, run, actor, role, data):
    if order.version != data.expected_version:
        raise DomainError("VERSION_CONFLICT")
    personal = role == "personal"
    if personal:
        if order.owner_id != actor.id:
            raise DomainError("NOT_FOUND", 404)
        if data.action not in {"cancel", "request_cancel"}:
            raise DomainError("FORBIDDEN", 403)
    elif role not in {"staff", "manager"}:
        raise DomainError("FORBIDDEN", 403)
    if not personal and order.assignee_id not in {None, actor.id} and role != "manager":
        raise DomainError("ASSIGNED_TO_ANOTHER_STAFF", 403)
    lines = lines_for(db, order)
    action, old = data.action, order.state
    if (
        action in {"reject", "request_cancel", "approve_cancel", "deny_cancel"}
        and not data.note.strip()
    ):
        raise DomainError("REASON_REQUIRED", 422)
    if action == "accept" and old == "submitted":
        if order.binding_revision != run.binding_revision and order.expected_g:
            raise DomainError("BINDING_CHANGED")
        for line in lines:
            item = db.get(MenuItem, line.menu_item_id)
            validate_sale(db, item, run, line.quantity, accepting=True)
        # All rows have been checked while holding the run lock. Reserve atomically.
        for line in lines:
            if line.stock_source == "measured":
                line.reserved_g = line.quantity * line.portion_g
            else:
                line.reserved_portions = line.quantity
        order.state = "accepted"
    elif action == "reject" and old == "submitted" and not personal:
        order.state = "rejected"
    elif action == "cancel" and old == "submitted" and personal:
        order.state = "cancelled"
    elif (
        action == "request_cancel"
        and old == "accepted"
        and personal
        and order.cancellation != "pending"
    ):
        order.cancellation = "pending"
    elif (
        action in {"approve_cancel", "deny_cancel"}
        and old == "accepted"
        and order.cancellation == "pending"
        and not personal
    ):
        order.cancellation = "approved" if action == "approve_cancel" else "denied"
        if action == "approve_cancel":
            order.state = "cancelled"
            for line in lines:
                line.reserved_g = line.reserved_portions = 0
    elif action == "begin_preparation" and old == "accepted" and not personal:
        if order.cancellation == "pending":
            raise DomainError("CANCELLATION_PENDING")
        if order.expected_g:
            if order.binding_revision != run.binding_revision:
                raise DomainError("BINDING_CHANGED")
            if not usable(run) or (run.net_g or 0) < order.expected_g:
                raise DomainError("DATA_NOT_READY")
            if has_fulfillment_window(db, run.id) or any(
                t.state in {"awaiting_reconciliation", "needs_review"} for t in tasks_for(db, run)
            ):
                raise DomainError("FULFILLMENT_WINDOW_BUSY")
        order.assignee_id = actor.id
        order.preparation_sequence = run.last_sequence
        order.state = "preparing"
    elif action == "confirm_fulfillment" and old == "preparing" and not personal:
        if order.expected_g:
            if not usable(run):
                raise DomainError("DATA_NOT_READY")
            events = eligible_fulfillment_events(db, order, run)
            requested = data.physical_event_ids or (
                [data.physical_event_id] if data.physical_event_id else []
            )
            selected = [e for e in events if e.id in requested]
            if (
                not selected
                or len(selected) != len(requested)
                or len(set(requested)) != len(requested)
            ):
                raise DomainError("NO_VALID_FULFILLMENT_EVENT")
            actual = sum(-e.delta_g for e in selected)
            if actual != order.expected_g:
                if not data.allow_variance or role != "manager" or not data.note.strip():
                    raise DomainError("FULFILLMENT_AMOUNT_MISMATCH")
            order.event_id, order.actual_g = selected[0].id, actual
            for e in selected:
                db.add(FulfillmentAllocation(event_id=e.id, order_id=order.id, amount_g=-e.delta_g))
        for line in lines:
            if line.stock_source == "manual":
                item = db.get(MenuItem, line.menu_item_id)
                if item.manual_stock < line.quantity:
                    raise DomainError("INSUFFICIENT_SUPPLY")
                item.manual_stock -= line.quantity
                item.version += 1
                item.updated_at = utcnow()
            line.reserved_g = line.reserved_portions = 0
        order.state = "ready"
    elif action == "collect" and old == "ready" and not personal:
        if order.pickup_blocked_until and order.pickup_blocked_until > utcnow():
            raise DomainError("TRY_LATER", 429)
        if order.pickup_blocked_until:
            order.pickup_failures = 0
            order.pickup_blocked_until = None
        if not data.pickup_code or not secrets.compare_digest(data.pickup_code, order.pickup_code):
            order.pickup_failures += 1
            if order.pickup_failures >= 5:
                order.pickup_blocked_until = utcnow() + timedelta(seconds=60)
            raise DomainError("PICKUP_CODE_INVALID", 422)
        order.state = "collected"
    else:
        raise DomainError("INVALID_TRANSITION")
    order.note = data.note
    order.version += 1
    record_change(db, order, run, action, actor, data.note)


def register_order_routes(app, db_dependency, user_dependency, authorize, key_for):
    DB = Annotated[Session, Depends(db_dependency)]
    Actor = Annotated[User, Depends(user_dependency)]
    Context = Annotated[str | None, Header(alias="X-Context-ID")]
    Key = Annotated[str | None, Header(alias="Idempotency-Key")]

    def current(db, workspace_id, lock=False):
        ws = (
            db.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
            if lock
            else db.get(Workspace, workspace_id)
        )
        if not ws or not ws.active_run_id:
            raise DomainError("NO_ACTIVE_RUN", 404)
        query = select(Run).where(Run.id == ws.active_run_id)
        run = db.scalar(query.with_for_update() if lock else query)
        return ws, run

    def personal_scope(context):
        if context != "personal":
            raise DomainError("PERSONAL_CONTEXT_REQUIRED", 403)

    @app.get("/v1/menus/{code}", tags=["Ordering"])
    def customer_menu(code: str, actor: Actor, db: DB, x_context_id: Context = None):
        personal_scope(x_context_id)
        if not re.fullmatch(r"[A-Z0-9-]{6,32}", code):
            raise DomainError("INVALID_MENU_CODE", 404)
        ws = db.scalar(select(Workspace).where(Workspace.menu_code == code))
        if not ws:
            raise DomainError("INVALID_MENU_CODE", 404)
        ws, run = current(db, ws.id)
        return menu_view(db, ws, run)

    @app.get("/v1/me/orders", tags=["Ordering"])
    def own_orders(actor: Actor, db: DB, x_context_id: Context = None):
        personal_scope(x_context_id)
        rows = db.scalars(
            select(Order)
            .where(Order.owner_id == actor.id)
            .order_by(Order.created_at.desc(), Order.id)
            .limit(100)
        )
        return {"items": [order_view(db, o, True) for o in rows]}

    @app.post("/v1/orders", tags=["Ordering"])
    def place_order(
        data: SubmitOrder,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        idempotency_key: Key = None,
    ):
        personal_scope(x_context_id)
        referenced = db.get(Run, data.run_id)
        if not referenced:
            raise DomainError("NOT_FOUND", 404)
        ws, run = current(db, referenced.workspace_id, True)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"path": "submit_order", "body": data.model_dump()})
        cached = operation_cached(db, actor.id, "personal", key, fingerprint)
        if cached:
            return cached
        order = submit_order(db, run, actor, data)
        result = remember(
            db,
            actor.id,
            "personal",
            key,
            fingerprint,
            {"order_id": order.id, "state": order.state, "resource_version": order.version},
        )
        db.commit()
        return result

    @app.get("/v1/orders/{order_id}", tags=["Ordering"])
    def order_detail(order_id: str, actor: Actor, db: DB, x_context_id: Context = None):
        order = db.get(Order, order_id)
        if not order or (x_context_id == "personal" and order.owner_id != actor.id):
            raise DomainError("NOT_FOUND", 404)
        if x_context_id != "personal":
            authorize(db, actor, order.workspace_id, x_context_id)
        return order_view(db, order, x_context_id == "personal")

    @app.post("/v1/orders/{order_id}/actions", tags=["Ordering"])
    def order_action(
        order_id: str,
        data: OrderAction,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        idempotency_key: Key = None,
    ):
        order = db.get(Order, order_id)
        if not order or (x_context_id == "personal" and order.owner_id != actor.id):
            raise DomainError("NOT_FOUND", 404)
        role = (
            "personal"
            if x_context_id == "personal"
            else authorize(db, actor, order.workspace_id, x_context_id, write=True)
        )
        _, run = current(db, order.workspace_id, True)
        db.refresh(order)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"order": order_id, "body": data.model_dump()})
        cached = operation_cached(db, actor.id, x_context_id, key, fingerprint)
        if cached:
            return cached
        if order.run_id != run.id:
            raise DomainError("SESSION_CHANGED")
        try:
            act_order(db, order, run, actor, role, data)
        except DomainError as exc:
            if exc.code == "PICKUP_CODE_INVALID":
                db.commit()  # Persist only the failed-code counter, never a fulfilled order.
            raise
        result = remember(
            db,
            actor.id,
            x_context_id,
            key,
            fingerprint,
            {"order_id": order.id, "state": order.state, "resource_version": order.version},
        )
        db.commit()
        return result

    @app.get("/v1/workspaces/{workspace_id}/orders", tags=["Ordering"])
    def kitchen_orders(workspace_id: str, actor: Actor, db: DB, x_context_id: Context = None):
        authorize(db, actor, workspace_id, x_context_id)
        _, run = current(db, workspace_id)
        orders = db.scalars(select(Order).where(Order.run_id == run.id).order_by(Order.number))
        return {"items": [order_view(db, order) for order in orders]}

    @app.get("/v1/workspaces/{workspace_id}/menu", tags=["Ordering"])
    def managed_menu(workspace_id: str, actor: Actor, db: DB, x_context_id: Context = None):
        authorize(db, actor, workspace_id, x_context_id)
        ws, run = current(db, workspace_id)
        return menu_view(db, ws, run, True)

    @app.get("/v1/workspaces/{workspace_id}/menu-qr.svg", tags=["Ordering"])
    def menu_qr(workspace_id: str, actor: Actor, db: DB, x_context_id: Context = None):
        authorize(db, actor, workspace_id, x_context_id)
        ws, _ = current(db, workspace_id)
        output = io.BytesIO()
        segno.make_qr("senplate://menu/" + ws.menu_code, error="m").save(
            output, kind="svg", scale=6, dark="#163F35", light="white", border=4
        )
        return Response(output.getvalue(), media_type="image/svg+xml")

    @app.post("/v1/menu-items/{item_id}/actions", tags=["Ordering"])
    def edit_menu_item(
        item_id: str,
        data: MenuItemAction,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        idempotency_key: Key = None,
    ):
        item = db.get(MenuItem, item_id)
        if not item:
            raise DomainError("NOT_FOUND", 404)
        old_run = db.get(Run, item.run_id)
        if authorize(db, actor, old_run.workspace_id, x_context_id, write=True) != "manager":
            raise DomainError("MANAGER_REQUIRED", 403)
        _, run = current(db, old_run.workspace_id, True)
        db.refresh(item)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"item": item_id, "body": data.model_dump()})
        cached = operation_cached(db, actor.id, x_context_id, key, fingerprint)
        if cached:
            return cached
        if run.id != item.run_id:
            raise DomainError("SESSION_CHANGED")
        if item.version != data.expected_version:
            raise DomainError("VERSION_CONFLICT")
        if not data.name_en.strip() or not data.name_zh.strip():
            raise DomainError("VALIDATION_FAILED", 422)
        if data.manual_stock < reserved_portions(db, item.id):
            raise DomainError("STOCK_BELOW_RESERVATIONS")
        quote_changed = False
        for field in [
            "name_en",
            "name_zh",
            "description_en",
            "description_zh",
            "allergens_en",
            "allergens_zh",
            "price_minor",
            "published",
            "enabled",
        ]:
            quote_changed = quote_changed or getattr(item, field) != getattr(data, field)
            setattr(item, field, getattr(data, field))
        if quote_changed:
            item.quote_version += 1
        if item.stock_source == "manual":
            item.manual_stock = data.manual_stock
        item.updated_at = utcnow()
        item.version += 1
        event(db, run, "menu_updated", actor=actor.id, detail=item.id)
        result = remember(
            db,
            actor.id,
            x_context_id,
            key,
            fingerprint,
            {"menu_item_id": item.id, "resource_version": item.version},
        )
        db.commit()
        return result

    @app.post("/v1/workspaces/{workspace_id}/service", tags=["Ordering"])
    def change_service(
        workspace_id: str,
        data: ServiceAction,
        actor: Actor,
        db: DB,
        x_context_id: Context = None,
        idempotency_key: Key = None,
    ):
        if authorize(db, actor, workspace_id, x_context_id, write=True) != "manager":
            raise DomainError("MANAGER_REQUIRED", 403)
        _, run = current(db, workspace_id, True)
        key = key_for(idempotency_key, data.client_operation_id)
        fingerprint = digest({"service": workspace_id, "body": data.model_dump()})
        cached = operation_cached(db, actor.id, x_context_id, key, fingerprint)
        if cached:
            return cached
        if run.service_version != data.expected_version:
            raise DomainError("VERSION_CONFLICT")
        if run.mode != "foodservice":
            raise DomainError("MEAL_MODE_ACTIVE")
        if has_open_orders(db, run.id) or any(
            t.state in {"awaiting_reconciliation", "needs_review"} for t in tasks_for(db, run)
        ):
            raise DomainError("OPEN_ORDERS_OR_MEASUREMENT")
        run.service_type = data.service_type
        run.service_version += 1
        event(db, run, "service_changed", actor=actor.id, detail=data.service_type)
        result = remember(
            db,
            actor.id,
            x_context_id,
            key,
            fingerprint,
            {"run_id": run.id, "service_type": run.service_type},
        )
        db.commit()
        return result
