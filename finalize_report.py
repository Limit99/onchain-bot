#!/usr/bin/env python3
import json
from datetime import datetime
from web3 import Web3

bal = json.load(open('balance_check.json'))
send = json.load(open('send_results.json'))
swap = json.load(open('swap_results.json'))
CFG = json.load(open('onchain_config.json'))
ADDR = Web3.to_checksum_address(CFG['wallets'][0]['address'])
SEPOLIA_PUBLIC = "https://ethereum-sepolia-rpc.publicnode.com"
def rpc_of(n,cfg):
    r=cfg.get('rpc','')
    if 'ALCHEMY' in r and n=='Sepolia': return SEPOLIA_PUBLIC
    return r if r.startswith('http') else None

final_bal = {}
for n,info in bal['results'].items():
    if info['status']!='ok': continue
    cfg=CFG['chains'][n]; rpc=rpc_of(n,cfg)
    try:
        w3=Web3(Web3.HTTPProvider(rpc,request_kwargs={'timeout':10}))
        b=float(w3.from_wei(w3.eth.get_balance(ADDR),'ether'))
        final_bal[n]={"before":info['balance'],"after":b,"delta":b-info['balance'],"symbol":info['symbol']}
    except Exception as e:
        final_bal[n]={"error":str(e)[:60]}

report={
  "timestamp":datetime.now().isoformat(),"wallet":ADDR,
  "summary":{
    "send_success":sum(1 for r in send['results'].values() if r['status']=='success'),
    "send_skipped":sum(1 for r in send['results'].values() if r['status']=='skipped'),
    "send_failed":sum(1 for r in send['results'].values() if r['status'] not in ('success','skipped')),
    "swap_success":sum(1 for c in swap['results'].values() for op,r in c['operations'].items() if r['status']=='success'),
    "swap_failed":sum(1 for c in swap['results'].values() for op,r in c['operations'].items() if r['status'] not in ('success','skipped')),
  },
  "balance_delta":final_bal,
  "send_details":send['results'],
  "swap_details":swap['results'],
}
json.dump(report,open('test_suite_report.json','w'),indent=2)
print(json.dumps(report['summary'],indent=2))
print("\n--- BALANCE DELTAS ---")
for n,b in final_bal.items():
    if 'delta' in b:
        print(f"  {n:25} {b['before']:.6f} -> {b['after']:.6f} {b['symbol']} (delta {b['delta']:+.8f})")
