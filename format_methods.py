#!/usr/bin/env python3
"""Extract the two inline methods, format them with black, and reconstruct the file."""

import subprocess
import os

# Read backup
with open('onchain_bot.py.bak', 'r') as f:
    lines = f.readlines()

monster = lines[1818]

# Find split points
idx_balance = monster.find('    def _ensure_minimum_balance')
idx_scheduler = monster.find('class Scheduler:')

raw_faucet = monster[:idx_balance].rstrip()
raw_balance = monster[idx_balance:idx_scheduler].rstrip()

print(f"Faucet raw: {len(raw_faucet)} chars")
print(f"Balance raw: {len(raw_balance)} chars")

# Wrap each method in a minimal valid module and run black
def format_with_black(code, label):
    """Wrap code in a dummy class, format with black, extract the method."""
    wrapper = f"class _Dummy:\n"
    for line in code.split('\n'):
        wrapper += f"    {line}\n"
    
    tmpfile = f'_tmp_{label}.py'
    outfile = f'_tmp_{label}_out.py'
    
    with open(tmpfile, 'w') as f:
        f.write(wrapper)
    
    result = subprocess.run(
        ['python3', '-m', 'black', tmpfile, '--quiet'],
        capture_output=True, text=True,
        timeout=30
    )
    
    if result.returncode != 0:
        print(f"  black ERROR for {label}: {result.stderr[:200]}")
        return code
    
    # Read formatted output and extract just the method body
    with open(tmpfile, 'r') as f:
        formatted = f.read()
    
    # Extract lines that were inside _Dummy
    # Remove the class header and dedent
    formatted_lines = formatted.split('\n')
    method_lines = []
    for line in formatted_lines:
        # Skip class _Dummy: line (first) and empty
        if line.startswith('class _Dummy:') or line.strip() == '':
            continue
        # Remove the 4-space class indent
        if line.startswith('    '):
            method_lines.append(line[4:])
    
    os.remove(tmpfile)
    
    result = '\n'.join(method_lines)
    print(f"  Formatted {label}: {len(result)} chars, {result.count(chr(10))+1} lines")
    return result

formatted_faucet = format_with_black(raw_faucet, 'faucet')
formatted_balance = format_with_black(raw_balance, 'balance')

print(f"\n--- faucet result (first 300 chars) ---")
print(formatted_faucet[:300])
print(f"\n--- balance result (first 300 chars) ---")
print(formatted_balance[:300])

# Now reconstruct the file
# We have:
# lines[0..1817] unchanged
# lines[1818] = monster line (to replace)
# lines[1819] = '' (empty)
# lines[1820] = '' (empty - but originally was the _ensure_minimum_balance line)
# Actually, after the backup restore, the monster line is back at line 1818.
# Let's check what lines 1818-1823 look like

print(f"\n--- Current state ---")
for i in range(1815, 1825):
    print(f"  {i+1}: {lines[i][:100]!r}")