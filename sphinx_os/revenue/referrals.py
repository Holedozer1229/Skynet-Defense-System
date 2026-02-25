# sphinx_os/revenue/referrals.py
import sqlite3
import os
import hashlib
import time

DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")

REFERRAL_COMMISSION_RATE = 0.05  # 5%


class ReferralProgram:
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
                CREATE TABLE IF NOT EXISTS referral_codes (
                    user_id TEXT PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id TEXT NOT NULL,
                    referred_id TEXT NOT NULL,
                    commission_paid REAL NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def get_or_create_code(self, user_id):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT code FROM referral_codes WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                return row["code"]

            code = hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()[:8].upper()
            conn.execute(
                "INSERT INTO referral_codes (user_id, code, created_at) VALUES (?, ?, ?)",
                (user_id, code, time.time()),
            )
            conn.commit()
            return code

    def signup_with_referral(self, user_id, referral_code):
        with self._get_conn() as conn:
            referrer = conn.execute(
                "SELECT user_id FROM referral_codes WHERE code = ?", (referral_code,)
            ).fetchone()

            if not referrer:
                raise ValueError(f"Invalid referral code: {referral_code}")

            referrer_id = referrer["user_id"]
            if referrer_id == user_id:
                raise ValueError("Cannot refer yourself.")

            conn.execute(
                "INSERT INTO referrals (referrer_id, referred_id, commission_paid, created_at) "
                "VALUES (?, ?, 0, ?)",
                (referrer_id, user_id, time.time()),
            )
            conn.commit()

        return {
            "user_id": user_id,
            "referrer_id": referrer_id,
            "commission_rate": REFERRAL_COMMISSION_RATE,
            "status": "registered",
        }

    def pay_commission(self, referred_id, earnings):
        commission = earnings * REFERRAL_COMMISSION_RATE
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE referrals SET commission_paid = commission_paid + ? WHERE referred_id = ?",
                (commission, referred_id),
            )
            conn.commit()
        return commission

    def get_stats(self):
        with self._get_conn() as conn:
            total_referrals = conn.execute(
                "SELECT COUNT(*) as cnt FROM referrals"
            ).fetchone()["cnt"]
            total_commission = conn.execute(
                "SELECT COALESCE(SUM(commission_paid), 0) as total FROM referrals"
            ).fetchone()["total"]

        return {
            "total_referrals": total_referrals,
            "total_commission_paid": float(total_commission),
        }
