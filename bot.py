#!/usr/bin/env python3
"""Interactive Telegram bot daemon — listens for commands and responds."""
from __future__ import annotations

import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from state import State
from telegram_notifier import (
    send_message,
    copper_to_gold_string,
    format_deal_digest,
)

POLL_URL = "https://api.telegram.org/bot{token}/getUpdates"
LAST_UPDATE_KEY = "last_bot_update_id"


def handle_command(
    cmd: str,
    args: str,
    cfg: Config,
    state: State,
) -> tuple[str, dict | None]:
    if cmd == "/help":
        return (
            "<b>Underbot Commands</b>\n\n"
            "/scan \u2014 Run a scan now\n"
            "/deals [N] \u2014 Show top N deals from last scan (default 10)\n"
            "/watch &lt;item_id&gt; \u2014 Add item to your watchlist\n"
            "/unwatch &lt;item_id&gt; \u2014 Remove item from watchlist\n"
            "/mylist \u2014 Show your watchlist\n"
            "/token \u2014 Current WoW Token price\n"
            "/stats \u2014 Scan history and API credits\n"
            "/help \u2014 This message"
        ), None

    elif cmd == "/scan":
        try:
            from monitor import main as scan_main
            scan_main()
            return "\u2705 Scan complete.", None
        except Exception as e:
            return f"\u274c Scan failed: {e}", None

    elif cmd == "/deals":
        try:
            limit = int(args) if args.isdigit() else 10
        except (ValueError, AttributeError):
            limit = 10

        deals = state.get("last_deals", [])
        if not deals:
            return "No deals from last scan.", None

        info = {}
        for d in deals[:limit]:
            info[d["item_id"]] = {}
        text, kb = format_deal_digest(
            realm=cfg.realms[0],
            deals=deals[:limit],
            info=info,
            total_deals_found=len(deals),
            credits_remaining=state.get("last_credits", 0),
            credits_limit=3000,
        )
        return text, kb

    elif cmd == "/watch":
        if not args or not args.strip().isdigit():
            return "Usage: /watch &lt;item_id&gt;\nExample: /watch 4409", None
        item_id = int(args.strip())
        ok = state.add_to_watchlist(item_id)
        if ok:
            return f"\u2705 Added item {item_id} to watchlist.", None
        return f"\u2139\ufe0f Item {item_id} is already in your watchlist.", None

    elif cmd == "/unwatch":
        if not args or not args.strip().isdigit():
            return "Usage: /unwatch &lt;item_id&gt;\nExample: /unwatch 4409", None
        item_id = int(args.strip())
        ok = state.remove_from_watchlist(item_id)
        if ok:
            return f"\u2705 Removed item {item_id} from watchlist.", None
        return f"\u274c Item {item_id} was not in your watchlist.", None

    elif cmd == "/mylist":
        wl = state.get_watchlist()
        if not wl:
            return "Your watchlist is empty.\nUse /watch &lt;item_id&gt; to add items.", None

        lines = ["<b>Your Watchlist</b>", ""]
        for entry in wl:
            name = entry.get("name", f"Item {entry['item_id']}")
            last_str = copper_to_gold_string(entry.get("last_price", 0))
            lines.append(
                f"\u2022 <a href='https://www.wowhead.com/item={entry['item_id']}'>{name}</a> "
                f"(ID {entry['item_id']}) \u2014 last seen: {last_str}"
            )
        return "\n".join(lines), None

    elif cmd == "/token":
        try:
            resp = requests.get(
                "https://wowtokenprice.com/api/v1/tokens/prices",
                headers={"User-Agent": "underbot/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return "\u274c Token API returned error", None
            for entry in data.get("data", []):
                if entry.get("region") == cfg.region.lower() and entry.get("gameVersion") == "retail":
                    price = entry.get("priceGold", "N/A")
                    return f"\U0001fa99 WoW Token ({cfg.region.upper()}): {price:,}g", None
            return "\u274c No token data for your region", None
        except Exception as e:
            return f"\u274c Failed to fetch token price: {e}", None

    elif cmd == "/stats":
        deals_found = len(state.get("last_deals", []))
        credits = state.get("last_credits", "N/A")
        watch_count = len(state.get_watchlist())
        return (
            "<b>Bot Stats</b>\n\n"
            f"\u2022 Deals found last scan: {deals_found}\n"
            f"\u2022 API Credits remaining: {credits:,}\n"
            f"\u2022 Watchlist items: {watch_count}\n"
            f"\u2022 Realms: {', '.join(cfg.realms)}\n"
            f"\u2022 Threshold: {cfg.price_percent_threshold}% of median"
        ), None

    else:
        return f"Unknown command: {cmd}\nUse /help for available commands.", None


def main() -> None:
    cfg = Config()
    state = State(cfg.state_file_path)

    print(f"Starting interactive bot (poll every {cfg.telegram_poll_interval}s)...")
    print(f"Region: {cfg.region}, Realms: {cfg.realms}")

    offset = state.get(LAST_UPDATE_KEY, 0)

    while True:
        try:
            url = POLL_URL.format(token=cfg.telegram_bot_token)
            resp = requests.get(
                url,
                params={"offset": offset + 1, "timeout": cfg.telegram_poll_interval},
                timeout=cfg.telegram_poll_interval + 10,
            )
            resp.raise_for_status()
            updates = resp.json().get("result", [])

            for update in updates:
                update_id = update["update_id"]
                if update_id <= offset:
                    continue
                offset = update_id

                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()

                if chat_id != cfg.telegram_chat_id:
                    continue

                if not text:
                    continue

                parts = text.split(maxsplit=1)
                cmd = parts[0].lower() if parts else ""
                args = parts[1] if len(parts) > 1 else ""

                response, keyboard = handle_command(cmd, args, cfg, state)
                if response:
                    send_message(cfg.telegram_bot_token, chat_id, response, keyboard)

            if offset > state.get(LAST_UPDATE_KEY, 0):
                state.set(LAST_UPDATE_KEY, offset)
                state.save()

        except KeyboardInterrupt:
            print("\nBot stopped.")
            break
        except Exception as e:
            print(f"Bot error: {e}", file=sys.stderr)
            time.sleep(cfg.telegram_poll_interval)


if __name__ == "__main__":
    main()
