"""SQLite-backed price history tracker."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_NAME = "price_history.db"


class PriceHistory:
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                realm TEXT NOT NULL,
                region TEXT NOT NULL,
                price INTEGER NOT NULL,
                median INTEGER NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                pct_of_median REAL NOT NULL DEFAULT 0.0,
                snapshot_date TEXT NOT NULL,
                UNIQUE(item_id, realm, snapshot_date)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_lookup
                ON price_snapshots(item_id, realm, snapshot_date);

            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                realm TEXT NOT NULL,
                region TEXT NOT NULL,
                deals_found INTEGER NOT NULL DEFAULT 0,
                credits_remaining INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date, realm)
            );
        """)
        self.conn.commit()

    def record_snapshot(
        self,
        item_id: int,
        realm: str,
        region: str,
        price: int,
        median: int,
        quantity: int,
    ) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pct = (price / median * 100.0) if median > 0 else 0.0
        self.conn.execute("""
            INSERT OR REPLACE INTO price_snapshots
                (item_id, realm, region, price, median, quantity, pct_of_median, snapshot_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, realm, region, price, median, quantity, round(pct, 1), today))
        self.conn.commit()

    def record_scan_summary(
        self,
        realm: str,
        region: str,
        deals_found: int,
        credits_remaining: int,
    ) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.conn.execute("""
            INSERT OR REPLACE INTO scan_history
                (date, realm, region, deals_found, credits_remaining)
            VALUES (?, ?, ?, ?, ?)
        """, (today, realm, region, deals_found, credits_remaining))
        self.conn.commit()

    def get_trend(self, item_id: int, realm: str, days: int = 14) -> dict[str, Any]:
        cursor = self.conn.execute("""
            SELECT price, snapshot_date
            FROM price_snapshots
            WHERE item_id = ? AND realm = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
        """, (item_id, realm, days))

        rows = cursor.fetchall()
        if len(rows) < 2:
            return {
                "direction": "unknown",
                "change_pct": 0.0,
                "current_price": rows[0]["price"] if rows else 0,
                "min_price": rows[0]["price"] if rows else 0,
                "max_price": rows[0]["price"] if rows else 0,
                "avg_price": rows[0]["price"] if rows else 0,
                "data_points": len(rows),
            }

        prices = [r["price"] for r in rows]
        first_price = prices[-1]
        last_price = prices[0]

        change_pct = ((last_price - first_price) / first_price) * 100.0 if first_price > 0 else 0.0

        if change_pct > 15:
            direction = "up"
        elif change_pct < -15:
            direction = "down"
        else:
            direction = "flat"

        return {
            "direction": direction,
            "change_pct": round(change_pct, 1),
            "current_price": last_price,
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": round(sum(prices) / len(prices)),
            "data_points": len(rows),
        }

    def get_top_deals_last_days(
        self, realm: str, days: int = 7, limit: int = 10
    ) -> list[dict[str, Any]]:
        cursor = self.conn.execute("""
            SELECT item_id, price, median, quantity, pct_of_median, snapshot_date
            FROM price_snapshots
            WHERE realm = ?
                AND snapshot_date >= date('now', ? || ' days')
                AND median > price
            ORDER BY (median - price) * quantity DESC
            LIMIT ?
        """, (realm, f"-{days}", limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_biggest_drops(
        self, realm: str, days: int = 7, limit: int = 5
    ) -> list[dict[str, Any]]:
        cursor = self.conn.execute("""
            SELECT
                item_id,
                MIN(price) AS min_price,
                MAX(price) AS max_price,
                COUNT(*) AS snapshots
            FROM price_snapshots
            WHERE realm = ?
                AND snapshot_date >= date('now', ? || ' days')
            GROUP BY item_id
            HAVING max_price > min_price * 1.3 AND min_price > 0
            ORDER BY (max_price - min_price) * 100.0 / min_price DESC
            LIMIT ?
        """, (realm, f"-{days}", limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_scan_summary_last_days(
        self, realm: str, days: int = 7
    ) -> list[dict[str, Any]]:
        cursor = self.conn.execute("""
            SELECT date, deals_found, credits_remaining
            FROM scan_history
            WHERE realm = ?
                AND date >= date('now', ? || ' days')
            ORDER BY date DESC
        """, (realm, f"-{days}"))
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self.conn.close()
