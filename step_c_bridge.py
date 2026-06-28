#!/usr/bin/env python3
"""Step C: Bridge testnet ETH from Sepolia ke chain-chain zero saldo via OP Stack portal / Blast L1Bridge.

Strategi: Untuk OP Stack chains (OP/Base/Unichain Sepolia), kirim ETH langsung ke
OptimismPortalProxy fallback() yang akan trigger depositTransaction(msg.sender, value, gas, false, data)
sehingga ETH otomatis credited ke address yang sama di L2.
Untuk Blast Sepolia, kirim ETH ke L1StandardBridge yang receive() forward deposit.

Aman: hanya gunakan ~0.005 ETH per bridge, sisain gas + buffer di Sepolia.
"""
import json, time, sys
from datetime import datetime
from web3 import Web3

CFG_PATH = "/data/data/com.termux/files/home/onchain-bot/onchain_config.json"
OUT_PATH = "/data/data/com.termux/files/home/onchain-bot/bridge_results.json"

with open(CFG_PATH) as f:
    cfg = json.load(f)

wallet = cfg["wallets"][0]
ADDR = Web3.to_checksum_address(wallet["address"])
PK = wallet["private_key"]

# Sepolia RPC — config punya placeholder, pakai fallback public
sep_rpc = cfg["chains"]["Sepolia"]["rpc"]
if not sep_rpc.startswith("http"):
    sep_rpc = "https://ethereum-sepolia-rpc.publicnode.com"

w3 = Web3(Web3.HTTPProvider(sep_rpc, request_kwargs={"timeout": 30}))
print(f"[i] Sepolia connected: {w3.is_connected()}  chain_id={w3.eth.chain_id}")
bal = w3.eth.get_balance(ADDR)
print(f"[i] Sepolia balance: {w3.from_wei(bal,'ether')} ETH")

# Setiap bridge pakai 0.005 ETH biar awet (4 bridge = 0.02 ETH, sisa untuk gas)
BRIDGE_AMOUNT_ETH = 0.005
amount_wei = w3.to_wei(BRIDGE_AMOUNT_ETH, "ether")

bridges = cfg["bridge_contracts"]["Sepolia"]
results = {}
nonce = w3.eth.get_transaction_count(ADDR)

for name, b in bridges.items():
    print(f"\n=== Bridge → {b['dest_chain']} ({b['type']}) ===")
    target = b.get("portal") or b.get("l1_bridge")
    target = Web3.to_checksum_address(target)
    try:
        # Gas estimate untuk simple transfer ke contract dengan fallback
        try:
            gas = w3.eth.estimate_gas({"from": ADDR, "to": target, "value": amount_wei})
            gas = int(gas * 1.3)
        except Exception as eg:
            print(f"  [!] estimate failed: {eg}; using fallback gas 200_000")
            gas = 200_000

        gas_price = int(w3.eth.gas_price * 1.2)
        tx = {
            "from": ADDR,
            "to": target,
            "value": amount_wei,
            "gas": gas,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": 11155111,
        }
        signed = w3.eth.account.sign_transaction(tx, PK)
        raw = signed.raw_transaction if hasattr(signed, "raw_transaction") else signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw)
        tx_hex = tx_hash.hex()
        if not tx_hex.startswith("0x"):
            tx_hex = "0x" + tx_hex
        print(f"  [✓] tx sent: {tx_hex}")
        print(f"      https://sepolia.etherscan.io/tx/{tx_hex}")
        nonce += 1

        # Wait receipt
        try:
            rc = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            status = "success" if rc.status == 1 else "failed"
            print(f"      receipt status: {status}  gas_used={rc.gasUsed}")
        except Exception as ew:
            status = "pending_timeout"
            print(f"      [!] wait timeout: {ew}")

        results[name] = {
            "status": status,
            "tx": tx_hex,
            "to_contract": target,
            "amount_eth": BRIDGE_AMOUNT_ETH,
            "dest_chain": b["dest_chain"],
            "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hex}",
        }
    except Exception as e:
        print(f"  [✗] error: {e}")
        results[name] = {"status": "error", "error": str(e), "dest_chain": b["dest_chain"]}

    time.sleep(2)

out = {
    "timestamp": datetime.utcnow().isoformat(),
    "wallet": ADDR,
    "operation": "bridge_sepolia_to_op_stack",
    "source_chain": "Sepolia",
    "results": results,
}
with open(OUT_PATH, "w") as f:
    json.dump(out, f, indent=2)
print(f"\n[✓] saved → {OUT_PATH}")
