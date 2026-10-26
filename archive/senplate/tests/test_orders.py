from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from senplate_api.domain import utcnow
from senplate_api.models import FulfillmentAllocation, Membership, Order, Workspace
from test_api import api as api, get_state, step


def personal(a, actor="personal"):
    return {**a["headers"][actor], "X-Context-ID": "personal"}


def post(a, path, body, headers=None, key=None):
    key = key or str(uuid4())
    return a["client"].post(
        path,
        headers={**(headers or a["headers"]["manager"]), "Idempotency-Key": key},
        json={"client_operation_id": key, **body},
    )


def menu(a):
    r = a["client"].get(f"/v1/workspaces/{a['workspace']}/menu", headers=a["headers"]["manager"])
    assert r.status_code == 200, r.text
    return r.json()


def public_menu(a):
    return a["client"].get("/v1/menus/" + menu(a)["menu_code"], headers=personal(a))


def counter_service(a):
    r = post(
        a,
        f"/v1/workspaces/{a['workspace']}/service",
        {"service_type": "staff_portioned", "expected_version": menu(a)["service_version"]},
    )
    assert r.status_code == 200, r.text


def submit(a, slug="chicken", quantity=1, actor="personal", key=None):
    item = next(x for x in menu(a)["items"] if x["slug"] == slug)
    return post(
        a,
        "/v1/orders",
        {
            "run_id": a["run"]["run_id"],
            "lines": [
                {
                    "menu_item_id": item["id"],
                    "item_version": item["quote_version"],
                    "quantity": quantity,
                }
            ],
        },
        personal(a, actor),
        key,
    )


def detail(a, order_id, actor="manager", own=False):
    r = a["client"].get(
        "/v1/orders/" + order_id, headers=personal(a, actor) if own else a["headers"][actor]
    )
    assert r.status_code == 200, r.text
    return r.json()


def action(a, order_id, action_name, actor="manager", own=False, version=None, key=None, **extra):
    current = detail(a, order_id, actor, own)
    return post(
        a,
        f"/v1/orders/{order_id}/actions",
        {"expected_version": version or current["version"], "action": action_name, **extra},
        personal(a, actor) if own else a["headers"][actor],
        key,
    )


def edit(a, item, **changes):
    fields = [
        "name_en",
        "name_zh",
        "description_en",
        "description_zh",
        "allergens_en",
        "allergens_zh",
        "price_minor",
        "published",
        "enabled",
        "manual_stock",
    ]
    return post(
        a,
        f"/v1/menu-items/{item['id']}/actions",
        {"expected_version": item["version"], **{f: item[f] for f in fields}, **changes},
    )


def accepted(a, slug="chicken", quantity=1, actor="personal"):
    r = submit(a, slug, quantity, actor)
    assert r.status_code == 200, r.text
    order_id = r.json()["order_id"]
    r = action(a, order_id, "accept")
    assert r.status_code == 200, r.text
    return order_id


def test_measured_reservation_and_fulfillment_never_double_decrement(api):
    a = api
    counter_service(a)
    step(a, "add", 500)  # S=2000
    first = accepted(a, quantity=3)
    accepted(a, quantity=5, actor="staff")
    state = get_state(a)
    assert (state["net_g"], state["reserved_g"], state["available_to_promise_g"]) == (
        2000,
        800,
        1200,
    )
    assert detail(a, first)["total_minor"] == 7200
    assert action(a, first, "begin_preparation").status_code == 200
    assert get_state(a)["suggestion_reason"] == "ORDER_RECONCILIATION_REQUIRED"
    step(a, "consume", 100)
    step(a, "consume", 200)
    state = get_state(a)
    assert (state["net_g"], state["reserved_g"], state["available_to_promise_g"]) == (
        1700,
        800,
        900,
    )
    event_ids = [e["id"] for e in detail(a, first)["eligible_events"]]
    assert len(event_ids) == 2
    key = str(uuid4())
    old_version = detail(a, first)["version"]
    result = action(
        a, first, "confirm_fulfillment", physical_event_ids=event_ids, version=old_version, key=key
    )
    assert result.status_code == 200, result.text
    assert (
        action(
            a,
            first,
            "confirm_fulfillment",
            physical_event_ids=event_ids,
            version=old_version,
            key=key,
        ).json()
        == result.json()
    )
    state = get_state(a)
    assert (state["net_g"], state["reserved_g"], state["available_to_promise_g"]) == (
        1700,
        500,
        1200,
    )
    assert detail(a, first)["actual_g"] == 300
    assert detail(a, first)["pickup_code"] is None
    code = detail(a, first, "personal", True)["pickup_code"]
    assert action(a, first, "collect", pickup_code=code).status_code == 200
    state = get_state(a)
    assert (state["net_g"], state["reserved_g"], state["available_to_promise_g"]) == (
        1700,
        500,
        1200,
    )
    item = next(x for x in public_menu(a).json()["items"] if x["slug"] == "chicken")
    assert item["completed_portions"] == 3 and item["popular"]
    with Session(a["engine"]) as db:
        assert len(list(db.scalars(select(FulfillmentAllocation)))) == 2


def test_concurrent_accept_cannot_oversell_measured_supply(api):
    a = api
    counter_service(a)
    orders = [
        submit(a, quantity=10, actor=actor).json()["order_id"] for actor in ["personal", "staff"]
    ]
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda order: action(a, order, "accept"), orders))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert get_state(a)["reserved_g"] == 1000
    assert get_state(a)["net_g"] == 1500


def test_manual_stock_accept_serve_collect_once(api):
    a = api
    order = accepted(a, "salad", 3)
    item = next(x for x in menu(a)["items"] if x["slug"] == "salad")
    assert (item["manual_stock"], item["reserved_portions"], item["available_portions"]) == (
        12,
        3,
        9,
    )
    assert action(a, order, "begin_preparation").status_code == 200
    before = detail(a, order)
    key = str(uuid4())
    assert (
        action(a, order, "confirm_fulfillment", key=key, version=before["version"]).status_code
        == 200
    )
    assert (
        action(a, order, "confirm_fulfillment", key=key, version=before["version"]).status_code
        == 200
    )
    item = next(x for x in menu(a)["items"] if x["slug"] == "salad")
    assert (item["manual_stock"], item["reserved_portions"], item["available_portions"]) == (
        9,
        0,
        9,
    )
    assert get_state(a)["net_g"] == 1500
    code = detail(a, order, "personal", True)["pickup_code"]
    assert action(a, order, "collect", pickup_code=code).status_code == 200
    assert next(x for x in menu(a)["items"] if x["slug"] == "salad")["manual_stock"] == 9


def test_concurrent_manual_stock_orders(api):
    a = api
    orders = [
        submit(a, "salad", 8, actor=actor).json()["order_id"] for actor in ["personal", "staff"]
    ]
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda order: action(a, order, "accept"), orders))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert next(x for x in menu(a)["items"] if x["slug"] == "salad")["reserved_portions"] == 8


def test_customer_cancel_and_accepted_cancel_request(api):
    a = api
    counter_service(a)
    order = submit(a, quantity=3).json()["order_id"]
    assert get_state(a)["reserved_g"] == 0
    assert action(a, order, "cancel", actor="personal", own=True).status_code == 200
    order = accepted(a, quantity=3)
    assert action(a, order, "cancel", actor="personal", own=True).status_code == 409
    assert (
        action(
            a, order, "request_cancel", actor="personal", own=True, note="Changed plans"
        ).status_code
        == 200
    )
    assert detail(a, order)["state"] == "accepted"
    assert get_state(a)["reserved_g"] == 300
    assert action(a, order, "begin_preparation").json()["error"]["code"] == "CANCELLATION_PENDING"
    assert action(a, order, "approve_cancel", note="Not started").status_code == 200
    assert get_state(a)["reserved_g"] == 0
    assert (
        next(x for x in public_menu(a).json()["items"] if x["slug"] == "chicken")[
            "completed_portions"
        ]
        == 0
    )


def test_cancel_request_racing_with_preparation(api):
    a = api
    order = accepted(a, "soup", 2)
    version = detail(a, order)["version"]
    with ThreadPoolExecutor(2) as pool:
        one = pool.submit(
            action,
            a,
            order,
            "request_cancel",
            actor="personal",
            own=True,
            version=version,
            note="Cancel please",
        )
        two = pool.submit(action, a, order, "begin_preparation", version=version)
        results = [one.result(), two.result()]
    assert sorted(r.status_code for r in results) == [200, 409]
    current = detail(a, order)
    assert (current["state"], current["cancellation"]) in [
        ("accepted", "pending"),
        ("preparing", None),
    ]


def test_menu_price_versions_and_historical_order_price(api):
    a = api
    item = next(x for x in menu(a)["items"] if x["slug"] == "soup")
    body = {
        "run_id": a["run"]["run_id"],
        "lines": [
            {"menu_item_id": item["id"], "item_version": item["quote_version"], "quantity": 2}
        ],
    }
    old_order = post(a, "/v1/orders", body, personal(a)).json()["order_id"]
    assert edit(a, item, price_minor=2000).status_code == 200
    assert post(a, "/v1/orders", body, personal(a)).json()["error"]["code"] == "MENU_CHANGED"
    assert detail(a, old_order)["total_minor"] == 3200
    assert action(a, old_order, "accept").status_code == 200
    assert detail(a, old_order)["total_minor"] == 3200


def test_unpublished_and_self_service_items_cannot_be_ordered(api):
    a = api
    assert submit(a).json()["error"]["code"] == "ITEM_NOT_ORDERABLE"
    item = next(x for x in menu(a)["items"] if x["slug"] == "salad")
    assert edit(a, item, published=False).status_code == 200
    assert item["id"] not in [x["id"] for x in public_menu(a).json()["items"]]
    hidden = post(
        a,
        "/v1/orders",
        {
            "run_id": a["run"]["run_id"],
            "lines": [
                {
                    "menu_item_id": item["id"],
                    "item_version": item["quote_version"] + 1,
                    "quantity": 1,
                }
            ],
        },
        personal(a),
    )
    assert hidden.status_code == 409


def test_unknown_measurement_stops_new_reservations(api):
    a = api
    counter_service(a)
    order = submit(a).json()["order_id"]
    step(a, "advance", seconds=6)
    assert action(a, order, "accept").status_code == 409
    item = next(x for x in public_menu(a).json()["items"] if x["slug"] == "chicken")
    assert (
        item["status"] == "unknown" and item["available_portions"] is None and not item["orderable"]
    )
    assert get_state(a)["reserved_g"] == 0


def test_order_scope_and_personal_operation_recovery(api):
    a = api
    key = str(uuid4())
    result = submit(a, "soup", key=key)
    assert result.status_code == 200
    assert submit(a, "soup", key=key).json() == result.json()
    assert submit(a, "soup", quantity=2, key=key).status_code == 409
    oid = result.json()["order_id"]
    assert a["client"].get("/v1/orders/" + oid, headers=personal(a, "staff")).status_code == 404
    assert a["client"].get("/v1/orders/" + oid, headers=a["headers"]["personal"]).status_code == 403
    assert action(a, oid, "accept", actor="personal", own=True).status_code == 403
    assert (
        post(
            a,
            "/v1/orders/" + oid + "/actions",
            {"action": "accept", "expected_version": 1},
            a["headers"]["viewer"],
        ).status_code
        == 403
    )
    recovery = a["client"].get("/v1/operations/" + key, headers=personal(a))
    assert recovery.json() == result.json()
    assert a["client"].get("/v1/operations/" + key, headers=personal(a, "staff")).status_code == 404
    with Session(a["engine"]) as db:
        db.get(Membership, (a["ids"]["manager"], a["workspace"])).active = False
        db.commit()
    assert a["client"].get("/v1/orders/" + oid, headers=a["headers"]["manager"]).status_code == 403


def test_single_pan_window_and_old_event_rejection(api):
    a = api
    counter_service(a)
    step(a, "consume", 100)
    old = next(e for e in get_state(a)["events"] if e["kind"] == "food_removed")
    first = accepted(a, quantity=1)
    second = accepted(a, quantity=1, actor="staff")
    assert action(a, first, "begin_preparation").status_code == 200
    assert (
        action(a, second, "begin_preparation").json()["error"]["code"] == "FULFILLMENT_WINDOW_BUSY"
    )
    assert action(a, first, "confirm_fulfillment", physical_event_id=old["id"]).status_code == 409
    step(a, "consume", 100)
    eligible = detail(a, first)["eligible_events"]
    assert (
        action(
            a,
            first,
            "confirm_fulfillment",
            physical_event_ids=[eligible[0]["id"], eligible[0]["id"]],
        ).status_code
        == 409
    )
    assert (
        action(a, first, "confirm_fulfillment", physical_event_id=eligible[0]["id"]).status_code
        == 200
    )
    assert action(a, second, "begin_preparation").status_code == 200
    assert (
        action(a, second, "confirm_fulfillment", physical_event_id=eligible[0]["id"]).status_code
        == 409
    )


def test_manager_explains_weight_variance(api):
    a = api
    counter_service(a)
    order = accepted(a, quantity=3)
    assert action(a, order, "begin_preparation", actor="staff").status_code == 200
    step(a, "consume", 290)
    measured = detail(a, order)["eligible_events"][0]["id"]
    assert (
        action(
            a, order, "confirm_fulfillment", actor="staff", physical_event_id=measured
        ).status_code
        == 409
    )
    assert (
        action(
            a,
            order,
            "confirm_fulfillment",
            actor="staff",
            physical_event_id=measured,
            allow_variance=True,
            note="Observed",
        ).status_code
        == 409
    )
    assert (
        action(
            a,
            order,
            "confirm_fulfillment",
            physical_event_id=measured,
            allow_variance=True,
            note="Checked portion variance",
        ).status_code
        == 200
    )
    assert detail(a, order)["actual_g"] == 290 and get_state(a)["net_g"] == 1210


def test_unresolved_orders_block_service_and_run_replacement(api):
    a = api
    order = accepted(a, "salad")
    assert (
        post(
            a,
            f"/v1/workspaces/{a['workspace']}/service",
            {"service_type": "staff_portioned", "expected_version": menu(a)["service_version"]},
        ).status_code
        == 409
    )
    key = str(uuid4())
    r = a["client"].post(
        "/v1/dev/runs",
        headers={**a["machine"], "Idempotency-Key": key},
        json={"workspace_id": a["workspace"], "client_operation_id": key},
    )
    assert r.json()["error"]["code"] == "OPEN_ORDERS_OR_MEASUREMENT"
    key = str(uuid4())
    r = a["client"].post(
        f"/v1/dev/runs/{a['run']['run_id']}/actions",
        headers={**a["machine"], "Idempotency-Key": key},
        json={"action": "rebind", "client_operation_id": key},
    )
    assert r.status_code == 409
    assert detail(a, order)["state"] == "accepted"


def test_pickup_code_and_attempt_limit(api):
    a = api
    order = accepted(a, "soup")
    action(a, order, "begin_preparation")
    action(a, order, "confirm_fulfillment")
    code = detail(a, order, "personal", True)["pickup_code"]
    wrong = "000000" if code != "000000" else "111111"
    assert action(a, order, "collect", pickup_code="１２３４５６").status_code == 422
    for _ in range(5):
        assert action(a, order, "collect", pickup_code=wrong).status_code == 422
    assert action(a, order, "collect", pickup_code=code).status_code == 429
    with Session(a["engine"]) as db:
        db.get(Order, order).pickup_blocked_until = utcnow() - timedelta(seconds=1)
        db.commit()
    assert action(a, order, "collect", pickup_code=code).status_code == 200
    assert detail(a, order, "personal", True)["pickup_code"] is None


def test_qr_scope_and_personal_websocket_refresh(api):
    a = api
    qr = a["client"].get(
        f"/v1/workspaces/{a['workspace']}/menu-qr.svg", headers=a["headers"]["manager"]
    )
    assert (
        qr.status_code == 200
        and "<svg" in qr.text
        and "image/svg+xml" in qr.headers["content-type"]
    )
    assert (
        a["client"]
        .get(f"/v1/workspaces/{a['workspace']}/menu-qr.svg", headers=personal(a))
        .status_code
        == 403
    )
    assert a["client"].get("/v1/menus/NOT-A-MENU", headers=personal(a)).status_code == 404
    with a["client"].websocket_connect("/v1/events?context_id=personal", headers=personal(a)) as ws:
        assert ws.receive_json()["type"] == "state.changed"
        submit(a, "soup")
        assert ws.receive_json()["type"] == "state.changed"
    with Session(a["engine"]) as db:
        other = db.get(Workspace, a["other"])
        other_code = other.menu_code
    assert a["client"].get("/v1/menus/" + other_code, headers=personal(a)).status_code == 404


def test_stock_updates_do_not_stale_customer_quote_or_restore_old_stock(api):
    a = api
    original = next(x for x in menu(a)["items"] if x["slug"] == "salad")
    order = accepted(a, "salad", 2)
    assert action(a, order, "begin_preparation").status_code == 200
    assert action(a, order, "confirm_fulfillment").status_code == 200
    current = next(x for x in menu(a)["items"] if x["slug"] == "salad")
    assert current["manual_stock"] == 10
    assert current["version"] > original["version"]
    assert current["quote_version"] == original["quote_version"]
    assert edit(a, original, price_minor=2000).json()["error"]["code"] == "VERSION_CONFLICT"
    assert next(x for x in menu(a)["items"] if x["slug"] == "salad")["manual_stock"] == 10
    assert submit(a, "salad", 1).status_code == 200


def test_service_changes_require_the_config_version(api):
    a = api
    version = menu(a)["service_version"]
    counter_service(a)
    result = post(
        a,
        f"/v1/workspaces/{a['workspace']}/service",
        {"expected_version": version, "service_type": "buffet_self_service"},
    )
    assert result.json()["error"]["code"] == "VERSION_CONFLICT"


def test_order_payload_cannot_override_price_or_duplicate_lines(api):
    a = api
    item = next(x for x in menu(a)["items"] if x["slug"] == "soup")
    line = {"menu_item_id": item["id"], "item_version": item["quote_version"], "quantity": 1}
    body = {"run_id": a["run"]["run_id"], "lines": [line]}
    assert post(a, "/v1/orders", {**body, "total_minor": 1}, personal(a)).status_code == 422
    assert post(a, "/v1/orders", {**body, "lines": [line, line]}, personal(a)).status_code == 422
    assert submit(a, "soup", 21).status_code == 422
    assert get_state(a)["net_g"] == 1500
