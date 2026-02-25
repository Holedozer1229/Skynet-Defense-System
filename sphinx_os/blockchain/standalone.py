# sphinx_os/blockchain/standalone.py
import sqlite3
import json
import time
import os

from .block import Block
from .transaction import Transaction, TRANSACTION_FEE

DIFFICULTY = 4
MINING_REWARD = 50.0  # SPHINX tokens per block
DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")


class SphinxSkynetBlockchain:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.difficulty = DIFFICULTY
        self.mining_reward = MINING_REWARD
        self.pending_transactions = []
        self._init_db()
        if self.get_chain_length() == 0:
            self._create_genesis_block()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_index INTEGER UNIQUE,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS balances (
                    address TEXT PRIMARY KEY,
                    balance REAL NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def _create_genesis_block(self):
        genesis = Block(0, [], "0" * 64)
        genesis.hash = genesis.calculate_hash()
        self._save_block(genesis)

    def _save_block(self, block):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO blocks (block_index, data, created_at) VALUES (?, ?, ?)",
                (block.index, json.dumps(block.to_dict()), time.time()),
            )
            conn.commit()

    def get_chain_length(self):
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM blocks").fetchone()
            return row["cnt"]

    def get_latest_block(self):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM blocks ORDER BY block_index DESC LIMIT 1"
            ).fetchone()
            if row:
                data = json.loads(row["data"])
                block = Block(
                    data["index"],
                    data["transactions"],
                    data["previous_hash"],
                    data["nonce"],
                    data["timestamp"],
                )
                block.hash = data["hash"]
                return block
        return None

    def mine_pending_transactions(self, mining_reward_address):
        reward_tx = Transaction("SYSTEM", mining_reward_address, self.mining_reward, fee=0)
        self.pending_transactions.append(reward_tx.to_dict())

        latest = self.get_latest_block()
        new_block = Block(
            latest.index + 1,
            self.pending_transactions[:],
            latest.hash,
        )
        self._proof_of_work(new_block)
        self._save_block(new_block)

        # Update balances
        for tx_data in self.pending_transactions:
            self._apply_transaction(tx_data)

        self.pending_transactions = []
        return new_block

    def _proof_of_work(self, block):
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash = block.calculate_hash()
        return block

    def _apply_transaction(self, tx_data):
        with self._get_conn() as conn:
            from_addr = tx_data.get("from_address")
            to_addr = tx_data.get("to_address")
            amount = tx_data.get("amount", 0)
            fee = tx_data.get("fee", 0)

            if from_addr and from_addr != "SYSTEM":
                conn.execute(
                    "INSERT INTO balances (address, balance) VALUES (?, 0) ON CONFLICT(address) DO NOTHING",
                    (from_addr,),
                )
                conn.execute(
                    "UPDATE balances SET balance = balance - ? WHERE address = ?",
                    (amount + fee, from_addr),
                )

            if to_addr:
                conn.execute(
                    "INSERT INTO balances (address, balance) VALUES (?, 0) ON CONFLICT(address) DO NOTHING",
                    (to_addr,),
                )
                conn.execute(
                    "UPDATE balances SET balance = balance + ? WHERE address = ?",
                    (amount, to_addr),
                )

            conn.commit()

    def get_balance(self, address):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT balance FROM balances WHERE address = ?", (address,)
            ).fetchone()
            return row["balance"] if row else 0.0

    def add_transaction(self, transaction):
        if transaction.from_address != "SYSTEM":
            balance = self.get_balance(transaction.from_address)
            total_cost = transaction.amount + transaction.fee
            if balance < total_cost:
                raise ValueError(
                    f"Insufficient balance: {balance} < {total_cost}"
                )
        self.pending_transactions.append(transaction.to_dict())
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO transactions (tx_id, data, created_at) VALUES (?, ?, ?)",
                (transaction.tx_id, json.dumps(transaction.to_dict()), time.time()),
            )
            conn.commit()
        return transaction.tx_id

    def get_info(self):
        return {
            "chain_length": self.get_chain_length(),
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "pending_transactions": len(self.pending_transactions),
            "token": "SPHINX",
        }
