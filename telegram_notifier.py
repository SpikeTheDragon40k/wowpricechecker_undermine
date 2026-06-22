"""Telegram message formatting — digest mode + inline keyboards."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

import requests

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def copper_to_gold_string(copper: int) -> str:
    if copper == 0:
        return "0g"
    gold = copper // 10000
    silver = (copper % 10000) // 100
    c = copper % 100
    if gold > 0:
        return f"{gold}g {silver}s {c}c"
    elif silver > 0:
        return f"{silver}s {c}c"
    return f"{c}c"


def gold_to_compact(gold: int) -> str:
    if gold >= 1_000_000:
        return f"{gold / 1_000_000:.1f}m"
    elif gold >= 1_000:
        return f"{gold / 1_000:.1f}k"
    return str(gold)


def _trend_icon(direction: str) -> str:
    return {
        "up": "\U0001f4c8",
        "down": "\U0001f4c9",
        "flat": "\u27a1\ufe0f",
        "unknown": "\u2753",
    }.get(direction, "\u2753")


def _class_emoji(class_id: int | None) -> str:
    return {
        0: "\U0001f9ea",
        1: "\U0001f4e6",
        2: "\u2694\ufe0f",
        3: "\U0001f48e",
        4: "\U0001f6e1\ufe0f",
        5: "\U0001f52e",
        6: "\U0001f300",
        7: "\U0001f4e6",
        8: "\u2728",
        9: "\U0001f4dc",
        10: "\U0001f43e",
        11: "\u2753",
    }.get(class_id, "\U0001f4e6")


def send_message(
    bot_token: str, chat_id: str, text: str,
    keyboard: dict | None = None,
) -> None:
    url = API_URL.format(token=bot_token)
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()


def _build_inline_keyboard(item_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "\U0001f50d Wowhead",
                    "url": f"https://www.wowhead.com/item={item_id}",
                },
                {
                    "text": "\U0001f4ca Undermine",
                    "url": f"https://undermine.exchange/item={item_id}",
                },
            ],
        ]
    }


def format_deal_digest(
    realm: str,
    deals: list[dict[str, Any]],
    info: dict[int, dict],
    total_deals_found: int,
    credits_remaining: int,
    credits_limit: int,
    token_price: int | None = None,
) -> tuple[str, dict | None]:
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M")
    lines = [
        f"\U0001f4ca <b>Deal Digest \u2014 {html.escape(realm)}</b>",
        f"Scanned: {now} UTC",
        "",
    ]

    if not deals:
        lines.append("No new deals found this scan.")
        lines.append("")
    else:
        lines.append("\U0001f525 <b>TOP PICKS</b> (by deal score):")
        lines.append("")

        for idx, deal in enumerate(deals[:12], 1):
            item_id = deal["item_id"]
            item_name = info.get(item_id, {}).get("name", f"Item {item_id}")
            class_id = info.get(item_id, {}).get("class_id")

            price_str = copper_to_gold_string(deal["price"])
            median_str = copper_to_gold_string(deal["region_median"])
            pct_str = f"{deal['pct_of_median']:.1f}%"
            score = deal.get("score", 0)
            profit_gold = (deal["region_median"] - deal["price"]) * deal["quantity"] // 10000
            profit_compact = gold_to_compact(profit_gold)

            emoji = "\U0001f911" if deal.get("is_vendor_flip") else _class_emoji(class_id)

            flip_tag = ""
            if deal.get("is_vendor_flip"):
                flip_str = copper_to_gold_string(deal["vendor_price"])
                flip_tag = f" <b>[VENDOR {flip_str}]</b>"

            trend = deal.get("trend", {})
            trend_icon = _trend_icon(trend.get("direction", "unknown"))
            trend_str = f" {trend_icon}" if trend.get("data_points", 0) >= 2 else ""

            lines.append(
                f"{idx}. {emoji} <a href='https://www.wowhead.com/item={item_id}'>"
                f"{html.escape(item_name)}</a>{trend_str}{flip_tag}"
            )
            lines.append(
                f"   \U0001f4b0 {price_str} \u2192 median {median_str} "
                f"({pct_str}) | Qty: {deal['quantity']} | "
                f"\U0001f3c6 {profit_compact} profit | Score: {score}"
            )
            lines.append("")

        if total_deals_found > len(deals):
            lines.append(
                f"<i>... and {total_deals_found - len(deals)} more deals "
                f"(showing top {len(deals)} by score)</i>"
            )
            lines.append("")

    cred_pct = (credits_remaining / credits_limit * 100) if credits_limit > 0 else 0
    lines.append("\u2014" * 20)
    lines.append(f"\u26a1 API Credits: {credits_remaining:,} / {credits_limit:,} ({cred_pct:.0f}%)")

    if token_price is not None:
        lines.append(f"\U0001fa99 WoW Token: {token_price:,}g")

    text = "\n".join(lines)

    keyboard = None
    if deals:
        keyboard = _build_inline_keyboard(deals[0]["item_id"])

    return text, keyboard


def format_watch_alert(
    item_name: str, item_id: int,
    old_price: int, new_price: int, change_pct: float,
) -> str:
    direction = "\U0001f4c8" if change_pct > 0 else "\U0001f4c9"
    old_str = copper_to_gold_string(old_price)
    new_str = copper_to_gold_string(new_price)
    return (
        f"{direction} <b>Watch Alert</b>\n"
        f"<a href='https://www.wowhead.com/item={item_id}'>{html.escape(item_name)}</a>\n"
        f"Price: {old_str} \u2192 {new_str} ({change_pct:+.1f}%)"
    )


def format_trend_report(
    realm: str,
    top_deals: list[dict[str, Any]],
    biggest_drops: list[dict[str, Any]],
    scan_days: list[dict[str, Any]],
    item_names: dict[int, str],
    token_price: int | None = None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%d %b %Y")
    lines = [
        f"\U0001f4c6 <b>Weekly Market Report \u2014 {html.escape(realm)}</b>",
        f"Generated: {now}",
        "",
    ]

    if top_deals:
        lines.append("\U0001f3c6 <b>TOP DEALS THIS WEEK</b>")
        for d in top_deals[:8]:
            name = item_names.get(d["item_id"], f"Item {d['item_id']}")
            profit_g = (d["median"] - d["price"]) * d["quantity"] // 10000
            lines.append(
                f"  \u2022 <a href='https://www.wowhead.com/item={d['item_id']}'>"
                f"{html.escape(name)}</a> \u2014 {gold_to_compact(profit_g)} profit "
                f"({d['pct_of_median']:.1f}% of median, qty {d['quantity']})"
            )
        lines.append("")

    if biggest_drops:
        lines.append("\U0001f4c9 <b>BIGGEST PRICE DROPS</b>")
        for d in biggest_drops[:5]:
            name = item_names.get(d["item_id"], f"Item {d['item_id']}")
            drop_pct = (d["max_price"] - d["min_price"]) / d["max_price"] * 100
            lines.append(
                f"  \u2022 {html.escape(name)} \u2014 "
                f"{copper_to_gold_string(d['max_price'])} \u2192 {copper_to_gold_string(d['min_price'])} "
                f"(\u2193 {drop_pct:.0f}%)"
            )
        lines.append("")

    if scan_days:
        total_deals = sum(s["deals_found"] for s in scan_days)
        avg_credits = sum(s["credits_remaining"] for s in scan_days) // len(scan_days)
        lines.append("\U0001f4ca <b>SCAN STATS</b>")
        lines.append(f"  \u2022 Active scan days: {len(scan_days)}")
        lines.append(f"  \u2022 Total deals found: {total_deals}")
        lines.append(f"  \u2022 Avg credits remaining: {avg_credits:,}")
        lines.append("")

    if token_price is not None:
        lines.append(f"\U0001fa99 WoW Token: {token_price:,}g")

    return "\n".join(lines)


def send_deal_alert(
    bot_token: str,
    chat_id: str,
    realm: str,
    item_id: int,
    item_name: str,
    price_copper: int,
    quantity: int,
    region_median: int,
    pct_of_median: float,
) -> None:
    price_str = copper_to_gold_string(price_copper)
    median_str = copper_to_gold_string(region_median)
    discount = 100 - pct_of_median

    wowhead_url = f"https://www.wowhead.com/item={item_id}"

    lines = [
        f"Deal on {realm}!",
        f"<a href='{wowhead_url}'>{item_name}</a> (ID {item_id})",
        f"Price: {price_str}",
        f"Regional median: {median_str}",
        f"Discount: {discount:.1f}% ({pct_of_median:.1f}% of median)",
        f"Quantity: {quantity}",
    ]

    text = "\n".join(lines)
    keyboard = _build_inline_keyboard(item_id)
    send_message(bot_token, chat_id, text, keyboard)
