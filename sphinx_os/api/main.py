# sphinx_os/api/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from ..blockchain.standalone import SphinxSkynetBlockchain
from ..blockchain.transaction import Transaction, TRANSACTION_FEE
from ..wallet.builtin_wallet import BuiltinWallet
from ..mining.free_miner import FreeMiner
from ..revenue.fee_collector import FeeCollector
from ..revenue.subscriptions import SubscriptionManager
from ..revenue.referrals import ReferralProgram

DB_PATH = os.environ.get("SPHINX_DB_PATH", "sphinxskynet.db")

app = FastAPI(
    title="SphinxSkynet Gasless Blockchain API",
    description="100% Free, Standalone Blockchain with NO Gas Fees!",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
blockchain = SphinxSkynetBlockchain(DB_PATH)
wallet_manager = BuiltinWallet(DB_PATH)
miner = FreeMiner(DB_PATH)
fee_collector = FeeCollector(DB_PATH)
subscription_manager = SubscriptionManager(DB_PATH)
referral_program = ReferralProgram(DB_PATH)


# ──────────────────────────── Request models ────────────────────────────

class CreateWalletRequest(BaseModel):
    name: str


class StartMiningRequest(BaseModel):
    address: str
    tier: Optional[str] = "free"


class SendTransactionRequest(BaseModel):
    from_address: str
    to_address: str
    amount: float
    private_key: str


class UpgradeSubscriptionRequest(BaseModel):
    user_id: str
    tier: str


class ReferralSignupRequest(BaseModel):
    user_id: str
    referral_code: str


# ──────────────────────────── Health / Info ────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "blockchain": "SphinxSkynet", "token": "SPHINX"}


@app.get("/api/blockchain/info")
def blockchain_info():
    return blockchain.get_info()


# ──────────────────────────── Wallet ────────────────────────────

@app.post("/api/wallet/create")
def create_wallet(req: CreateWalletRequest):
    wallet = wallet_manager.create_wallet(req.name)
    return {"success": True, "wallet": wallet}


@app.get("/api/wallet/{address}/balance")
def get_balance(address: str):
    balance = blockchain.get_balance(address)
    return {"address": address, "balance": balance, "token": "SPHINX"}


# ──────────────────────────── Mining ────────────────────────────

@app.post("/api/mining/start")
def start_mining(req: StartMiningRequest):
    try:
        result = miner.start_mining(req.address, req.tier)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/mining/mine-block")
def mine_block(address: str = Query(...)):
    try:
        result = miner.mine_block(address, blockchain)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ──────────────────────────── Transactions ────────────────────────────

@app.post("/api/transaction/send")
def send_transaction(req: SendTransactionRequest):
    try:
        tx = Transaction(
            from_address=req.from_address,
            to_address=req.to_address,
            amount=req.amount,
            fee=TRANSACTION_FEE,
        )
        tx.sign(req.private_key)
        tx_id = blockchain.add_transaction(tx)
        fee_collector.record_fee(tx_id, TRANSACTION_FEE)
        return {
            "success": True,
            "tx_id": tx_id,
            "fee": TRANSACTION_FEE,
            "message": "Transaction added to pending pool.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ──────────────────────────── Subscriptions ────────────────────────────

@app.post("/api/subscription/upgrade")
def upgrade_subscription(req: UpgradeSubscriptionRequest):
    try:
        result = subscription_manager.upgrade(req.user_id, req.tier)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ──────────────────────────── Referrals ────────────────────────────

@app.get("/api/referral/{user_id}/code")
def get_referral_code(user_id: str):
    code = referral_program.get_or_create_code(user_id)
    return {"user_id": user_id, "referral_code": code}


@app.post("/api/referral/signup")
def referral_signup(req: ReferralSignupRequest):
    try:
        result = referral_program.signup_with_referral(req.user_id, req.referral_code)
        return {"success": True, **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ──────────────────────────── Admin / Revenue ────────────────────────────

@app.get("/api/admin/revenue/today")
def revenue_today():
    today_fees = fee_collector.get_today_fees()
    sub_revenue = subscription_manager.get_monthly_revenue()
    return {
        "transaction_fees": today_fees,
        "subscription_revenue": sub_revenue,
        "total_revenue": today_fees + sub_revenue,
    }


@app.get("/api/admin/revenue/total")
def revenue_total():
    total_fees = fee_collector.get_total_fees()
    sub_revenue = subscription_manager.get_monthly_revenue()
    return {
        "transaction_fees": total_fees,
        "subscription_revenue": sub_revenue,
        "total_revenue": total_fees + sub_revenue,
    }


@app.get("/api/admin/revenue/stats")
def revenue_stats():
    today_fees = fee_collector.get_today_fees()
    total_fees = fee_collector.get_total_fees()
    sub_stats = subscription_manager.get_stats()
    ref_stats = referral_program.get_stats()
    sub_revenue = sub_stats["monthly_revenue"]

    return {
        "revenue": {
            "today": {
                "transaction_fees": today_fees,
                "subscription_revenue": sub_revenue,
                "total_revenue": today_fees + sub_revenue,
            },
            "total": {
                "transaction_fees": total_fees,
                "subscription_revenue": sub_revenue,
                "total_revenue": total_fees + sub_revenue,
            },
        },
        "subscriptions": sub_stats,
        "referrals": ref_stats,
    }
