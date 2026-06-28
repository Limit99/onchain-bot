import sys
import re

def read_lines(path):
    with open(path, 'r') as f:
        return f.readlines()

def write_lines(path, lines):
    with open(path, 'w') as f:
        f.writelines(lines)

def main():
    # Update onchain_config.json: ensure Monad Testnet has chain_id 10143
    config_path = 'onchain_config.json'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        config = {}
    chains = config.get('chains', {})
    # Ensure Monad Testnet entry exists with correct chain_id
    if 'Monad Testnet' in chains:
        chains['Monad Testnet']['chain_id'] = 10143
    else:
        # Maybe it's under a different key? We'll just set it.
        chains['Monad Testnet'] = {
            'rpc': 'https://testnet-rpc.monad.xyz',
            'chain_id': 10143,
            'symbol': 'MON',
            'explorer': 'https://testnet.monadexplorer.com',
            'type': 'testnet'
        }
    # Also check for any monad-testnet with wrong chain_id and fix
    for name, data in chains.items():
        if 'monad' in name.lower() and data.get('chain_id') == 41455:
            data['chain_id'] = 10143
    config['chains'] = chains
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print('Updated onchain_config.json')

    # Now update onchain_bot.py
    lines = read_lines('onchain_bot.py')

    # 1. Fix Monad Testnet chain_id in KNOWN_CHAINS dictionary (lines around 127)
    for i, line in enumerate(lines):
        if '41455:' in line and 'Monad Testnet' in line:
            lines[i] = line.replace('41455:', '10143:')
            break

    # 2. Add import for requests after 'from decimal import Decimal'
    for i, line in enumerate(lines):
        if line.strip().startswith('from decimal import Decimal'):
            # Insert after this line
            lines.insert(i+1, '\n')
            lines.insert(i+2, '# For faucet functionality\n')
            lines.insert(i+3, 'try:\n')
            lines.insert(i+4, '    import requests\n')
            lines.insert(i+5, 'except ImportError:\n')
            lines.insert(i+6, '    requests = None\n')
            lines.insert(i+7, '\n')
            break

    # 3. In BlockchainEngine.__init__, after self._load_history(), add faucet state
    # Find the __init__ method
    init_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('def __init__(self, config: Config):'):
            init_start = i
            break
    if init_start is not None:
        # Find the line with self._load_history()
        for i in range(init_start, len(lines)):
            if 'self._load_history()' in lines[i]:
                # Insert after this line
                indent = len(lines[i]) - len(lines[i].lstrip())
                lines.insert(i+1, ' ' * indent + '        # Faucet-related state\n')
                lines.insert(i+2, ' ' * indent + '        self._faucet_last_request = {}\n')
                break

    # 4. Add the two new methods after the __init__ method, but before the next method.
    # We'll insert them at the end of the BlockchainEngine class, just before the next class (Scheduler).
    # Find the start of the Scheduler class
    scheduler_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('class Scheduler:'):
            scheduler_start = i
            break
    if scheduler_start is not None:
        # We'll insert our methods at position scheduler_start, but we need to indent them as class methods.
        # Build the lines to insert.
        indent = '    '  # 4 spaces for method indentation
        method_lines = [
            '',
            '    def _request_faucet(self, chain_name: str, address: str) -> bool:',
            '        \"\"\"Attempt to get funds from a faucet for the given address on the given chain.\"\"\"',
            '        # Faucet configurations: key = chain name as in config',
            '        FAUCETS = {',
            '            \"Sepolia\": {',
            '                \"url\": \"https://sepolia-faucet.pk910.de/\",',
            '                \"method\": \"POST\",',
            '                \"headers\": {\"Content-Type\": \"application/json\"},',
            '                \"data\": lambda addr: {\"address\": addr},',
            '            },',
            '            \"Polygon Amoy\": {',
            '                \"url\": \"https://faucet.polygon.technology/\",',
            '                \"method\": \"POST\",',
            '                \"headers\": {\"Content-Type\": \"application/json\"},',
            '                \"data\": lambda addr: {\"address\": addr},',
            '            },',
            '            \"Arbitrum Sepolia\": {',
            '                \"url\": \"https://arbitrum-sepolia.faucet.arbitrum.io/\",',
            '                \"method\": \"POST\",',
            '                \"headers\": {\"Content-Type\": \"application/json\"},',
            '                \"data\": lambda addr: {\"address\": addr},',
            '            },',
            '            \"Optimism Sepolia\": {',
            '                \"url\": \"https://opsepolia-fuel.com/\",',
            '                \"method\": \"POST\",',
            '                \"headers\": {\"Content-Type\": \"application/json\"},',
            '                \"data\": lambda addr: {\"address\": addr},',
            '            },',
            '            # Add more faucets as needed',
            '        }',
            '        if chain_name not in FAUCETS:',
            '            log_warn(f\"No faucet configured for {chain_name}\")',
            '            return False',
            '        conf = FAUCETS[chain_name]',
            '        url = conf[\"url\"]',
            '        method = conf.get(\"method\", \"GET\").upper()',
            '        headers = conf.get(\"headers\", {})',
            '        data_func = conf.get(\"data\")',
            '        if data_func is None:',
            '            data = None',
            '        else:',
            '            data = data_func(address)',
            '        # Rate limiting: wait at least 1 minute between requests per address',
            '        now = time.time()',
            '        last = self._faucet_last_request.get((chain_name, address), 0)',
            '        if now - last < 60:',
            '            wait = int(60 - (now - last))',
            '            log_info(f\"Faucet rate limit: waiting {wait}s before next request for {address} on {chain_name}\")',
            '            time.sleep(wait)',
            '        try:',
            '            if requests is not None:',
            '                if method == \"POST\":',
            '                    resp = requests.post(url, json=data, headers=headers, timeout=30)',
            '                else:',
            '                    resp = requests.get(url, params=data, headers=headers, timeout=30)',
            '                if resp.status_code in (200, 201, 202):',
            '                    log_ok(f\"Faucet request successful for {address} on {chain_name}\")',
            '                    self._faucet_last_request[(chain_name, address)] = time.time()',
            '                    return True',
            '                else:',
            '                    log_err(f\"Faucet request failed: {resp.status_code} {resp.text[:200]}\")',
            '            else:',
            '                # Fallback to urllib',
            '                import urllib.request',
            '                import urllib.error',
            '                data_encoded = None',
            '                if data is not None:',
            '                    if method == \"POST\":',
            '                        data_encoded = json.dumps(data).encode(\"utf-8\")',
            '                    else:',
            '                        # For GET, we would need to append to URL - skip for simplicity',
            '                        log_warn(\"GET with data not supported in fallback, skipping faucet\")',
            '                        return False',
            '                req = urllib.request.Request(url, data=data_encoded, headers=headers, method=method)',
            '                try:',
            '                    with urllib.request.urlopen(req, timeout=30) as resp:',
            '                        if 200 <= resp.status < 300:',
            '                            log_ok(f\"Faucet request successful for {address} on {chain_name}\")',
            '                            self._faucet_last_request[(chain_name, address)] = time.time()',
            '                            return True',
            '                except urllib.error.HTTPError as e:',
            '                    log_err(f\"Faucet request failed: {e.code} {e.read()[:200]}\")',
            '                except Exception as e:',
            '                    log_err(f\"Faucet request error: {e}\")',
            '        except Exception as e:',
            '            log_err(f\"Faucet request error: {e}\")',
            '        return False',
            '',
            '    def _ensure_minimum_balance(self, wallet: dict, amount_ether: Decimal, min_balance: Decimal = Decimal(\"0.001\")) -> bool:',
            '        \"\"\"Ensure the wallet has enough balance for the transaction plus a minimum buffer.\"\"\"',
            '        if self.w3 is None:',
            '            return False',
            '        address = wallet[\"address\"]',
            '        try:',
            '            balance = self.get_balance(address)',
            '            needed = amount_ether + min_balance',
            '            if balance >= needed:',
            '                return True',
            '            # Balance too low, try to get from faucet if on testnet',
            '            chain_info = self._chain_info()',
            '            if chain_info.get(\"type\") == \"testnet\":',
            '                log_warn(f\"Low balance on {self.current_chain}: {balance} {chain_info[\"symbol\"]}, need {needed}\")',
            '                # Try to request from faucet up to 3 times',
            '                for attempt in range(3):',
            '                    if self._request_faucet(self.current_chain, address):',
            '                        # Wait a bit for the transaction to be mined',
            '                        time.sleep(15)',
            '                        balance = self.get_balance(address)',
            '                        if balance >= needed:',
            '                            log_ok(f\"Balance after faucet: {balance} {chain_info[\"symbol\"]}\")',
            '                            return True',
            '                    else:',
            '                        if attempt < 2:',
            '                            time.sleep(10)',
            '                log_err(f\"Failed to obtain sufficient funds from faucet after {attempt+1} attempts\")',
            '            else:',
            '                log_warn(f\"Not a testnet or faucet not enabled for {self.current_chain}\")',
            '        except Exception as e:',
            '            log_err(f\"Error checking balance: {e}\")',
            '        return False',
        ]
        # Insert each line at position scheduler_start
        for i, line in enumerate(method_lines):
            lines.insert(scheduler_start + i, line)
        # Update scheduler_start to account for the inserted lines (if we need to insert more later, but we don't)
        # We'll just note that the Scheduler class is now shifted down.

    # 5. Modify the transaction methods to call _ensure_minimum_balance at the start
    # We'll patch the following methods: send_native, wrap_native, unwrap_native, swap_native_to_token
    # For each, we'll insert after the docstring (if any) and after the method signature.
    def insert_check_at_method_start(lines, method_name):
        for i, line in enumerate(lines):
            if line.strip().startswith(f'def {method_name}(self,'):
                # Find the line after the docstring (if any) or the first line of the function
                j = i + 1
                while j < len(lines) and (lines[j].strip().startswith('\"\"\"') or lines[j].strip() == ''):
                    j += 1
                # Now insert at j
                indent = len(lines[j]) - len(lines[j].lstrip())
                check_line = ' ' * indent + 'if not self._ensure_minimum_balance(wallet, amount_ether):\n'
                check_line2 = ' ' * indent + '    raise ValueError(\"Insufficient funds and faucet failed\")\n'
                lines.insert(j, check_line2)
                lines.insert(j, check_line)
                return True
        return False

    methods_to_patch = ['send_native', 'wrap_native', 'unwrap_native', 'swap_native_to_token']
    for method in methods_to_patch:
        if not insert_check_at_method_start(lines, method):
            print(f'Warning: Could not find method {method} to patch', file=sys.stderr)

    # Write back
    write_lines('onchain_bot.py', lines)
    print('Updated onchain_bot.py')

if __name__ == '__main__':
    import json
    main()
