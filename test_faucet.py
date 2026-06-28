#!/usr/bin/env python3
"""
Test script untuk auto-faucet onchain-bot.
Target: Request faucet untuk Sepolia dengan wallet test.
"""
import sys
import os

# Tambahkan path ke onchain-bot
sys.path.insert(0, '/data/data/com.termux/files/home/onchain-bot')

# Import module yang diperlukan
from onchain_bot import BlockchainEngine, Config, log_ok, log_err, log_warn
from decimal import Decimal

# Path config
CONFIG_FILE = '/data/data/com.termux/files/home/onchain-bot/onchain_config.json'

def test_faucet():
    """Test request faucet untuk Sepolia."""
    print("=" * 60)
    print("TEST AUTO-FAUCET ONCHAIN-BOT")
    print("=" * 60)
    
    # Inisialisasi config (load dari file)
    print("\n[1] Load config dari file...")
    try:
        config = Config(CONFIG_FILE)
        log_ok(f"Config dimuat! Chain: {list(config.data['chains'].keys())[:5]}...")
    except Exception as e:
        log_err(f"Gagal load config: {e}")
        return False
    
    # Inisialisasi engine
    print("\n[2] Inisialisasi BlockchainEngine...")
    try:
        engine = BlockchainEngine(config)
        log_ok("BlockchainEngine berjalan!")
    except Exception as e:
        log_err(f"Gagal inisialisasi: {e}")
        return False
    
    # Set chain ke Sepolia
    print("\n[3] Set chain ke Sepolia...")
    try:
        engine.set_chain("Sepolia")
        log_ok(f"Chain: {engine.current_chain} (ID: {engine.chain_id})")
    except Exception as e:
        log_err(f"Gagal set chain: {e}")
        return False
    
    # Wallet test
    wallet_test = {
        "address": "0x3E947a1B809847AA635c88ba1C1C95A14F518268",
        "private_key": ""  # Tidak diperlukan untuk faucet
    }
    
    # Test _request_faucet
    print("\n[4] Test _request_faucet untuk Sepolia...")
    try:
        result = engine._request_faucet("Sepolia", wallet_test["address"])
        if result:
            log_ok("✅ Faucet request SUKSES!")
        else:
            log_warn("⚠️ Faucet request GAGAL (lihat log di atas)")
    except Exception as e:
        log_err(f"❌ Error saat request faucet: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test _ensure_minimum_balance (simulasi low balance)
    print("\n[5] Test _ensure_minimum_balance (simulasi low balance)...")
    try:
        # Coba dengan amount kecil (0.0001 ETH)
        result = engine._ensure_minimum_balance(wallet_test, Decimal("0.0001"))
        if result:
            log_ok("✅ Balance check PASSED (faucet berjalan atau balance cukup)")
        else:
            log_warn("⚠️ Balance check GAGAL (faucet gagal atau bukan testnet)")
    except Exception as e:
        log_err(f"❌ Error saat balance check: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("TEST SELESAI")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_faucet()
    sys.exit(0 if success else 1)
