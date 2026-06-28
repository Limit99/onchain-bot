#!/usr/bin/env python3
"""Post-bridge wrap/unwrap on L2s that received funds."""
import json, time
from web3 import Web3

CFG = json.load(open('onchain_config.json'))
WALLET = CFG['wallets'][0]
ADDR = Web3.to_checksum_address(WALLET['address'])
PK = WALLET['private_key']

# WETH address on OP Stack L2s (same as L1 canonical)
WETH_L2 = Web3.to_checksum_address('0x4200000000000000000000000000000000000006')
WETH_ABI = [
    {"constant":False,"inputs":[],"name":"deposit","outputs":[],"payable":True,"stateMutability":"payable","type":"function"},
    {"constant":False,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"type":"function"},
]

def wrap_unwrap(chain_name):
    c = CHAINS.get(chain_name)
    if not c:
        print(f"[{chain_name}] not in config")
        return
    rpc = c['rpc']
    if not rpc.startswith('http'):
        print(f"[{chain_name}] RPC not http")
        return
    w3 = Web3(Web3.HTTPProvider(rpc))
    try:
        bal = w3.eth.get_balance(ADDR)
        print(f"[{chain_name}] balance {w3.from_wei(bal,'ether')} {c['symbol']}")
    except Exception as e:
        print(f"[{chain_name}] RPC error: {e}")
        return
    if bal == 0:
        print(f"[{chain_name}] zero balance, skip")
        return
    # WETH contract
    weth = w3.eth.contract(address=WETH_L2, abi=WETH_ABI)
    amount = web3.to_wei(0.001, 'ether')  # use 0.001 for wrap/unwrap (should be enough)
    try:
        # Wrap
        nonce = w3.eth.get_transaction_count(ADDR)
        tx = weth.functions.deposit().build_transaction({
            'from': ADDR, 'value': amount, 'nonce': nonce,
            'chainId': w3.eth.chain_id, 'gas': 100000,
            'gasPrice': w3.eth.gas_price,
        })
        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.2)
        except: pass
        signed = w3.eth.account.sign_transaction(tx, PK)
        raw = signed.raw_transaction if hasattr(signed,'raw_transaction') else signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw)
        rcpt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        print(f"  [{chain_name}] wrap {'✅' if rcpt.status==1 else '❌'} tx {tx_hash.hex()[:10]}...")
        time.sleep(2)
        # Unwrap
        nonce = w3.eth.get_transaction_count(ADDR)
        tx = weth.functions.withdraw(amount).build_transaction({
            'from': ADDR, 'nonce': nonce,
            'chainId': w3.eth.chain_id, 'gas': 100000,
            'gasPrice': w3.eth.gas_price,
        })
        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.2)
        except: pass
        signed = w3.eth.account.sign_transaction(tx, PK)
        raw = signed.raw_transaction if hasattr(signed,'raw_transaction') else signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw)
        rcpt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        print(f"  [{chain_name}] unwrap {'✅' if rcpt.status==1 else '❌'} tx {tx_hash.hex()[:10]}...")
    except Exception as e:
        print(f"[{chain_name}] error: {e}")

if __name__ == '__main__':
    CHAINS = {c['chain_id']:c for c in CFG['ch in CFG['chains'].values()}  # nope
    # Build dict by name
    CHAINS = {name:conf for name,conf in CFG['chains'].items()}
    for name in ['Optimism Sepolia', 'Base Sepolia', 'Unichain Sepolia']:
        wrap_unwrap(name)
        print()