# sphinx_os/revenue/subscriptions.py
import sqlite3
import os
import time

DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")

SUBSCRIPTION_TIERS = {
    "free": {"price_monthly": 0},
    "premium": {"price_monthly": 5},
    "pro": {"price_monthly": 20},
}


class SubscriptionManager:
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
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id TEXT PRIMARY KEY,
                    tier TEXT NOT NULL DEFAULT 'free',
                    started_at REAL NOT NULL,
                    renewed_at REAL NOT NULL
                )
            """)
            conn.commit()

    def upgrade(self, user_id, tier):
        if tier not in SUBSCRIPTION_TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO subscriptions (user_id, tier, started_at, renewed_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, tier, now, now),
            )
            conn.commit()

        return {
            "user_id": user_id,
            "tier": tier,
            "price_monthly": SUBSCRIPTION_TIERS[tier]["price_monthly"],
            "status": "active",
        }

    def get_subscription(self, user_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_stats(self):
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM subscriptions WHERE tier != 'free'"
            ).fetchone()["cnt"]
            premium = conn.execute(
                "SELECT COUNT(*) as cnt FROM subscriptions WHERE tier = 'premium'"
            ).fetchone()["cnt"]
            pro = conn.execute(
                "SELECT COUNT(*) as cnt FROM subscriptions WHERE tier = 'pro'"
            ).fetchone()["cnt"]

        monthly_revenue = (
            premium * SUBSCRIPTION_TIERS["premium"]["price_monthly"]
            + pro * SUBSCRIPTION_TIERS["pro"]["price_monthly"]
        )
        return {
            "active_subscriptions": total,
            "premium_users": premium,
            "pro_users": pro,
            "monthly_revenue": monthly_revenue,
        }

    def get_monthly_revenue(self):
        stats = self.get_stats()
        return stats["monthly_revenue"]
