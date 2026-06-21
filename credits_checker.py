#!/usr/bin/env python3
from __future__ import annotations

import sys

from config import Config
from undermine import UndermineClient
from telegram_notifier import send_message


def main() -> None:
    cfg = Config()
    undermine = UndermineClient(cfg.undermine_api_key)

    try:
        remaining, limit = undermine.check_credits()
    except RuntimeError as e:
        print(f"ERROR checking credits: {e}", file=sys.stderr)
        sys.exit(1)

    text = f"⚡ API Credits: {remaining} / {limit} remaining"
    print(text)

    send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, text)


if __name__ == "__main__":
    main()
