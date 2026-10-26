from sqlalchemy import func, select

from .models import Order, OrderLine

OPEN_ORDERS = {"submitted", "accepted", "preparing", "ready"}


def reserved_grams(db, run_id):
    return (
        db.scalar(
            select(func.coalesce(func.sum(OrderLine.reserved_g), 0))
            .join(Order)
            .where(Order.run_id == run_id)
        )
        or 0
    )


def reserved_portions(db, item_id):
    return (
        db.scalar(
            select(func.coalesce(func.sum(OrderLine.reserved_portions), 0)).where(
                OrderLine.menu_item_id == item_id
            )
        )
        or 0
    )


def has_open_orders(db, run_id):
    return bool(
        db.scalar(
            select(Order.id).where(Order.run_id == run_id, Order.state.in_(OPEN_ORDERS)).limit(1)
        )
    )


def has_fulfillment_window(db, run_id):
    return bool(
        db.scalar(
            select(Order.id)
            .where(Order.run_id == run_id, Order.state == "preparing", Order.expected_g > 0)
            .limit(1)
        )
    )
