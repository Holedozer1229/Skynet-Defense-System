# sphinx_os/wallet/builtin_wallet.py
import hashlib
import os
import random
import string
import sqlite3
import json
import time

DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")

# Simple wordlist for demo mnemonic generation (not BIP39 production-grade)
_WORDLIST = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    "acoustic", "acquire", "across", "action", "actor", "adapt", "add", "address",
    "adjust", "admit", "adult", "advance", "advice", "aerobic", "afford", "afraid",
    "again", "agent", "agree", "ahead", "aim", "air", "airport", "aisle",
    "alarm", "album", "alcohol", "alert", "alien", "all", "alley", "allow",
    "almost", "alone", "alpha", "already", "also", "alter", "always", "amateur",
    "amazing", "among", "amount", "amused", "analyst", "anchor", "ancient", "anger",
    "angle", "angry", "animal", "ankle", "announce", "annual", "another", "answer",
    "antenna", "antique", "anxiety", "apart", "apology", "appear", "apply", "approve",
    "april", "arch", "arctic", "area", "arena", "argue", "arm", "armor",
    "army", "around", "arrange", "arrest", "arrive", "arrow", "art", "artefact",
    "artist", "artwork", "ask", "aspect", "assault", "asset", "assist", "assume",
    "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction",
    "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado",
]


def _generate_private_key():
    return hashlib.sha256(os.urandom(32)).hexdigest()


def _private_key_to_address(private_key):
    pub_key_hash = hashlib.sha256(private_key.encode()).hexdigest()
    short = pub_key_hash[:20]
    return f"0xSPHINX{short.upper()}"


def _generate_mnemonic():
    return " ".join(random.choices(_WORDLIST, k=12))


class BuiltinWallet:
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
                CREATE TABLE IF NOT EXISTS wallets (
                    name TEXT PRIMARY KEY,
                    address TEXT UNIQUE NOT NULL,
                    private_key TEXT NOT NULL,
                    mnemonic TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def create_wallet(self, name):
        private_key = _generate_private_key()
        address = _private_key_to_address(private_key)
        mnemonic = _generate_mnemonic()

        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wallets (name, address, private_key, mnemonic, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, address, private_key, mnemonic, time.time()),
            )
            conn.commit()

        return {
            "name": name,
            "address": address,
            "private_key": private_key,
            "mnemonic": mnemonic,
            "warning": "⚠️ Save your private key and mnemonic securely!",
        }

    def get_wallet_by_name(self, name):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM wallets WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None

    def get_wallet_by_address(self, address):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM wallets WHERE address = ?", (address,)
            ).fetchone()
            return dict(row) if row else None
