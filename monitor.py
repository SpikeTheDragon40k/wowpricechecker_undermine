#!/usr/bin/env python3
"""WoW Auction House deal scanner — main orchestrator."""
from __future__ import annotations

import sys
from typing import Any

from config import Config
from state import State
from undermine import UndermineClient
from deal_scorer import score_and_rank_deals
from vendor_prices import get_vendor_price, vendor_flip_profit
from history import PriceHistory
from telegram_notifier import (
    send_message,
    format_deal_digest,
    format_watch_alert,
    copper_to_gold_string,
)

ALERTED_DEALS_KEY = "alerted_deals"
EQUIPMENT_CLASSES = {2, 4}


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


def fetch_token_price(region: str = "eu") -> int | None:
    import requests as req
    try:
        resp = req.get(
            "https://wowtokenprice.com/api/v1/tokens/prices",
            headers={"User-Agent": "underbot/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            return None
        for entry in data.get("data", []):
            if entry.get("region") == region.lower() and entry.get("gameVersion") == "retail":
                return entry.get("priceGold")
        return None
    except Exception:
        return None


def process_realm(
    cfg: Config,
    undermine: UndermineClient,
    state: State,
    history: PriceHistory,
    realm: str,
) -> tuple[list[dict[str, Any]], dict[int, dict]]:
    print(f"\n\u2500\u2500 Scanning {realm} ({cfg.region}) \u2500\u2500")

    try:
        realm_items = undermine.get_realm_items(cfg.region, realm)
    except RuntimeError as e:
        print(f"  ERROR fetching realm items: {e}", file=sys.stderr)
        return [], {}

    print(f"  Items on realm: {len(realm_items)}")

    try:
        region_items = undermine.get_region_items(cfg.region)
    except RuntimeError as e:
        print(f"  ERROR fetching region summary: {e}", file=sys.stderr)
        return [], []

    print(f"  Items in region: {len(region_items)}")

    alerted_deals: dict[str, Any] = state.get(ALERTED_DEALS_KEY, {})
    raw_deals: list[dict[str, Any]] = []

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

            raw_deals.append({
                "item_id": item_id,
                "price": realm_price,
                "quantity": realm_qty,
                "region_median": region_median,
                "pct_of_median": pct,
            })

    print(f"  Raw deals: {len(raw_deals)}")

    if not raw_deals:
        return [], {}

    info: dict[int, dict] = {}
    has_blizzard = cfg.blizzard_client_id and cfg.blizzard_client_secret

    if has_blizzard:
        print("  Resolving item info via Blizzard API...")
        item_ids = [d["item_id"] for d in raw_deals]
        info = resolve_item_info(
            (cfg.blizzard_client_id, cfg.blizzard_client_secret, cfg.region),
            item_ids,
        )

    before = len(raw_deals)
    deals_filtered = []
    for d in raw_deals:
        class_id = info.get(d["item_id"], {}).get("class_id")

        if class_id is not None and class_id in cfg.exclude_classes:
            continue

        if cfg.focus_classes is not None and (
            class_id is None or class_id not in cfg.focus_classes
        ):
            continue

        deals_filtered.append(d)

    filtered_count = before - len(deals_filtered)
    if filtered_count:
        print(f"  Filtered out {filtered_count} items by class")

    if not deals_filtered:
        return [], info

    deals_filtered = score_and_rank_deals(deals_filtered, info, cfg.score_weights)
    print(f"  Scored deals: {len(deals_filtered)}")

    blizzard_client = None
    if has_blizzard:
        from blizzard import BlizzardClient as BC
        blizzard_client = BC(
            cfg.blizzard_client_id, cfg.blizzard_client_secret, cfg.region
        )

    for d in deals_filtered:
        vendor_price = get_vendor_price(d["item_id"], blizzard_client)
        profit = vendor_flip_profit(d["price"], vendor_price)
        if profit is not None:
            d["is_vendor_flip"] = True
            d["vendor_price"] = vendor_price
            d["score"] = max(d["score"], 85.0)
            print(f"  \U0001f911 Vendor flip: item {d['item_id']} \u2014 "
                  f"profit {copper_to_gold_string(profit)}/unit")

    for d in deals_filtered:
        history.record_snapshot(
            item_id=d["item_id"],
            realm=realm,
            region=cfg.region,
            price=d["price"],
            median=d["region_median"],
            quantity=d["quantity"],
        )
        trend = history.get_trend(d["item_id"], realm, days=14)
        d["trend"] = trend

    for entry in state.get_watchlist():
        str_id = str(entry["item_id"])
        realm_entry = realm_items.get(str_id)
        if not realm_entry:
            continue

        current_price = realm_entry.get("price", 0)
        last_price = entry.get("last_price", 0)

        if last_price > 0 and current_price > 0:
            change_pct = (current_price - last_price) / last_price * 100
            if abs(change_pct) >= 20:
                item_name = entry.get("name", f"Item {entry['item_id']}")
                alert_text = format_watch_alert(
                    item_name, entry["item_id"],
                    last_price, current_price, change_pct,
                )
                try:
                    send_message(
                        cfg.telegram_bot_token, cfg.telegram_chat_id, alert_text
                    )
                except Exception as e:
                    print(f"  WARNING: failed to send watch alert: {e}")

        entry["last_price"] = current_price

    return deals_filtered, info


def main() -> None:
    cfg = Config()
    state = State(cfg.state_file_path)
    history = PriceHistory(cfg.price_history_db)
    undermine = UndermineClient(cfg.undermine_api_key)

    print(
        f"Underbot \u2014 scanning {len(cfg.realms)} realm(s) "
        f"at \u2264{cfg.price_percent_threshold}% of regional median"
    )

    all_deals: list[dict[str, Any]] = []
    all_info: dict[int, dict] = {}

    for realm in cfg.realms:
        realm_deals, realm_info = process_realm(cfg, undermine, state, history, realm)
        all_deals.extend(realm_deals)
        all_info.update(realm_info)

    all_deals.sort(key=lambda d: d["score"], reverse=True)

    token_price = fetch_token_price(cfg.region)
    try:
        remaining, limit = undermine.check_credits()
    except RuntimeError:
        remaining, limit = 0, 3000

    digest_text, keyboard = format_deal_digest(
        realm=", ".join(cfg.realms) if len(cfg.realms) > 1 else cfg.realms[0],
        deals=all_deals[:15],
        info=all_info,
        total_deals_found=len(all_deals),
        credits_remaining=remaining,
        credits_limit=limit,
        token_price=token_price,
    )

    try:
        send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, digest_text, keyboard)
        print(f"\nSent digest with {len(all_deals)} deal(s)")
    except Exception as e:
        print(f"ERROR sending digest: {e}", file=sys.stderr)

    alerted_deals: dict[str, Any] = state.get(ALERTED_DEALS_KEY, {})
    for deal in all_deals:
        alerted_deals[str(deal["item_id"])] = {
            "price": deal["price"],
            "last_alerted": "",
        }
    state.set(ALERTED_DEALS_KEY, alerted_deals)

    state.set("last_deals", all_deals[:15])
    state.set("last_credits", remaining)

    primary_realm = cfg.realms[0] if cfg.realms else "unknown"
    history.record_scan_summary(
        realm=primary_realm,
        region=cfg.region,
        deals_found=len(all_deals),
        credits_remaining=remaining,
    )

    if cfg.trend_report_interval > 0:
        scan_counter = state.increment_scan_counter()
        if scan_counter % cfg.trend_report_interval == 0:
            print("  Generating trend report...")
            top = history.get_top_deals_last_days(primary_realm, days=7)
            drops = history.get_biggest_drops(primary_realm, days=7)
            scans = history.get_scan_summary_last_days(primary_realm, days=7)
            item_names = {
                iid: inf.get("name", f"Item {iid}")
                for iid, inf in all_info.items()
            }

            from telegram_notifier import format_trend_report
            report = format_trend_report(
                realm=primary_realm,
                top_deals=top,
                biggest_drops=drops,
                scan_days=scans,
                item_names=item_names,
                token_price=token_price,
            )
            try:
                send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, report)
                print("  Trend report sent.")
            except Exception as e:
                print(f"  WARNING: failed to send trend report: {e}")

    history.close()
    state.save()
    print("\nScan complete.")


if __name__ == "__main__":
    main()
