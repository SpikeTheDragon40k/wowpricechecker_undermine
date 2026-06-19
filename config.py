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
    realm: str
    price_percent_threshold: float
    state_file_path: str

    def __init__(self):
        self.undermine_api_key = self._require("UNDERMINE_API_KEY")
        self.blizzard_client_id = os.getenv("BLIZZARD_CLIENT_ID")
        self.blizzard_client_secret = os.getenv("BLIZZARD_CLIENT_SECRET")
        self.telegram_bot_token = self._require("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = self._require("TELEGRAM_CHAT_ID")
        self.region = os.getenv("REGION", "eu")
        self.realm = os.getenv("REALM", "pozzo-delleternità")
        pct = os.getenv("PRICE_PERCENT_THRESHOLD")
        self.price_percent_threshold = float(pct) if pct else 5.0
        self.state_file_path = os.getenv(
            "STATE_FILE_PATH", "state.json"
        )

    @staticmethod
    def _require(name: str) -> str:
        val = os.getenv(name)
        if not val:
            raise ValueError(
                f"Missing required environment variable: {name}"
            )
        return val
