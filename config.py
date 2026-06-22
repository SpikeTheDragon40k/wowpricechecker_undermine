import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    undermine_api_key: str
    blizzard_client_id: str | None
    blizzard_client_secret: str | None
    telegram_bot_token: str
    telegram_chat_id: str
    region: str
    realms: list[str]
    price_percent_threshold: float
    state_file_path: str
    price_history_db: str
    focus_classes: set[int] | None
    exclude_classes: set[int]
    score_weights: dict[str, float]
    trend_report_interval: int
    trend_report_day: str
    telegram_poll_interval: int

    def __init__(self):
        self.undermine_api_key = self._require("UNDERMINE_API_KEY")
        self.telegram_bot_token = self._require("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = self._require("TELEGRAM_CHAT_ID")

        self.blizzard_client_id = os.getenv("BLIZZARD_CLIENT_ID")
        self.blizzard_client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")

        self.region = os.getenv("REGION", "eu")

        realms_raw = os.getenv("REALMS")
        if realms_raw:
            self.realms = [r.strip() for r in realms_raw.split(",") if r.strip()]
        else:
            single = os.getenv("REALM", "pozzo-delleternità")
            self.realms = [single]

        pct = os.getenv("PRICE_PERCENT_THRESHOLD")
        self.price_percent_threshold = float(pct) if pct else 5.0

        self.state_file_path = os.getenv("STATE_FILE_PATH", "state.json")
        self.price_history_db = os.getenv("PRICE_HISTORY_DB", "price_history.db")

        focus_raw = os.getenv("FOCUS_CLASSES")
        if focus_raw:
            self.focus_classes = {
                int(x.strip()) for x in focus_raw.split(",") if x.strip()
            }
        else:
            self.focus_classes = None

        exclude_raw = os.getenv("EXCLUDE_CLASSES")
        if exclude_raw:
            self.exclude_classes = {
                int(x.strip()) for x in exclude_raw.split(",") if x.strip()
            }
        else:
            self.exclude_classes = {2, 4}

        weights_raw = os.getenv("SCORE_WEIGHTS")
        if weights_raw:
            parts = [float(x) for x in weights_raw.split() if x]
            if len(parts) == 4:
                self.score_weights = {
                    "discount_depth": parts[0],
                    "absolute_profit": parts[1],
                    "quantity": parts[2],
                    "velocity": parts[3],
                }
            else:
                self.score_weights = {
                    "discount_depth": 0.35,
                    "absolute_profit": 0.35,
                    "quantity": 0.15,
                    "velocity": 0.15,
                }
        else:
            self.score_weights = {
                "discount_depth": 0.35,
                "absolute_profit": 0.35,
                "quantity": 0.15,
                "velocity": 0.15,
            }

        interval_raw = os.getenv("TREND_REPORT_INTERVAL")
        self.trend_report_interval = int(interval_raw) if interval_raw else 7
        self.trend_report_day = os.getenv("TREND_REPORT_DAY", "monday").lower()

        poll_raw = os.getenv("TELEGRAM_POLL_INTERVAL")
        self.telegram_poll_interval = int(poll_raw) if poll_raw else 30

    @staticmethod
    def _require(name: str) -> str:
        val = os.getenv(name)
        if not val:
            raise ValueError(
                f"Missing required environment variable: {name}"
            )
        return val
