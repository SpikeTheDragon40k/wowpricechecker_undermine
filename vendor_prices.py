"""Vendor price lookup — detects risk-free vendor-flip opportunities."""
from __future__ import annotations

from typing import Any

VENDOR_PRICES: dict[int, int] = {
    29739: 25000,
    21228: 5000,
    63530: 50000,
    954: 2500,
    955: 2500,
    957: 2500,
    159: 500,
    1179: 1000,
    1205: 2500,
    1708: 500,
    1645: 5000,
    8766: 50000,
}


def get_vendor_price(
    item_id: int,
    blizzard_client: Any = None,
) -> int | None:
    copper = VENDOR_PRICES.get(item_id)
    if copper is not None:
        return copper

    if blizzard_client is not None:
        try:
            info = blizzard_client.get_item_info(item_id)
            if info and info.get("sell_price") is not None:
                return int(info["sell_price"])
        except Exception:
            pass

    return None


def is_vendor_flip(realm_price: int, vendor_price: int | None) -> bool:
    if vendor_price is None or realm_price <= 0:
        return False
    return realm_price < vendor_price


def vendor_flip_profit(realm_price: int, vendor_price: int | None) -> int | None:
    if not is_vendor_flip(realm_price, vendor_price):
        return None
    return vendor_price - realm_price
