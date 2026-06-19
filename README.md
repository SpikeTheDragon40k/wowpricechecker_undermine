# Telegram Undermine — WoW Auction House Deal Scanner

Scans the [Undermine Exchange](https://undermine.exchange) API for extreme bargains on a specific WoW realm and sends Telegram alerts when items are priced at a fraction of their regional median.

## How it works

Every 8 hours (via systemd timer), the bot:

1. Fetches **all items currently listed on your realm** — `/v1/realm/:region/:realm/items.json`
2. Fetches **region-wide medians** — `/v1/region/:region/items.json`
3. Cross-references: finds items where the realm price is ≤ X% of the regional median (default: 5%)
4. Filters out **equipment** (weapons/armor — their medians are distorted by item level variations)
5. Resolves item names + classes via **Blizzard API**
6. Sends a **Telegram alert** for each genuine deal
7. Persists state to avoid duplicate alerts on subsequent runs

### Example alert

```
Deal on pozzo-delleternità!
Schematic: Small Seaforium Charge (ID 4409)
Price: 10g 4s 0c
Regional median: 500g 0s 0c
Discount: 97.9% (2.1% of median)
Quantity: 1
```

## Requirements

- Python 3.10+
- An [Undermine Exchange API key](https://undermine.exchange/api.html) (free, requires Patreon login)
- A [Telegram bot token](https://t.me/BotFather) and chat ID
- [Blizzard API credentials](https://develop.battle.net/) (free — enables item names in alerts)

## Setup

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

Fill in your `.env`:

```ini
UNDERMINE_API_KEY=your_undermine_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
REALM=pozzo-delleternità
REGION=eu
PRICE_PERCENT_THRESHOLD=5.0
BLIZZARD_CLIENT_ID=your_blizzard_client_id
BLIZZARD_CLIENT_SECRET=your_blizzard_client_secret
```

### 3. Test

```bash
python3 monitor.py
```

### 4. Schedule (systemd)

```bash
sudo ./install.sh
```

This installs and enables a timer that runs at 00:00, 08:00, 16:00 daily.

### 5. Manual trigger

```bash
sudo systemctl start price-alert.service
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `UNDERMINE_API_KEY` | ✅ | — | API key from Undermine Exchange |
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | — | Your Telegram chat ID |
| `REGION` | — | `eu` | WoW region (`us`, `eu`, `tw`, `kr`) |
| `REALM` | — | `pozzo-delleternità` | Realm slug to scan |
| `PRICE_PERCENT_THRESHOLD` | — | `5.0` | Alert when price ≤ this % of regional median |
| `BLIZZARD_CLIENT_ID` | — | — | Enables item name resolution |
| `BLIZZARD_CLIENT_SECRET` | — | — | Enables item name resolution |
| `STATE_FILE_PATH` | — | `state.json` | Path to persistence file |

## Files

| File | Purpose |
|---|---|
| `monitor.py` | Main entry point — scan, filter, alert |
| `undermine.py` | Undermine Exchange API client |
| `blizzard.py` | Blizzard API client (item names + classes) |
| `telegram_notifier.py` | Telegram message formatting |
| `config.py` | Environment variable loading |
| `state.py` | JSON file persistence |
| `price-alert.service` | systemd oneshot unit |
| `price-alert.timer` | systemd timer (8-hour interval) |
| `install.sh` | Installs systemd units |
| `run.sh` | Wrapper script for manual use |

## How deals are detected

```
deal_score = realm_price / region_median * 100
alert if deal_score ≤ PRICE_PERCENT_THRESHOLD
```

Equipment (item class 2 = Weapon, 4 = Armor) is automatically excluded because their region median is averaged across all item levels, making low-level versions appear as false positives.

## Rate limits

- Undermine Exchange: 3,000 points/hour sliding window
- Each scan costs **6 points** (3 realm items + 3 region summary)
- Blizzard API: generous free tier, only called for deal items

## License

GPL-3.0
