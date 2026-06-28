import json
path = 'onchain_config.json'
with open(path, 'r') as f:
    data = json.load(f)
chains = data.get('chains', {})
new_chains = {}
for k, v in list(chains.items()):
    klower = k.strip().lower()
    if klower == 'monad-testnet' or klower == 'monad testnet':
        if v.get('chain_id') == 10143:
            new_chains['Monad Testnet'] = v
        # else skip duplicate/wrong
    else:
        new_chains[k] = v
data['chains'] = new_chains
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print('Fixed Monad Testnet entry')
