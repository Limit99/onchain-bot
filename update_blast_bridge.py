#!/usr/bin/env python3
"""Update onchain_config.json dengan Blast bridge yang benar"""
import json

cfg = json.load(open('onchain_config.json'))

# Update Blast bridge contract dengan OptimismPortal yang benar
cfg['bridge_contracts']['Sepolia']['blast_sepolia'] = {
    "type": "op_stack_portal",
    "portal": "0x0eC143D865D90050C65f50b8B97B3c4C2F6A4B69",
    "dest_chain": "Blast Sepolia",
    "dest_chain_id": 168587773
}

# Save
json.dump(cfg, open('onchain_config.json', 'w'), indent=2)
print("✅ Updated Blast bridge portal to 0x0eC143D865D90050C65f50b8B97B3c4C2F6A4B69")
