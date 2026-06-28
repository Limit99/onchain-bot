import sys
import re

with open('onchain_bot.py', 'r') as f:
    lines = f.readlines()

# 1. Add imports for urllib and requests (try/except)
# Find the line after the last import (after 'from decimal import Decimal')
insert_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith('from decimal import Decimal'):
        insert_idx = i+1
        break
if insert_idx is not None:
    lines.insert(insert_idx, '\n')
    lines.insert(insert_idx+1, '# For faucet functionality\n')
    lines.insert(insert_idx+2, 'try:\n')
    lines.insert(insert_idx+3, '    import requests\n')
    lines.insert(insert_idx+4, 'except ImportError:\n')
    lines.insert(insert_idx+5, '    requests = None\n')
    lines.insert(insert_idx+6, '\n')

# 2. Find the BlockchainEngine class and its __init__ method to add faucet state
class_start = None
for i, line in enumerate(lines):
    if line.strip().startswith('class BlockchainEngine:'):
        class_start = i
        break
if class_start is not None:
    init_start = None
    for i in range(class_start, len(lines)):
        if lines[i].strip().startswith('def __init__(self, config: Config):'):
            init_start = i
            break
    if init_start is not None:
        # Find where self._load_history() is called
        for i in range(init_start, len(lines)):
            if 'self._load_history()' in lines[i]:
                indent = len(lines[i]) - len(lines[i].lstrip())
                # Insert after this line
                lines.insert(i+1, ' ' * indent + '        # Faucet-related state\n')
                lines.insert(i+2, ' ' * indent + '        self._faucet_last_request = {}\n')
                break

# 3. Add _request_faucet method after __init__
# Find the line after __init__ ends (look for next 'def ' at same indent level)
def_after_init = None
for i in range(init_start, len(lines)):
    if i > init_start and lines[i].strip().startswith('def ') and not lines[i].strip().startswith('def _'):
        # Check if it's at class level (indent 4 spaces)
        if len(lines[i]) - len(lines[i].lstrip()) == 4:
            def_after_init = i
            break
if def_after_init is not None:
    # Insert our method before this def
    indent = '    '
    method_lines = [
        '',
        '    def _request_faucet(self, chain_name: str, address: str) -> bool:',
        '        """Attempt to get funds from a faucet for the given address on the given chain."""',
        '        # Faucet configurations: key = chain name as in config',
        '        FAUCETS = {',
        '            "Sepolia": {',
        '                "url": "https://sepolia-faucet.pk910.de/",',
        '                "method": "POST",',
        '                "headers": {"Content-Type": "application/json"},',
        '                "data": lambda addr: {"address": addr},',
        '            },',
        '            "Polygon Amoy": {',
        '                "url": "https://faucet.polygon.technology/",',
        '                "method": "POST",',
        '                "headers": {"Content-Type": "application/json"},',
        '                "data": lambda addr: {"address": addr},',
        '            },',
        '            "Arbitrum Sepolia": {',
        '                "url": "https://arbitrum-sepolia.faucet.arbitrum.io/",',
        '                "method": "POST",',
        '                "headers": {"Content-Type": "application/json"},',
        '                "data": lambda addr: {"address": addr},',
        '            },',
        '            "Optimism Sepolia": {',
        '                "url": "https://opsepolia-fuel.com/",',
        '                "method": "POST",',
        '                "headers": {"Content-Type": "application/json"},',
        '                "data": lambda addr: {"address": addr},',
        '            },',
        '            # Add more faucets as needed',
        '        }',
        '        if chain_name not in FAUCETS:',
        '            log_warn(f"No faucet configured for {chain_name}")',
        '            return False',
        '        conf = FAUCETS[chain_name]',
        '        url = conf["url"]',
        '        method = conf.get("method", "GET").upper()',
        '        headers = conf.get("headers", {})',
        '        data_func = conf.get("data")',
        '        if data_func is None:',
        '            data = None',
        '        else:',
        '            data = data_func(address)',
        '        # Rate limiting: wait at least 1 minute between requests per address',
        '        now = time.time()',
        '        last = self._faucet_last_request.get((chain_name, address), 0)',
        '        if now - last < 60:',
        '            wait = int(60 - (now - last))',
        '            log_info(f"Faucet rate limit: waiting {wait}s before next request for {address} on {chain_name}")',
        '            time.sleep(wait)',
        '        try:',
        '            if requests is not None:',
        '                if method == "POST":',
        '                    resp = requests.post(url, json=data, headers=headers, timeout=30)',
        '                else:',
        '                    resp = requests.get(url, params=data, headers=headers, timeout=30)',
        '                if resp.status_code in (200, 201, 202):',
        '                    log_ok(f"Faucet request successful for {address} on {chain_name}")',
        '                    self._faucet_last_request[(chain_name, address)] = time.time()',
        '                    return True',
        '                else:',
        '                    log_err(f"Faucet request failed: {resp.status_code} {resp.text[:200]}")',
        '            else:',
        '                # Fallback to urllib',
        '                import urllib.request',
        '                import urllib.error',
        '                data_encoded = None',
        '                if data is not None:',
        '                    if method == "POST":',
        '                        data_encoded = json.dumps(data).encode("utf-8")',
        '                    else:',
        '                        # For GET, we would need to append to URL - skip for simplicity',
        '                        log_warn("GET with data not supported in fallback, skipping faucet")',
        '                        return False',
        '                req = urllib.request.Request(url, data=data_encoded, headers=headers, method=method)',
        '                try:',
        '                    with urllib.request.urlopen(req, timeout=30) as resp:',
        '                        if 200 <= resp.status < 300:',
        '                            log_ok(f"Faucet request successful for {address} on {chain_name}")',
        '                            self._faucet_last_request[(chain_name, address)] = time.time()',
        '                            return True',
        '                except urllib.error.HTTPError as e:',
        '                    log_err(f"Faucet request failed: {e.code} {e.read()[:200]}")',
        '                except Exception as e:',
        '                    log_err(f"Faucet request error: {e}")',
        '        except Exception as e:',
        '            log_err(f"Faucet request error: {e}")',
        '        return False',
    ]
    for i, line in enumerate(method_lines):
        lines.insert(def_after_init + i, line)
    # Update def_after_init to point to the next original method (shifted by len(method_lines))
    def_after_init += len(method_lines)

# 4. Add _ensure_minimum_balance method after _request_faucet
# Find the next 'def ' after _request_faucet
def_after_faucet = None
for i in range(def_after_init, len(lines)):
    if i > def_after_init and lines[i].strip().startswith('def ') and not lines[i].strip().startswith('def _'):
        if len(lines[i]) - len(lines[i].lstrip()) == 4:
            def_after_faucet = i
            break
if def_after_faucet is not None:
    indent = '    '
    method_lines = [
        '',
        '    def _ensure_minimum_balance(self, wallet: dict, amount_ether: Decimal, min_balance: Decimal = Decimal("0.001")) -> bool:',
        '        """Ensure the wallet has enough balance for the transaction plus a minimum buffer."""',
        '        if self.w3 is None:',
        '            return False',
        '        address = wallet["address"]',
        '        try:',
        '            balance = self.get_balance(address)',
        '            needed = amount_ether + min_balance',
        '            if balance >= needed:',
        '                return True',
        '            # Balance too low, try to get from faucet if on testnet',
        '            chain_info = self._chain_info()',
        '            if chain_info.get("type") == "testnet":',
        '                log_warn(f"Low balance on {self.current_chain}: {balance} {chain_info[\"symbol\"]}, need {needed}")',
        '                # Try to request from faucet up to 3 times',
        '                for attempt in range(3):',
        '                    if self._request_faucet(self.current_chain, address):',
        '                        # Wait a bit for the transaction to be mined',
        '                        time.sleep(15)',
        '                        balance = self.get_balance(address)',
        '                        if balance >= needed:',
        '                            log_ok(f"Balance after faucet: {balance} {chain_info[\"symbol\"]}")',
        '                            return True',
        '                    else:',
        '                        if attempt < 2:',
        '                            time.sleep(10)',
        '                log_err(f"Failed to obtain sufficient funds from faucet after {attempt+1} attempts")',
        '            else:',
        '                log_warn(f"Not a testnet or faucet not enabled for {self.current_chain}")',
        '        except Exception as e:',
        '            log_err(f"Error checking balance: {e}")',
        '        return False',
    ]
    for i, line in enumerate(method_lines):
        lines.insert(def_after_faucet + i, line)
    # Update def_after_faucet for next insertion
    def_after_faucet += len(method_lines)

# 5. Modify transaction methods to call _ensure_minimum_balance
# List of methods to modify
methods_to_patch = ['send_native', 'wrap_native', 'unwrap_native', 'swap_native_to_token', 'swap_token_to_native', 'swap_token_to_token']
for method_name in methods_to_patch:
    for i, line in enumerate(lines):
        if line.strip().startswith(f'def {method_name}(self,'):
            # Find the line after the docstring (if any) or the first line of the function
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith('"""') or lines[j].strip() == ''):
                j += 1
            # Now insert after the function signature and docstring
            indent = len(lines[j]) - len(lines[j].lstrip())
            check_line = ' ' * indent + 'if not self._ensure_minimum_balance(wallet, amount_ether):\n'
            check_line2 = ' ' * indent + '    raise ValueError("Insufficient funds and faucet failed")\n'
            lines.insert(j, check_line2)
            lines.insert(j, check_line)
            break  # only first occurrence

# 6. Also, we might want to improve error handling in _build_and_send by adding retry on certain errors?
# For now, we'll leave it as is.

# Write back
with open('onchain_bot.py', 'w') as f:
    f.writelines(lines)
print('Modified onchain_bot.py')
