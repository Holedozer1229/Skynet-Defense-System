# sphinx_os/mining/free_miner.py
import sqlite3
import os
import time

DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")

MINING_TIERS = {
    "free": {"hashrate_mhs": 10, "cost_monthly": 0, "daily_limit": 1000},
    "premium": {"hashrate_mhs": 100, "cost_monthly": 5, "daily_limit": 10000},
    "pro": {"hashrate_mhs": 1000, "cost_monthly": 20, "daily_limit": None},
}


class FreeMiner:
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
                CREATE TABLE IF NOT EXISTS miners (
                    address TEXT PRIMARY KEY,
                    tier TEXT NOT NULL DEFAULT 'free',
                    started_at REAL NOT NULL,
                    daily_mined REAL NOT NULL DEFAULT 0,
                    last_reset REAL NOT NULL
                )
            """)
            conn.commit()

    def start_mining(self, address, tier="free"):
        if tier not in MINING_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Choose from {list(MINING_TIERS.keys())}")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO miners (address, tier, started_at, daily_mined, last_reset) "
                "VALUES (?, ?, ?, 0, ?)",
                (address, tier, time.time(), time.time()),
            )
            conn.commit()

        tier_info = MINING_TIERS[tier]
        return {
            "address": address,
            "tier": tier,
            "hashrate_mhs": tier_info["hashrate_mhs"],
            "daily_limit": tier_info["daily_limit"],
            "cost_monthly": tier_info["cost_monthly"],
            "status": "mining",
        }

    def mine_block(self, address, blockchain):
        miner = self._get_miner(address)
        if not miner:
            raise ValueError(f"Miner not registered. Call start_mining first.")

        tier_info = MINING_TIERS[miner["tier"]]
        daily_limit = tier_info["daily_limit"]

        # Reset daily counter if it's a new day
        last_reset = miner["last_reset"]
        if time.time() - last_reset > 86400:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE miners SET daily_mined = 0, last_reset = ? WHERE address = ?",
                    (time.time(), address),
                )
                conn.commit()
            miner["daily_mined"] = 0

        if daily_limit is not None and miner["daily_mined"] >= daily_limit:
            raise ValueError(
                f"Daily mining limit reached ({daily_limit} SPHINX). Upgrade to increase limit."
            )

        block = blockchain.mine_pending_transactions(address)
        reward = blockchain.mining_reward

        with self._get_conn() as conn:
            conn.execute(
                "UPDATE miners SET daily_mined = daily_mined + ? WHERE address = ?",
                (reward, address),
            )
            conn.commit()

        return {
            "block_index": block.index,
            "block_hash": block.hash,
            "reward": reward,
            "address": address,
        }

    def _get_miner(self, address):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM miners WHERE address = ?", (address,)
            ).fetchone()
            return dict(row) if row else None

    def get_miner_status(self, address):
        miner = self._get_miner(address)
        if not miner:
            return None
        tier_info = MINING_TIERS[miner["tier"]]
        return {**miner, **tier_info}
