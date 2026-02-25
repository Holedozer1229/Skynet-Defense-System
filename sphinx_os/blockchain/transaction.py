# sphinx_os/blockchain/transaction.py
import hashlib
import json
import time


TRANSACTION_FEE = 0.001  # SPHINX per transaction


class Transaction:
    def __init__(self, from_address, to_address, amount, fee=TRANSACTION_FEE, signature=None):
        self.from_address = from_address
        self.to_address = to_address
        self.amount = amount
        self.fee = fee
        self.signature = signature
        self.timestamp = time.time()
        self.tx_id = self._generate_id()

    def _generate_id(self):
        data = f"{self.from_address}{self.to_address}{self.amount}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "amount": self.amount,
            "fee": self.fee,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    def sign(self, private_key):
        data = f"{self.from_address}{self.to_address}{self.amount}"
        self.signature = hashlib.sha256(f"{data}{private_key}".encode()).hexdigest()

    def verify_signature(self, private_key):
        data = f"{self.from_address}{self.to_address}{self.amount}"
        expected = hashlib.sha256(f"{data}{private_key}".encode()).hexdigest()
        return self.signature == expected
