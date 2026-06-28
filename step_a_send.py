#!/usr/bin/env python3
"""Step A: SEND native ke alamat random di semua chain yang ada saldo."""
import json, secrets, time
from datetime import datetime
from web3 import Web3
from eth_account import Account

CFG = json.load(open('onchain_config.json'))
BAL = json.load(open('balance_check.json'))['results']
WALLET = CFG['wallets'][0]
ADDR = Web3.to_checksum_address(WALLET['address'])
PK = WALLET['private_key']
SEPOLIA_PUBLIC = "https://ethereum-sepolia-rpc.publicnode.com"

def rpc_of(name, cfg):
    r = cfg.get('rpc','')
    if 'ALCHEMY' in r and name=='Sepolia': return SEPOLIA_PUBLIC
    return r if r.startswith('http') else None

def rand_addr():
    pk = '0x' + secrets.token_hex(32)
    return Account.from_key(pk).address

# Minimal amount per chain (very low to preserve gas)
MIN_AMOUNT = 0.00001  # native

results = {}
print(f"📤 SEND native dari {ADDR}\n")

for name, info in BAL.items():
    if info['status'] != 'ok' or info['balance'] <= 0.0001:
        results[name] = {"status":"skipped","reason":"no balance"}
        print(f"  ⏭️  {name:25} skip (saldo {info.get('balance',0)})")
        continue
    cfg = CFG['chains'][name]
    rpc = rpc_of(name, cfg)
    sym = cfg.get('symbol','?')
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout':20}))
        chain_id = w3.eth.chain_id
        to_addr = rand_addr()
        amount_wei = w3.to_wei(MIN_AMOUNT, 'ether')
        nonce = w3.eth.get_transaction_count(ADDR)
        # Use legacy gas to be safe across all chains
        try:
            gas_price = w3.eth.gas_price
        except:
            gas_price = w3.to_wei(1, 'gwei')
        tx = {
            'to': to_addr,
            'value': amount_wei,
            'gas': 21000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': chain_id,
        }
        # estimate gas dynamically (some chains need more)
        try:
            est = w3.eth.estimate_gas({'from':ADDR,'to':to_addr,'value':amount_wei})
            tx['gas'] = int(est * 1.2)
        except:
            pass
        signed = w3.eth.account.sign_transaction(tx, PK)
        raw = signed.raw_transaction if hasattr(signed,'raw_transaction') else signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw)
        h = tx_hash.hex()
        if not h.startswith('0x'): h = '0x'+h
        # wait briefly for receipt
        try:
            rcpt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            ok = rcpt.status == 1
        except Exception as e:
            ok = None
            rcpt = None
        explorer = cfg.get('explorer','')
        url = f"{explorer}/tx/{h}" if explorer else h
        status = "✅" if ok else ("⏳" if ok is None else "❌")
        print(f"  {status} {name:25} {MIN_AMOUNT} {sym} -> {to_addr[:10]}... | {h[:14]}...")
        results[name] = {
            "status":"success" if ok else ("pending" if ok is None else "reverted"),
            "tx": h, "to": to_addr, "amount": MIN_AMOUNT,
            "symbol": sym, "explorer_url": url,
        }
    except Exception as e:
        msg = str(e)[:120]
        print(f"  ❌ {name:25} ERROR: {msg}")
        results[name] = {"status":"error","error":msg,"symbol":sym}
    time.sleep(1)

out = {"timestamp": datetime.now().isoformat(), "wallet": ADDR, "operation":"send_native", "results": results}
json.dump(out, open('send_results.json','w'), indent=2)
print(f"\n✅ Saved to send_results.json")
