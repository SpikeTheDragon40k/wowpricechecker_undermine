"""Deal scoring engine — rates each deal 0-100 for profit potential."""
from __future__ import annotations

from typing import Any

CATEGORY_VELOCITY: dict[int, float] = {
    0: 1.0,
    1: 0.3,
    2: 0.1,
    3: 1.0,
    4: 0.1,
    5: 0.9,
    6: 0.4,
    7: 1.0,
    8: 0.6,
    9: 0.3,
    10: 0.5,
    11: 0.6,
    12: 0.5,
}

DEFAULT_WEIGHTS = {
    "discount_depth": 0.35,
    "absolute_profit": 0.35,
    "quantity": 0.15,
    "velocity": 0.15,
}


def calculate_deal_score(
    realm_price: int,
    region_median: int,
    quantity: int,
    class_id: int | None = None,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS

    if region_median <= 0 or realm_price <= 0:
        return 0.0

    pct_of_median = (realm_price / region_median) * 100.0

    depth = max(0.0, 50.0 - pct_of_median * 1.0)

    profit_per_item = region_median - realm_price
    total_profit = profit_per_item * quantity

    if total_profit >= 500_000:
        profit_score = 30.0
    elif total_profit >= 100_000:
        profit_score = 27.0
    elif total_profit >= 50_000:
        profit_score = 23.0
    elif total_profit >= 10_000:
        profit_score = 18.0
    elif total_profit >= 5_000:
        profit_score = 14.0
    elif total_profit >= 1_000:
        profit_score = 10.0
    elif total_profit >= 500:
        profit_score = 6.0
    elif total_profit >= 100:
        profit_score = 3.0
    else:
        profit_score = 1.0

    if quantity >= 200:
        qty_score = 10.0
    elif quantity >= 100:
        qty_score = 9.0
    elif quantity >= 50:
        qty_score = 8.0
    elif quantity >= 20:
        qty_score = 6.0
    elif quantity >= 10:
        qty_score = 4.0
    elif quantity >= 5:
        qty_score = 3.0
    elif quantity >= 2:
        qty_score = 2.0
    else:
        qty_score = 1.0

    velocity_mult = CATEGORY_VELOCITY.get(class_id, 0.3) if class_id is not None else 0.5
    velocity_score = 10.0 * velocity_mult

    raw = (
        depth * w["discount_depth"]
        + profit_score * w["absolute_profit"]
        + qty_score * w["quantity"]
        + velocity_score * w["velocity"]
    )

    return round(raw, 1)


def score_and_rank_deals(
    deals: list[dict[str, Any]],
    info: dict[int, dict],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    for deal in deals:
        class_id = info.get(deal["item_id"], {}).get("class_id")
        deal["score"] = calculate_deal_score(
            realm_price=deal["price"],
            region_median=deal["region_median"],
            quantity=deal["quantity"],
            class_id=class_id,
            weights=weights,
        )

    deals.sort(key=lambda d: d["score"], reverse=True)
    return deals
