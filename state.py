import json
import os
from typing import Any


class State:
    path: str
    data: dict[str, Any]

    def __init__(self, path: str):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        with open(self.path) as f:
            return json.load(f)

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get_watchlist(self) -> list[dict]:
        return self.data.get("watchlist", [])

    def add_to_watchlist(self, item_id: int, name: str = "") -> bool:
        wl = self.get_watchlist()
        if any(e["item_id"] == item_id for e in wl):
            return False
        wl.append({"item_id": item_id, "name": name, "last_price": 0})
        self.data["watchlist"] = wl
        self.save()
        return True

    def remove_from_watchlist(self, item_id: int) -> bool:
        wl = self.get_watchlist()
        before = len(wl)
        self.data["watchlist"] = [e for e in wl if e["item_id"] != item_id]
        self.save()
        return len(self.data["watchlist"]) < before

    def get_scan_counter(self) -> int:
        return self.data.get("scan_counter", 0)

    def increment_scan_counter(self) -> int:
        self.data["scan_counter"] = self.get_scan_counter() + 1
        self.save()
        return self.data["scan_counter"]
