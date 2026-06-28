#!/usr/bin/env python3
"""Fix the monster line 1819 in onchain_bot.py."""

import os, shutil

filepath = 'onchain_bot.py'
backup = 'onchain_bot.py.bak'

shutil.copy2(filepath, backup)
print(f"Backup: {backup}")

with open(filepath, 'r') as f:
    content = f.read()

lines = content.split('\n')
monster = lines[1818]

idx_balance = monster.find("    def _ensure_minimum_balance")
idx_scheduler = monster.find("class Scheduler:")

part1 = monster[:idx_balance].rstrip()
part2 = monster[idx_balance:idx_scheduler].rstrip()
part3 = "class Scheduler:"  # just the class header

print(f"Part 1 (_request_faucet): {len(part1)} chars")
print(f"Part 2 (_ensure_min_bal): {len(part2)} chars")
print(f"Part 3 (class Scheduler): `{part3}`")

# Check: does part1 end with proper indentation to be a method body?
# _request_faucet should end with "        return False"
print(f"Part 1 ends with: {part1[-80:]!r}")
print(f"Part 2 ends with: {part2[-80:]!r}")

# Replace the monster line
lines[1818] = part1 + '\n\n' + part2 + '\n\n' + part3

new_content = '\n'.join(lines)
with open(filepath, 'w') as f:
    f.write(new_content)

new_lines = new_content.split('\n')
print(f"\nNew total lines: {len(new_lines)}")
print("Done!")