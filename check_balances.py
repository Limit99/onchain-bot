#!/usr/bin/env python3
import json
import time
from web3 import Web3

addr = Web3.to_checksum_address("0xC11B7A03B924C24F91364986139D0BeceA20b2EF")

testnet_chains = {
    "Monad Testnet": "https://testnet-rpc.monad.xyz",
    "DAC-testnet": "https://rpctest.dachain.tech",
    "Sepolia": "https://ethereum-sepolia-rpc.publicnode.com",
    "Holesky": "https://holesky.drpc.org",
    "BSC Testnet": "https://bsc-testnet-rpc.publicnode.com",
    "Polygon Amoy": "https://rpc-amoy.polygon.technology",
    "Arbitrum Sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
    "Optimism Sepolia": "https://sepolia.optimism.io",
    "Avalanche Fuji": "https://api.avax-test.network/ext/bc/C/rpc",
    "Base Sepolia": "https://sepolia.base.org",
    "Scroll Sepolia": "https://sepolia-rpc.scroll.io",
    "Linea Sepolia": "https://rpc.sepolia.linea.build",
    "zkSync Sepolia": "https://sepolia.era.zksync.dev",
    "Blast Sepolia": "https://sepolia.blast.io",
    "Berachain Bepolia": "https://bepolia.rpc.berachain.com",
    "Unichain Sepolia": "https://unichain-sepolia-rpc.publicnode.com",
    "Gnosis Chiado": "https://rpc.chiadochain.net",
    "Mantle Sepolia": "https://rpc.sepolia.mantle.xyz",
}

print("=" * 80)
print("BALANCE AUDIT - TESTNET CHAINS")
print(f"Address: {addr}")
print("=" * 80)

results = []
for name, rpc in testnet_chains.items():
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
        if not w3.is_connected():
            print(f"❌ {name}: NOT CONNECTED")
            continue
        bal = w3.eth.get_balance(addr)
        chain_id = w3.eth.chain_id
        eth = float(w3.from_wei(bal, "ether"))
        status = "✅" if eth > 0.0001 else "⚠️ " if eth > 0 else "❌"
        print(f"{status} {name:20s} (chainId:{chain_id:8d}): {eth:.6f}")
        results.append({"name": name, "balance": eth, "chain_id": chain_id, "rpc": rpc})
    except Exception as e:
        print(f"❌ {name}: ERROR - {str(e)[:80]}")
    time.sleep(0.2)

print("=" * 80)
print("\nSUMMARY:")
chains_with_balance = [r for r in results if r["balance"] > 0.001]
chains_empty = [r for r in results if r["balance"] <= 0.001 and r["balance"] > 0]
chains_zero = [r for r in results if r["balance"] == 0]

print(f"Chains with sufficient balance (>0.001): {len(chains_with_balance)}")
for c in chains_with_balance:
    print(f"  ✅ {c['name']}: {c['balance']:.6f}")

print(f"\nChains with low balance (0-0.001): {len(chains_empty)}")
for c in chains_empty:
    print(f"  ⚠️  {c['name']}: {c['balance']:.6f}")

print(f"\nChains with zero balance: {len(chains_zero)}")
for c in chains_zero:
    print(f"  ❌ {c['name']}: {c['balance']:.6f}")

# Save to JSON for next steps
json.dump(results, open('balance_audit.json', 'w'), indent=2)
print("\n✅ Balance audit saved to balance_audit.json")
