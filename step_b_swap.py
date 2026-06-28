#!/usr/bin/env python3
"""Step B: SWAP native<->WETH (wrap/unwrap) di chain dgn router & saldo."""
import json, time
from datetime import datetime
from web3 import Web3

CFG = json.load(open('onchain_config.json'))
BAL = json.load(open('balance_check.json'))['results']
WALLET = CFG['wallets'][0]
ADDR = Web3.to_checksum_address(WALLET['address'])
PK = WALLET['private_key']
SEPOLIA_PUBLIC = "https://ethereum-sepolia-rpc.publicnode.com"

# Map config dex chain-name -> balance/chain key
CHAIN_MAP = {
    "Sepolia": "Sepolia",
    "monad-testnet": "Monad Testnet",
}

WETH_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name":"wad","type":"uint256"}], "name": "withdraw", "outputs": [], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]

def rpc_of(name, cfg):
    r = cfg.get('rpc','')
    if 'ALCHEMY' in r and name=='Sepolia': return SEPOLIA_PUBLIC
    return r if r.startswith('http') else None

SWAP_AMOUNT = 0.00005  # native per direction

results = {}
print(f"🔄 SWAP native<->WETH dari {ADDR}\n")

for dex_chain, dex_list in CFG['dex_routers'].items():
    cn = CHAIN_MAP.get(dex_chain, dex_chain)
    bal_info = BAL.get(cn, {})
    cfg = CFG['chains'].get(cn)
    if not cfg:
        print(f"  ⚠️  {dex_chain}: chain config missing"); continue
    if bal_info.get('balance', 0) < SWAP_AMOUNT * 4:
        print(f"  ⏭️  {dex_chain}: saldo kurang ({bal_info.get('balance',0)})")
        continue
    rpc = rpc_of(cn, cfg)
    sym = cfg.get('symbol','?')
    explorer = cfg.get('explorer','')
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout':30}))
    chain_id = w3.eth.chain_id

    # Just pick first dex's WETH (same across all dex on same chain usually)
    first_dex = list(dex_list.keys())[0]
    weth_addr = Web3.to_checksum_address(dex_list[first_dex]['weth'])
    weth = w3.eth.contract(address=weth_addr, abi=WETH_ABI)
    chain_results = {}

    # === WRAP (native -> WETH) ===
    try:
        nonce = w3.eth.get_transaction_count(ADDR)
        amount_wei = w3.to_wei(SWAP_AMOUNT, 'ether')
        tx = weth.functions.deposit().build_transaction({
            'from': ADDR, 'value': amount_wei, 'nonce': nonce,
            'chainId': chain_id, 'gas': 100000,
            'gasPrice': w3.eth.gas_price,
        })
        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.3)
        except: pass
        signed = w3.eth.account.sign_transaction(tx, PK)
        raw = signed.raw_transaction if hasattr(signed,'raw_transaction') else signed.rawTransaction
        h = w3.eth.send_raw_transaction(raw)
        rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
        ok = rcpt.status == 1
        hx = h.hex()
        if not hx.startswith('0x'): hx = '0x'+hx
        s = "✅" if ok else "❌"
        print(f"  {s} {cn:20} WRAP   {SWAP_AMOUNT} {sym}->W{sym} | {hx[:14]}...")
        chain_results['wrap'] = {"status":"success" if ok else "reverted","tx":hx,"explorer_url":f"{explorer}/tx/{hx}"}
    except Exception as e:
        print(f"  ❌ {cn:20} WRAP   ERROR: {str(e)[:80]}")
        chain_results['wrap'] = {"status":"error","error":str(e)[:200]}

    time.sleep(2)

    # === UNWRAP (WETH -> native) ===
    try:
        weth_bal = weth.functions.balanceOf(ADDR).call()
        if weth_bal == 0:
            print(f"  ⏭️  {cn:20} UNWRAP skip (WETH balance 0)")
            chain_results['unwrap'] = {"status":"skipped","reason":"no WETH balance"}
        else:
            unwrap_amt = min(weth_bal, w3.to_wei(SWAP_AMOUNT, 'ether'))
            nonce = w3.eth.get_transaction_count(ADDR)
            tx = weth.functions.withdraw(unwrap_amt).build_transaction({
                'from': ADDR, 'nonce': nonce, 'chainId': chain_id,
                'gas': 100000, 'gasPrice': w3.eth.gas_price,
            })
            try:
                tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.3)
            except: pass
            signed = w3.eth.account.sign_transaction(tx, PK)
            raw = signed.raw_transaction if hasattr(signed,'raw_transaction') else signed.rawTransaction
            h = w3.eth.send_raw_transaction(raw)
            rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
            ok = rcpt.status == 1
            hx = h.hex()
            if not hx.startswith('0x'): hx = '0x'+hx
            s = "✅" if ok else "❌"
            print(f"  {s} {cn:20} UNWRAP {w3.from_wei(unwrap_amt,'ether')} W{sym}->{sym} | {hx[:14]}...")
            chain_results['unwrap'] = {"status":"success" if ok else "reverted","tx":hx,"explorer_url":f"{explorer}/tx/{hx}"}
    except Exception as e:
        print(f"  ❌ {cn:20} UNWRAP ERROR: {str(e)[:80]}")
        chain_results['unwrap'] = {"status":"error","error":str(e)[:200]}

    results[cn] = {"dex_chain_key": dex_chain, "weth": weth_addr, "operations": chain_results}
    time.sleep(2)

out = {"timestamp": datetime.now().isoformat(), "wallet": ADDR, "operation":"swap_wrap_unwrap", "results": results}
json.dump(out, open('swap_results.json','w'), indent=2)
print(f"\n✅ Saved to swap_results.json")
