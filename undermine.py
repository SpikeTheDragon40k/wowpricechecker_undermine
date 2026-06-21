from __future__ import annotations

import time
from typing import Any

import requests

BASE_URL = "https://api.undermine.exchange"
REALMS_URL = f"{BASE_URL}/v1/static/realms.json"
NOW_URL = f"{BASE_URL}/v1/region/{{region}}/items/{{item_id}}/now.json"
DAILY_URL = f"{BASE_URL}/v1/region/{{region}}/items/{{item_id}}/daily.json"
REALM_ITEMS_URL = f"{BASE_URL}/v1/realm/{{region}}/{{realm}}/items.json"
REGION_ITEMS_URL = f"{BASE_URL}/v1/region/{{region}}/items.json"

CURRENT_ITEM_COST = 3
DAILY_ITEM_COST = 5
REALM_ITEMS_COST = 3
REGION_ITEMS_COST = 3


class UndermineClient:
    def __init__(self, api_key: str, user_agent: str = "underbot/1.0"):
        self.api_key = api_key
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"ApiKey {self.api_key}",
                "Accept-Encoding": "gzip",
                "User-Agent": self.user_agent,
            }
        )

    def _get(
        self, url: str, retries: int = 3, backoff: float = 2.0
    ) -> dict[str, Any]:
        last_exc = None
        for attempt in range(retries):
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 429:
                    wait = backoff * (2**attempt)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                last_exc = e
                if attempt < retries - 1:
                    time.sleep(backoff * (2**attempt))
        raise RuntimeError(
            f"Undermine API request failed after {retries} retries"
        ) from last_exc

    def get_realms(self) -> list[dict[str, Any]]:
        data = self._get(REALMS_URL)
        return data.get("result", {}).get("realms", [])

    def check_credits(self) -> tuple[int, int]:
        resp = self.session.get(REALMS_URL, timeout=30)
        resp.raise_for_status()
        remaining = int(resp.headers.get("ratelimit-remaining", 0))
        limit = int(resp.headers.get("ratelimit-limit", 0))
        return remaining, limit

    def get_item_now(
        self, region: str, item_id: int
    ) -> list[dict[str, Any]]:
        url = NOW_URL.format(region=region, item_id=item_id)
        data = self._get(url)
        return data.get("result", [])

    def get_item_daily(
        self, region: str, item_id: int
    ) -> list[dict[str, Any]]:
        url = DAILY_URL.format(region=region, item_id=item_id)
        data = self._get(url)
        return data.get("result", {}).get("daily", [])

    def get_realm_items(
        self, region: str, realm: str
    ) -> dict[str, Any]:
        url = REALM_ITEMS_URL.format(region=region, realm=realm)
        data = self._get(url)
        return data.get("result", {}).get("items", {})

    def get_region_items(
        self, region: str
    ) -> dict[str, Any]:
        data = self._get(REGION_ITEMS_URL.format(region=region))
        return data.get("result", {}).get("items", {})

    def cost_points(self, endpoint: str) -> int:
        if "now.json" in endpoint:
            return CURRENT_ITEM_COST
        if "daily.json" in endpoint:
            return DAILY_ITEM_COST
        return 0
