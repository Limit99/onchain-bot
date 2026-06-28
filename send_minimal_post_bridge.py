#!/usr/bin/env python3
"""Send minimal amounts to random address on chains that have balance after bridge."""
import json, secrets, time
from web3 import Web3
from eth_account import Account

CFG = json.load(open('onchain_config.json'))
WALLET = CFG['wallets'][0]
ADDR = Web3.to_checksum_address(WALLET['address'])
PK = WALLET['private_key']

def rpc_of(name, cfg):
    r = cfg.get('rpc','')
    if 'ALCHEMY' in r and name=='Sepolia':
        return "https://ethereum-sepolia-rpc.publicnode.com"
    return r if r.startswith('http') else None

def rand_addr():
    pk = '0x' + secrets.token_hex(32)
    return Account.from_key(pk).address

MIN_AMOUNT = 0.00001  # native

# We'll use the latest balance_check.json if exists, otherwise fetch fresh.
try:
    BAL = json.load(open('balance_check.json'))['results']
except:
    BAL = {}

results = {}
print(f"📤 SEND native dari {ADDR} (minimal {MIN_AMOUNT})")
for name, info in BAL.items():
    if info['status'] != 'ok' or info['balance'] <= 0:
        # skip if no balance or error
        continue
    cfg = CFG['chains'].get(name)
    if not cfg:
        continue
    rpc = rpc_of(name, cfg)
    if not rpc:
        continue
    w3 = Web3(Web3.HTTPProvider(rpc))
    try:
        bal = w3.eth.get_balance(ADDR)
        if bal == 0:
            print(f"  ⏭️  {name:25} skip (saldo 0 sekarang)")
            continue
        amount_wei = w3.to_wei(MIN_AMOUNT, 'ether')
        if bal < amount_wei:
            print(f"  ⏭️  {name:25} skip (saldo {w3.from_wei(bal,'ether'):.6f} < {MIN_AMOUNT})")
            continue
        to_addr = rand_addr()
        nonce = w3.eth.get_transaction_count(ADDR)
        tx = {
            'from': ADDR,
            'to': to_addr,
            'value': amount_wei,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id,
        }
        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.2)
        except:
            pass
        signed = w3.eth.account.sign_transaction(tx, PK)
        raw = signed.raw_transaction if hasattr(signed,'raw_transaction') else signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw)
        rcpt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        status = "success" if rcpt.status == 1 else "failed"
        print(f"  [{'✅' if status=='success' else '❌'}] {name:25} -> {to_addr} {MIN_AMOUNT} {cfg['symbol']} tx {tx_hash.hex()[:10]}...")
        results[name] = {
            "status": status,
            "tx": tx_hash.hex(),
            "to": to_addr,
            "amount": MIN_AMOUNT,
            "symbol": cfg['symbol'],
            "explorer": cfg.get('explorer', '').rstrip('/') + f"/tx/{tx_hash.hex()}" if cfg.get('explorer') else None
        }
        time.sleep(2)
    except Exception as e:
        print(f"  ❌ {name:25} error: {e}")
        results[name] = {"status": "error", "error": str(e)}

# Save results
out = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "wallet": ADDR,
    "operation": "send_minimal_post_bridge",
    "results": results
}
with open('send_results.json', 'w') as f:
    json.dump(out, f, indent=2)
print(f"\n✅ Saved to send_results.json")