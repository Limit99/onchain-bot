#!/usr/bin/env python3
"""
Step C Pending Tasks:
1. Bridge Sepolia → Arbitrum Sepolia (via Inbox depositEth)
2. Bridge Sepolia → Blast Sepolia (via L1 Bridge sendMessage)
3. Send minimal on Arbitrum Sepolia
4. Send minimal on Blast Sepolia
5. Commit results to repo
"""
import json
import time
from web3 import Web3
from eth_account import Account

cfg = json.load(open('onchain_config.json'))
pk = cfg['wallets'][0]['private_key']
addr = Web3.to_checksum_address(cfg['wallets'][0]['address'])
account = Account.from_key(pk)

def get_raw(signed):
    return signed.rawTransaction if hasattr(signed, 'rawTransaction') else signed.raw_transaction

def get_w3(rpc):
    return Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 30}))

# ===== RPCs =====
SEPOLIA_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
ARB_RPC = "https://sepolia-rollup.arbitrum.io/rpc"
BLAST_RPC = "https://sepolia.blast.io"

w3_sep = get_w3(SEPOLIA_RPC)

print("=" * 70)
print("STEP C - MENYELESAIKAN TUGAS PENDING")
print("=" * 70)
bal_sep = w3_sep.eth.get_balance(addr)
print(f"Sepolia balance: {w3_sep.from_wei(bal_sep, 'ether')} ETH")
print()

# ===== TASK 1: Bridge to Arbitrum Sepolia =====
# Arbitrum Inbox: depositEth() - payable, no args
ARBITRUM_INBOX = Web3.to_checksum_address("0xaAe29B0366299461418F5324a79Afc425BE5ae21")
BRIDGE_AMOUNT_ARB = Web3.to_wei(0.001, 'ether')  # 0.001 ETH

deposit_eth_selector = Web3.keccak(text="depositEth()")[:4]
print(f"1️⃣  BRIDGE Sepolia → Arbitrum Sepolia")
print(f"   Inbox: {ARBITRUM_INBOX}")
print(f"   Amount: {Web3.from_wei(BRIDGE_AMOUNT_ARB, 'ether')} ETH")
print(f"   Selector: {deposit_eth_selector.hex()}")

try:
    nonce = w3_sep.eth.get_transaction_count(addr)
    gas_price = int(w3_sep.eth.gas_price * 1.1)
    
    tx_arb = {
        'from': addr,
        'to': ARBITRUM_INBOX,
        'value': BRIDGE_AMOUNT_ARB,
        'data': deposit_eth_selector,
        'gas': 100000,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': 11155111,
    }
    
    signed = account.sign_transaction(tx_arb)
    tx_hash = w3_sep.eth.send_raw_transaction(get_raw(signed))
    print(f"   📤 Tx: {tx_hash.hex()}")
    receipt = w3_sep.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    arb_bridge_ok = receipt['status'] == 1
    print(f"   {'✅ SUCCESS' if arb_bridge_ok else '❌ FAILED'} - Gas: {receipt['gasUsed']}")
    arb_bridge_tx = tx_hash.hex()
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    arb_bridge_ok = False
    arb_bridge_tx = None

print()
time.sleep(2)

# ===== TASK 2: Bridge to Blast Sepolia =====
# Blast L1 Bridge: sendMessage(address,uint256,bytes)
BLAST_BRIDGE = Web3.to_checksum_address("0xDeDa8D3CCf044fE2A16217846B6e1f1cfD8e122f")
BRIDGE_AMOUNT_BLAST = Web3.to_wei(0.001, 'ether')

print(f"2️⃣  BRIDGE Sepolia → Blast Sepolia")
print(f"   Bridge: {BLAST_BRIDGE}")
print(f"   Amount: {Web3.from_wei(BRIDGE_AMOUNT_BLAST, 'ether')} ETH")

# sendMessage(address _to, uint256 _gasLimit, bytes _data)
send_msg_selector = Web3.keccak(text="sendMessage(address,uint256,bytes)")[:4]
# Encode params
to_padded = addr[2:].lower().zfill(64)
gas_limit_padded = hex(100000)[2:].zfill(64)  # 100k gas on L2
# data offset (position 3 = 0x60)
data_offset = hex(96)[2:].zfill(64)
# data length = 0
data_length = hex(0)[2:].zfill(64)

blast_data = send_msg_selector + bytes.fromhex(to_padded + gas_limit_padded + data_offset + data_length)

try:
    nonce = w3_sep.eth.get_transaction_count(addr)
    gas_price = int(w3_sep.eth.gas_price * 1.1)
    
    tx_blast = {
        'from': addr,
        'to': BLAST_BRIDGE,
        'value': BRIDGE_AMOUNT_BLAST,
        'data': blast_data,
        'gas': 200000,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': 11155111,
    }
    
    signed = account.sign_transaction(tx_blast)
    tx_hash = w3_sep.eth.send_raw_transaction(get_raw(signed))
    print(f"   📤 Tx: {tx_hash.hex()}")
    receipt = w3_sep.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    blast_bridge_ok = receipt['status'] == 1
    print(f"   {'✅ SUCCESS' if blast_bridge_ok else '❌ FAILED'} - Gas: {receipt['gasUsed']}")
    blast_bridge_tx = tx_hash.hex()
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    blast_bridge_ok = False
    blast_bridge_tx = None

print()
print("=" * 70)
print("BRIDGE SELESAI. Menunggu saldo masuk ke L2 (~2-5 menit)...")
print("=" * 70)

# ===== WAIT FOR BRIDGES =====
print("\n⏳ Menunggu 90 detik agar bridge selesai...")
time.sleep(90)

# ===== TASK 3: Send minimal on Arbitrum Sepolia =====
print("\n3️⃣  SEND MINIMAL di Arbitrum Sepolia")
w3_arb = get_w3(ARB_RPC)
bal_arb = w3_arb.eth.get_balance(addr)
print(f"   Arbitrum balance: {w3_arb.from_wei(bal_arb, 'ether')} ETH")

arb_send_ok = False
arb_send_tx = None

if bal_arb > Web3.to_wei(0.00005, 'ether'):
    # Send minimal to random address
    random_addr = Account.create().address
    send_amount = Web3.to_wei(0.00001, 'ether')
    
    try:
        nonce = w3_arb.eth.get_transaction_count(addr)
        gas_price = int(w3_arb.eth.gas_price * 1.2)
        
        tx_send = {
            'from': addr,
            'to': random_addr,
            'value': send_amount,
            'gas': 21000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 421614,
        }
        
        signed = account.sign_transaction(tx_send)
        tx_hash = w3_arb.eth.send_raw_transaction(get_raw(signed))
        print(f"   📤 Tx: {tx_hash.hex()}")
        receipt = w3_arb.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        arb_send_ok = receipt['status'] == 1
        print(f"   {'✅ SUCCESS' if arb_send_ok else '❌ FAILED'} - Gas: {receipt['gasUsed']}")
        arb_send_tx = tx_hash.hex()
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        # Retry with higher gas
        print(f"   🔄 Retry dengan gas lebih tinggi...")
        try:
            nonce = w3_arb.eth.get_transaction_count(addr)
            gas_price = int(w3_arb.eth.gas_price * 2)
            
            tx_send = {
                'from': addr,
                'to': random_addr,
                'value': send_amount,
                'gas': 50000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': 421614,
            }
            
            signed = account.sign_transaction(tx_send)
            tx_hash = w3_arb.eth.send_raw_transaction(get_raw(signed))
            print(f"   📤 Retry Tx: {tx_hash.hex()}")
            receipt = w3_arb.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            arb_send_ok = receipt['status'] == 1
            print(f"   {'✅ SUCCESS' if arb_send_ok else '❌ FAILED'} - Gas: {receipt['gasUsed']}")
            arb_send_tx = tx_hash.hex()
        except Exception as e2:
            print(f"   ❌ RETRY ERROR: {e2}")
else:
    print(f"   ⚠️  Saldo belum masuk atau terlalu kecil. Bridge mungkin butuh waktu lebih lama.")
    print(f"   Akan retry nanti setelah bridge selesai.")

print()

# ===== TASK 4: Send minimal on Blast Sepolia =====
print("4️⃣  SEND MINIMAL di Blast Sepolia")
w3_blast = get_w3(BLAST_RPC)
bal_blast = w3_blast.eth.get_balance(addr)
print(f"   Blast balance: {w3_blast.from_wei(bal_blast, 'ether')} ETH")

blast_send_ok = False
blast_send_tx = None

if bal_blast > Web3.to_wei(0.00005, 'ether'):
    random_addr = Account.create().address
    send_amount = Web3.to_wei(0.00001, 'ether')
    
    try:
        nonce = w3_blast.eth.get_transaction_count(addr)
        gas_price = int(w3_blast.eth.gas_price * 1.2)
        
        tx_send = {
            'from': addr,
            'to': random_addr,
            'value': send_amount,
            'gas': 21000,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': 168587773,
        }
        
        signed = account.sign_transaction(tx_send)
        tx_hash = w3_blast.eth.send_raw_transaction(get_raw(signed))
        print(f"   📤 Tx: {tx_hash.hex()}")
        receipt = w3_blast.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        blast_send_ok = receipt['status'] == 1
        print(f"   {'✅ SUCCESS' if blast_send_ok else '❌ FAILED'} - Gas: {receipt['gasUsed']}")
        blast_send_tx = tx_hash.hex()
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
else:
    print(f"   ⚠️  Saldo belum masuk. Bridge mungkin butuh waktu lebih lama.")

print()

# ===== FINAL SUMMARY =====
print("=" * 70)
print("FINAL SUMMARY - STEP C PENDING TASKS")
print("=" * 70)
print(f"1. Bridge Sepolia→Arbitrum: {'✅' if arb_bridge_ok else '❌'} {arb_bridge_tx or 'FAILED'}")
print(f"2. Bridge Sepolia→Blast:    {'✅' if blast_bridge_ok else '❌'} {blast_bridge_tx or 'FAILED'}")
print(f"3. Send Arbitrum Sepolia:   {'✅' if arb_send_ok else '⏳'} {arb_send_tx or 'PENDING'}")
print(f"4. Send Blast Sepolia:      {'✅' if blast_send_ok else '⏳'} {blast_send_tx or 'PENDING'}")
print()

# Save results
results = {
    "bridge_arbitrum": {"success": arb_bridge_ok, "tx": arb_bridge_tx},
    "bridge_blast": {"success": blast_bridge_ok, "tx": blast_bridge_tx},
    "send_arbitrum": {"success": arb_send_ok, "tx": arb_send_tx},
    "send_blast": {"success": blast_send_ok, "tx": blast_send_tx},
    "timestamp": int(time.time())
}
json.dump(results, open('step_c_results.json', 'w'), indent=2)
print("✅ Results saved to step_c_results.json")
