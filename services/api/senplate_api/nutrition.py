"""Versioned reference conversion; no chemical measurement or intake inference."""

from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

from sqlalchemy import select

from .domain import digest
from .models import FoodReference

NUTRIENTS = ("energy_kcal", "protein_g", "carbohydrate_g", "fat_g", "fibre_g")
DEMO_PLAN = {
    "id": "demo-portion-plan-v1",
    "version": 1,
    "review_status": "illustrative_unreviewed",
    "name_en": "Demonstration portion plan",
    "name_zh": "示范份量计划",
    "target_g": {"grains": 200, "protein_foods": 100, "vegetables": 150},
    "scope_en": "For this prototype sample only. A school must review its own meal plan.",
    "scope_zh": "仅用于本原型样本，学校实际配餐计划需另行审核。",
}


def seed_references(db):
    records = json.loads((Path(__file__).parent / "data/food_references.json").read_text())
    for record in records:
        version = digest(record)
        if not db.get(FoodReference, version):
            for old in db.scalars(
                select(FoodReference).where(FoodReference.slug == record["slug"])
            ):
                old.active = False
            db.add(FoodReference(id=version, slug=record["slug"], snapshot=record))
    db.flush()


def reference_view(reference):
    return {"id": reference.id, **reference.snapshot}


def rounded(value):
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def nutrition_for(portions):
    totals, subtotals, coverage = {}, {}, {}
    complete = 0
    for key in NUTRIENTS:
        known = [p for p in portions if p.reference_snapshot["per_100_g"].get(key) is not None]
        value = sum(
            (
                Decimal(str(p.reference_snapshot["per_100_g"][key])) * p.amount_g / 100
                for p in known
            ),
            Decimal(0),
        )
        coverage[key] = sum(p.amount_g for p in known)
        subtotals[key] = rounded(value) if known else None
        totals[key] = rounded(value) if portions and len(known) == len(portions) else None
        complete += totals[key] is not None
    return {
        "status": "complete"
        if complete == len(NUTRIENTS)
        else "partial"
        if any(v is not None for v in subtotals.values())
        else "unavailable",
        "total": totals,
        "known_subtotal": subtotals,
        "covered_g": coverage,
        "basis": "provided_edible_weight_reference_estimate",
        "intake": None,
    }


def groups_for(portions):
    groups = {}
    for p in portions:
        group = p.reference_snapshot["food_group"]
        groups[group] = groups.get(group, 0) + p.amount_g
    return groups


def plan_comparison(plan, portions):
    if not plan:
        return None
    groups = groups_for(portions)
    known = groups.get("unknown", 0) == 0
    return {
        "plan": plan,
        "status": "recorded_comparison" if known else "incomplete_food_groups",
        "groups": [
            {
                "group": group,
                "target_g": target,
                "recorded_g": groups.get(group, 0),
                "difference_g": groups.get(group, 0) - target if known else None,
            }
            for group, target in plan["target_g"].items()
        ],
        "nutritional_compliance": None,
    }
