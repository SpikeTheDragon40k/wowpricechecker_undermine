#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Any

from config import Config
from state import State
from undermine import UndermineClient
from telegram_notifier import send_deal_alert, copper_to_gold_string

ALERTED_DEALS_KEY = "alerted_deals"


EQUIPMENT_CLASSES = {2, 4}  # Weapon, Armor


def resolve_item_info(
    blizzard_cfg: tuple[str, str, str], item_ids: list[int]
) -> dict[int, dict]:
    from blizzard import BlizzardClient

    client_id, client_secret, region = blizzard_cfg
    client = BlizzardClient(client_id, client_secret, region)
    info: dict[int, dict] = {}
    for iid in item_ids:
        try:
            result = client.get_item_info(iid)
            if result:
                info[iid] = result
        except Exception:
            pass
    return info


def main() -> None:
    cfg = Config()
    state = State(cfg.state_file_path)

    print(
        f"Scanning {cfg.realm} ({cfg.region}) for deals "
        f"at ≤{cfg.price_percent_threshold}% of regional median..."
    )

    undermine = UndermineClient(cfg.undermine_api_key)

    # 1. Fetch realm items
    try:
        realm_items = undermine.get_realm_items(cfg.region, cfg.realm)
    except RuntimeError as e:
        print(f"ERROR fetching realm items: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Items on realm: {len(realm_items)}")

    # 2. Fetch region summary
    try:
        region_items = undermine.get_region_items(cfg.region)
    except RuntimeError as e:
        print(f"ERROR fetching region summary: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Items in region: {len(region_items)}")

    # 3. Cross-reference and find deals
    alerted_deals: dict[str, Any] = state.get(ALERTED_DEALS_KEY, {})
    deals: list[dict[str, Any]] = []

    for str_id, realm_entry in realm_items.items():
        realm_price = realm_entry.get("price", 0)
        realm_qty = realm_entry.get("quantity", 0)

        if realm_price <= 0 or realm_qty <= 0:
            continue

        region_entry = region_items.get(str_id)
        if not region_entry:
            continue

        region_median = region_entry.get("median", 0)
        if region_median <= 0:
            continue

        pct = (realm_price / region_median) * 100
        if pct <= cfg.price_percent_threshold:
            item_id = int(str_id)
            previous = alerted_deals.get(str_id)

            if previous and previous.get("price") == realm_price:
                continue

            deals.append(
                {
                    "item_id": item_id,
                    "price": realm_price,
                    "quantity": realm_qty,
                    "region_median": region_median,
                    "pct_of_median": pct,
                }
            )

    print(f"Deals found: {len(deals)}")

    # 4. Resolve names + classes for deal items (if Blizzard creds available)
    names: dict[int, str] = {}
    if cfg.blizzard_client_id and cfg.blizzard_client_secret and deals:
        print("Resolving item info via Blizzard API...")
        item_ids = [d["item_id"] for d in deals]
        info = resolve_item_info(
            (cfg.blizzard_client_id, cfg.blizzard_client_secret, cfg.region),
            item_ids,
        )
        names = {iid: inf["name"] for iid, inf in info.items() if inf.get("name")}

        # Filter out equipment (Weapon class 2, Armor class 4)
        before = len(deals)
        deals = [
            d
            for d in deals
            if info.get(d["item_id"], {}).get("class_id") not in EQUIPMENT_CLASSES
        ]
        filtered = before - len(deals)
        if filtered:
            filtered_ids = [
                iid
                for iid, inf in info.items()
                if inf.get("class_id") in EQUIPMENT_CLASSES
            ]
            print(f"Filtered out {filtered} equipment items:")
            for fid in filtered_ids:
                print(
                    f"  {names.get(fid, 'Unknown')} ({fid})"
                    f" [{info[fid].get('class_name', '?')}]"
                )

    # 5. Send alerts and update state
    for deal in deals:
        item_id = deal["item_id"]
        str_id = str(item_id)
        item_name = names.get(item_id, "Unknown")

        print(
            f"  Deal: {item_name} ({item_id}) — "
            f"{copper_to_gold_string(deal['price'])} "
            f"= {deal['pct_of_median']:.1f}% of regional median"
        )

        send_deal_alert(
            cfg.telegram_bot_token,
            cfg.telegram_chat_id,
            cfg.realm,
            item_id,
            item_name,
            deal["price"],
            deal["quantity"],
            deal["region_median"],
            deal["pct_of_median"],
        )

        alerted_deals[str_id] = {
            "price": deal["price"],
            "last_alerted": deal.get("lastSeen", ""),
        }

    state.set(ALERTED_DEALS_KEY, alerted_deals)
    state.save()

    print("Done.")


if __name__ == "__main__":
    main()
