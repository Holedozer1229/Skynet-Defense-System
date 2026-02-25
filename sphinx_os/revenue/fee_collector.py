# sphinx_os/revenue/fee_collector.py
import sqlite3
import os
import time

DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")


class FeeCollector:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fee_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_id TEXT NOT NULL,
                    fee_amount REAL NOT NULL,
                    collected_at REAL NOT NULL
                )
            """)
            conn.commit()

    def record_fee(self, tx_id, fee_amount):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO fee_collections (tx_id, fee_amount, collected_at) VALUES (?, ?, ?)",
                (tx_id, fee_amount, time.time()),
            )
            conn.commit()

    def get_today_fees(self):
        start_of_day = time.time() - (time.time() % 86400)
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(fee_amount), 0) as total FROM fee_collections WHERE collected_at >= ?",
                (start_of_day,),
            ).fetchone()
            return float(row["total"])

    def get_total_fees(self):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(fee_amount), 0) as total FROM fee_collections"
            ).fetchone()
            return float(row["total"])
