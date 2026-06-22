# Telegram Undermine — WoW Auction House Deal Scanner & Bot

Scans [Undermine Exchange](https://undermine.exchange) for bargains across one or more WoW realms and delivers deal alerts, price tracking, and an interactive Telegram bot.

## Features

- **Multi-realm scanning** — scan any number of realms in a single run
- **Deal detection** — finds items priced ≤ X% of their regional median (default: 5%)
- **Equipment filter** — automatically excludes weapons/armor whose medians are distorted by item level variants
- **Deal scoring** — ranks deals by discount depth, absolute profit, quantity, and historical velocity
- **Vendor flip detection** — flags items that can be bought from a vendor for profit
- **Price history** — tracks prices and trends over 14 days
- **Watchlist** — monitors specific items and alerts on ≥20% price changes
- **WoW Token price** — shows current token price in scan digests and via `/token`
- **Trend reports** — weekly summaries of top deals and biggest price drops
- **API credits monitor** — reports remaining Undermine Exchange points every 2 hours
- **Interactive Telegram bot** — run 24/7, responds to commands

## System Architecture

Three systemd units:

| Unit | Type | Schedule |
|---|---|---|
| `price-alert.timer` | triggers `monitor.py` | 00:00, 08:00, 16:00 daily |
| `credits-checker.timer` | triggers `credits_checker.py` | Every 2 hours |
| `underbot-bot.service` | long-running daemon | Always online |

## Telegram Commands

| Command | Description |
|---|---|
| `/scan` | Run a full scan now |
| `/deals [N]` | Show top N deals from last scan (default 10) |
| `/watch <item_id>` | Add an item to your watchlist |
| `/unwatch <item_id>` | Remove an item from your watchlist |
| `/mylist` | Show your watchlist with last seen prices |
| `/token` | Current WoW Token price for your region |
| `/stats` | Scan stats, remaining API credits, watchlist count |
| `/help` | List all commands |

### Example digest

```
📊 Deal Digest — pozzo-delleternità
Scanned: 22 Jun 2026 13:29 UTC

🔥 TOP PICKS (by deal score):

1. 📜 Plans: Bloodforged Warfists (ID 87411)
   💰 11g 26s → median 312g 78s (3.6%) | Qty: 1 | 🏆 301 profit | Score: 88.4

2. 📜 Plans: Obsidian Seared Hexsword (ID 194476)
   💰 75g 1s → median 6,821g 82s (1.1%) | Qty: 1 | 🏆 6.7k profit | Score: 85.2

3. 🔧 Proficient Leatherworker's Toolset (ID 222485)
   💰 150g 0s → median 5,000g 0s (3.0%) | Qty: 1 | 🏆 4.9k profit | Score: 82.1

————————————————————
⚡ API Credits: 2,965 / 3,000 (99%)
🪙 WoW Token: 357,143g
```

## Setup

### Requirements

- Python 3.10+
- [Undermine Exchange API key](https://undermine.exchange/api.html) (free, requires Patreon login)
- [Telegram bot token](https://t.me/BotFather) and chat ID
- [Blizzard API credentials](https://develop.battle.net/) (free — enables item names and class filtering)

### 1. Clone & install

```bash
git clone https://github.com/your-user/telegram-undermine.git
cd telegram-undermine
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Set your environment variables (see table below).

### 3. Test

```bash
python3 monitor.py
```

### 4. Install systemd services

```bash
sudo ./install.sh
```

This enables the scan timer, credits checker, and bot daemon.

### 5. Manual commands

```bash
# Run scan immediately
sudo systemctl start price-alert.service

# Check bot logs
sudo journalctl -u underbot-bot.service -f

# Check credits immediately
sudo systemctl start credits-checker.service
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `UNDERMINE_API_KEY` | ✅ | — | API key from [undermine.exchange](https://undermine.exchange/api.html) |
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | ✅ | — | Your Telegram chat ID |
| `REGION` | — | `eu` | WoW region (`us`, `eu`, `tw`, `kr`) |
| `REALM` | — | `pozzo-delleternità` | Single realm slug (used if `REALMS` not set) |
| `REALMS` | — | — | Comma-separated realm slugs, overrides `REALM` |
| `PRICE_PERCENT_THRESHOLD` | — | `5.0` | Alert when realm price ≤ this % of regional median |
| `BLIZZARD_CLIENT_ID` | — | — | Blizzard API client ID |
| `BLIZZARD_CLIENT_SECRET` | — | — | Blizzard API client secret |
| `STATE_FILE_PATH` | — | `state.json` | Persistence file path |
| `PRICE_HISTORY_DB` | — | `price_history.db` | SQLite database for price history |
| `FOCUS_CLASSES` | — | — | Comma-separated class IDs to exclusively scan (e.g. `0,1,3,5,6,7,8,9,11`) |
| `EXCLUDE_CLASSES` | — | `2,4` | Comma-separated class IDs to skip (default excludes Weapon and Armor) |
| `SCORE_WEIGHTS` | — | `0.35 0.35 0.15 0.15` | Deal scoring weights: discount_depth, absolute_profit, quantity, velocity |
| `TREND_REPORT_INTERVAL` | — | `7` | Generate trend report every N scans (0 = off) |
| `TELEGRAM_POLL_INTERVAL` | — | `30` | Bot polling interval in seconds |

## Files

| File | Purpose |
|---|---|
| `monitor.py` | Main orchestrator — scan, filter, score, alert |
| `bot.py` | Interactive Telegram bot daemon |
| `undermine.py` | Undermine Exchange API client |
| `blizzard.py` | Blizzard API client (item names + classes) |
| `telegram_notifier.py` | Telegram message formatting (digest, deals, trends) |
| `config.py` | Environment variable loading |
| `state.py` | JSON file persistence (deals, watchlist, counters) |
| `history.py` | SQLite price history and trend analysis |
| `deal_scorer.py` | Deal ranking algorithm |
| `vendor_prices.py` | Vendor buy price lookup |
| `credits_checker.py` | Standalone API credits reporter |
| `price-alert.service` | systemd oneshot for scan |
| `price-alert.timer` | systemd timer (8-hour interval) |
| `credits-checker.service` | systemd oneshot for credit check |
| `credits-checker.timer` | systemd timer (2-hour interval) |
| `underbot-bot.service` | systemd long-running bot daemon |
| `install.sh` | Installs all systemd units |
| `run.sh` | Wrapper for manual execution |

## How deal scoring works

Each deal gets a score (0–100) based on four weighted factors:

- **Discount depth** (35%) — how deep the discount is relative to median
- **Absolute profit** (35%) — total gold profit if resold at median price
- **Quantity** (15%) — number of units available
- **Velocity** (15%) — how often the item trades (from price history)

Vendor flips automatically score ≥85.

## Vendor flip detection

Items that can be bought from a vendor and resold on the auction house at a profit are flagged with a `[VENDOR]` tag. The bot checks the Blizzard vendor price for each deal item and scores it as a top priority if profitable.

## Rate limits

| Service | Limit | Cost per scan |
|---|---|---|
| Undermine Exchange | 3,000 points/hour sliding window | 6 points (3 realm + 3 region) + 1 for credit check |
| Blizzard API | generous free tier | Only called for deal items |
| wowtokenprice.com | no key required | 1 call per scan + per `/token` command |
| Telegram API | no meaningful limit | 1 message per deal + digest + credits |

## License

GPL-3.0
