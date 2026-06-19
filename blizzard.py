from __future__ import annotations

import time
from typing import Any

import requests

TOKEN_URL = "https://oauth.battle.net/token"
ITEM_URL = "https://{region}.api.blizzard.com/data/wow/item/{item_id}"


class BlizzardClient:
    def __init__(
        self, client_id: str, client_secret: str, region: str = "eu"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        if time.time() < self._token_expires_at and self._token:
            return self._token
        resp = requests.post(
            TOKEN_URL,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + body["expires_in"] - 60
        return self._token

    def get_item_info(self, item_id: int) -> dict[str, Any] | None:
        token = self._get_token()
        url = ITEM_URL.format(region=self.region, item_id=item_id)
        resp = requests.get(
            url,
            params={"namespace": "static-eu", "locale": "en_US"},
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        cls = data.get("item_class", {})
        return {
            "name": data.get("name"),
            "class_id": cls.get("id"),
            "class_name": cls.get("name"),
        }
