from typing import Any

import requests

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def copper_to_gold_string(copper: int) -> str:
    gold = copper // 10000
    silver = (copper % 10000) // 100
    c = copper % 100
    return f"{gold}g {silver}s {c}c"


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    url = API_URL.format(token=bot_token)
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    resp.raise_for_status()


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

    send_message(bot_token, chat_id, text)
