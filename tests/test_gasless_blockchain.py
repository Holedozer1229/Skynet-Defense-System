"""Tests for the SphinxSkynet Gasless Blockchain system."""
import os
import tempfile
import pytest

# Use a temporary database for tests
@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_sphinx.db")
    monkeypatch.setenv("SPHINX_DB_PATH", db_file)
    yield db_file


# ──────────────────────────── Blockchain tests ────────────────────────────

def test_blockchain_genesis_block():
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)
    assert chain.get_chain_length() == 1
    genesis = chain.get_latest_block()
    assert genesis.index == 0
    assert genesis.previous_hash == "0" * 64


def test_blockchain_info():
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)
    info = chain.get_info()
    assert info["token"] == "SPHINX"
    assert info["chain_length"] == 1
    assert info["difficulty"] >= 1


def test_mine_pending_transactions():
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)
    miner_address = "0xSPHINXTEST001"
    block = chain.mine_pending_transactions(miner_address)
    assert block.index == 1
    assert block.hash.startswith("0" * chain.difficulty)
    assert chain.get_balance(miner_address) == chain.mining_reward


def test_add_and_mine_transaction():
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    from sphinx_os.blockchain.transaction import Transaction
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)

    # Give sender some funds first
    sender = "0xSPHINXSENDER"
    receiver = "0xSPHINXRECEIVER"
    chain.mine_pending_transactions(sender)

    tx = Transaction(sender, receiver, 10.0)
    tx.sign("test_private_key")
    tx_id = chain.add_transaction(tx)
    assert len(tx_id) == 64

    chain.mine_pending_transactions(sender)
    assert chain.get_balance(receiver) == 10.0


def test_insufficient_balance_raises():
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    from sphinx_os.blockchain.transaction import Transaction
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)
    tx = Transaction("0xBROKE", "0xRICH", 9999.0)
    tx.sign("key")
    with pytest.raises(ValueError, match="Insufficient balance"):
        chain.add_transaction(tx)


# ──────────────────────────── Block tests ────────────────────────────

def test_block_hash_changes_with_nonce():
    from sphinx_os.blockchain.block import Block
    block = Block(1, [], "abc123")
    hash1 = block.calculate_hash()
    block.nonce = 1
    hash2 = block.calculate_hash()
    assert hash1 != hash2


def test_block_to_dict():
    from sphinx_os.blockchain.block import Block
    block = Block(0, [], "0" * 64)
    d = block.to_dict()
    assert "hash" in d
    assert d["index"] == 0


# ──────────────────────────── Transaction tests ────────────────────────────

def test_transaction_sign_and_verify():
    from sphinx_os.blockchain.transaction import Transaction
    tx = Transaction("0xA", "0xB", 5.0)
    tx.sign("secret_key")
    assert tx.verify_signature("secret_key")
    assert not tx.verify_signature("wrong_key")


def test_transaction_fee_default():
    from sphinx_os.blockchain.transaction import Transaction, TRANSACTION_FEE
    tx = Transaction("0xA", "0xB", 1.0)
    assert tx.fee == TRANSACTION_FEE


# ──────────────────────────── Wallet tests ────────────────────────────

def test_create_wallet():
    from sphinx_os.wallet.builtin_wallet import BuiltinWallet
    db = os.environ["SPHINX_DB_PATH"]
    w = BuiltinWallet(db)
    result = w.create_wallet("test_wallet")
    assert result["name"] == "test_wallet"
    assert result["address"].startswith("0xSPHINX")
    assert len(result["private_key"]) == 64
    assert len(result["mnemonic"].split()) == 12
    assert "warning" in result


def test_get_wallet_by_name():
    from sphinx_os.wallet.builtin_wallet import BuiltinWallet
    db = os.environ["SPHINX_DB_PATH"]
    w = BuiltinWallet(db)
    w.create_wallet("alice")
    wallet = w.get_wallet_by_name("alice")
    assert wallet is not None
    assert wallet["name"] == "alice"


def test_get_wallet_by_address():
    from sphinx_os.wallet.builtin_wallet import BuiltinWallet
    db = os.environ["SPHINX_DB_PATH"]
    w = BuiltinWallet(db)
    created = w.create_wallet("bob")
    wallet = w.get_wallet_by_address(created["address"])
    assert wallet["address"] == created["address"]


# ──────────────────────────── Mining tests ────────────────────────────

def test_start_mining():
    from sphinx_os.mining.free_miner import FreeMiner
    db = os.environ["SPHINX_DB_PATH"]
    m = FreeMiner(db)
    result = m.start_mining("0xMINER1", "free")
    assert result["tier"] == "free"
    assert result["hashrate_mhs"] == 10
    assert result["status"] == "mining"


def test_start_mining_invalid_tier():
    from sphinx_os.mining.free_miner import FreeMiner
    db = os.environ["SPHINX_DB_PATH"]
    m = FreeMiner(db)
    with pytest.raises(ValueError):
        m.start_mining("0xMINER1", "invalid_tier")


def test_mine_block_via_miner():
    from sphinx_os.mining.free_miner import FreeMiner
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)
    m = FreeMiner(db)
    address = "0xMINERTEST"
    m.start_mining(address, "free")
    result = m.mine_block(address, chain)
    assert result["block_index"] == 1
    assert result["reward"] == chain.mining_reward


def test_mine_block_without_start_raises():
    from sphinx_os.mining.free_miner import FreeMiner
    from sphinx_os.blockchain.standalone import SphinxSkynetBlockchain
    db = os.environ["SPHINX_DB_PATH"]
    chain = SphinxSkynetBlockchain(db)
    m = FreeMiner(db)
    with pytest.raises(ValueError, match="not registered"):
        m.mine_block("0xUNREGISTERED", chain)


# ──────────────────────────── Revenue tests ────────────────────────────

def test_fee_collector():
    from sphinx_os.revenue.fee_collector import FeeCollector
    db = os.environ["SPHINX_DB_PATH"]
    fc = FeeCollector(db)
    fc.record_fee("tx001", 0.001)
    fc.record_fee("tx002", 0.001)
    assert fc.get_total_fees() == pytest.approx(0.002)


def test_subscription_upgrade():
    from sphinx_os.revenue.subscriptions import SubscriptionManager
    db = os.environ["SPHINX_DB_PATH"]
    sm = SubscriptionManager(db)
    result = sm.upgrade("user1", "premium")
    assert result["tier"] == "premium"
    assert result["price_monthly"] == 5


def test_subscription_invalid_tier():
    from sphinx_os.revenue.subscriptions import SubscriptionManager
    db = os.environ["SPHINX_DB_PATH"]
    sm = SubscriptionManager(db)
    with pytest.raises(ValueError):
        sm.upgrade("user1", "platinum")


def test_subscription_stats():
    from sphinx_os.revenue.subscriptions import SubscriptionManager
    db = os.environ["SPHINX_DB_PATH"]
    sm = SubscriptionManager(db)
    sm.upgrade("u1", "premium")
    sm.upgrade("u2", "pro")
    stats = sm.get_stats()
    assert stats["premium_users"] == 1
    assert stats["pro_users"] == 1
    assert stats["monthly_revenue"] == 25  # 5 + 20


def test_referral_code_generation():
    from sphinx_os.revenue.referrals import ReferralProgram
    db = os.environ["SPHINX_DB_PATH"]
    rp = ReferralProgram(db)
    code = rp.get_or_create_code("user_abc")
    assert len(code) == 8
    # Calling again returns the same code
    assert rp.get_or_create_code("user_abc") == code


def test_referral_signup():
    from sphinx_os.revenue.referrals import ReferralProgram
    db = os.environ["SPHINX_DB_PATH"]
    rp = ReferralProgram(db)
    code = rp.get_or_create_code("referrer1")
    result = rp.signup_with_referral("new_user", code)
    assert result["referrer_id"] == "referrer1"
    assert result["commission_rate"] == 0.05


def test_referral_self_signup_raises():
    from sphinx_os.revenue.referrals import ReferralProgram
    db = os.environ["SPHINX_DB_PATH"]
    rp = ReferralProgram(db)
    code = rp.get_or_create_code("self_user")
    with pytest.raises(ValueError, match="Cannot refer yourself"):
        rp.signup_with_referral("self_user", code)


def test_referral_invalid_code_raises():
    from sphinx_os.revenue.referrals import ReferralProgram
    db = os.environ["SPHINX_DB_PATH"]
    rp = ReferralProgram(db)
    with pytest.raises(ValueError, match="Invalid referral code"):
        rp.signup_with_referral("someone", "BADCODE1")


# ──────────────────────────── API tests ────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "api_test.db")
    monkeypatch.setenv("SPHINX_DB_PATH", db_file)
    # Re-import to get fresh instances with the new DB path
    import importlib
    import sphinx_os.api.main as api_main
    importlib.reload(api_main)
    from fastapi.testclient import TestClient
    return TestClient(api_main.app)


def test_api_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_blockchain_info(client):
    resp = client.get("/api/blockchain/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == "SPHINX"


def test_api_create_wallet(client):
    resp = client.post("/api/wallet/create", json={"name": "mywallet"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["wallet"]["address"].startswith("0xSPHINX")


def test_api_get_balance(client):
    resp = client.get("/api/wallet/0xSPHINXTEST/balance")
    assert resp.status_code == 200
    assert resp.json()["balance"] == 0.0


def test_api_start_mining(client):
    resp = client.post("/api/mining/start", json={"address": "0xSPHINXMINER", "tier": "free"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_api_mine_block(client):
    # Register miner first
    client.post("/api/mining/start", json={"address": "0xSPHINXMINER2", "tier": "free"})
    resp = client.post("/api/mining/mine-block?address=0xSPHINXMINER2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["block_index"] == 1


def test_api_send_transaction(client):
    # Mine to get funds
    client.post("/api/mining/start", json={"address": "0xSPHINXSENDER2", "tier": "free"})
    client.post("/api/mining/mine-block?address=0xSPHINXSENDER2")
    # Get private key
    wc = client.post("/api/wallet/create", json={"name": "sender_wallet"})
    wallet = wc.json()["wallet"]

    # First mine a reward to the wallet address
    client.post("/api/mining/start", json={"address": wallet["address"], "tier": "free"})
    client.post(f"/api/mining/mine-block?address={wallet['address']}")

    resp = client.post(
        "/api/transaction/send",
        json={
            "from_address": wallet["address"],
            "to_address": "0xSPHINXRECEIVER2",
            "amount": 1.0,
            "private_key": wallet["private_key"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_api_subscription_upgrade(client):
    resp = client.post(
        "/api/subscription/upgrade", json={"user_id": "user_test", "tier": "premium"}
    )
    assert resp.status_code == 200
    assert resp.json()["tier"] == "premium"


def test_api_referral_code(client):
    resp = client.get("/api/referral/user123/code")
    assert resp.status_code == 200
    assert "referral_code" in resp.json()


def test_api_referral_signup(client):
    code_resp = client.get("/api/referral/referrer_api/code")
    code = code_resp.json()["referral_code"]
    resp = client.post(
        "/api/referral/signup", json={"user_id": "new_api_user", "referral_code": code}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_api_revenue_stats(client):
    resp = client.get("/api/admin/revenue/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue" in data
    assert "subscriptions" in data
    assert "referrals" in data
