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
