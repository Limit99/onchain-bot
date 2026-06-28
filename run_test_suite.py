#!/usr/bin/env python3
"""Full testnet suite runner: balance check -> send -> swap.
Operator: Hermes. Wallet testnet farming."""
import json, time, sys, os, secrets, traceback
from datetime import datetime
from web3 import Web3
from eth_account import Account

CONFIG = json.load(open('onchain_config.json'))
WALLET = CONFIG['wallets'][0]
ADDR = Web3.to_checksum_address(WALLET['address'])
PK = WALLET['private_key']

# Sepolia ALCHEMY placeholder fix - use public RPC
SEPOLIA_PUBLIC = "https://ethereum-sepolia-rpc.publicnode.com"

def get_rpc(chain_name, chain_cfg):
    rpc = chain_cfg.get('rpc', '')
    if 'ALCHEMY' in rpc or not rpc.startswith('http'):
        if chain_name == 'Sepolia':
            return SEPOLIA_PUBLIC
        return None
    return rpc

def connect(chain_name, chain_cfg, timeout=15):
    rpc = get_rpc(chain_name, chain_cfg)
    if not rpc:
        return None, f"no valid rpc"
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': timeout}))
        if not w3.is_connected():
            return None, "not connected"
        return w3, None
    except Exception as e:
        return None, str(e)[:80]

def get_balance(chain_name, chain_cfg):
    w3, err = connect(chain_name, chain_cfg)
    if err:
        return None, err
    try:
        bal_wei = w3.eth.get_balance(ADDR)
        bal_eth = w3.from_wei(bal_wei, 'ether')
        return float(bal_eth), None
    except Exception as e:
        return None, str(e)[:80]

def main_balance():
    testnets = {n:v for n,v in CONFIG['chains'].items() if v.get('type')=='testnet'}
    results = {}
    print(f"🔍 Cek saldo {ADDR}")
    print(f"   di {len(testnets)} chain testnet\n")
    for name, cfg in testnets.items():
        bal, err = get_balance(name, cfg)
        sym = cfg.get('symbol', '?')
        if err:
            print(f"  ❌ {name:25} ERROR: {err}")
            results[name] = {"status": "rpc_error", "error": err, "symbol": sym, "chain_id": cfg.get('chain_id')}
        else:
            status = "💰" if bal > 0 else "💨"
            print(f"  {status} {name:25} {bal:.6f} {sym}")
            results[name] = {"status": "ok", "balance": bal, "symbol": sym, "chain_id": cfg.get('chain_id')}
    with open('balance_check.json','w') as f:
        json.dump({"timestamp": datetime.utcnow().isoformat(), "wallet": ADDR, "results": results}, f, indent=2)
    print(f"\n✅ Saved to balance_check.json")
    return results

if __name__ == "__main__":
    main_balance()
