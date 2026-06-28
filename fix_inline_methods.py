#!/usr/bin/env python3
"""Expand inline methods at lines 1819 and 1821 into proper multi-line code."""
import re

with open('onchain_bot.py', 'r') as f:
    lines = f.readlines()

faucet_line = lines[1818].rstrip('\n')
balance_line = lines[1820].rstrip('\n')

print(f"Faucet line: {len(faucet_line)} chars")
print(f"Balance line: {len(balance_line)} chars")

def expand_method(line):
    """Expand a single-line method into proper multi-line format."""
    # Find the body start: the last colon followed by 8+ spaces
    # This should be the signature's closing colon before body
    matches = list(re.finditer(r':(\s{8,})', line))
    if not matches:
        return line
    
    # Use the LAST match with enough spaces that's plausible as a body separator
    # Filter: only consider ones after the return type (->)
    sig_end_idx = line.find('):')
    if sig_end_idx == -1:
        sig_end_idx = 0
    
    eligible = [m for m in matches if m.start() >= sig_end_idx]
    if not eligible:
        return line
    
    last = eligible[-1]
    sig = line[:last.start()].rstrip() + ':'
    body = line[last.end():]
    
    # Now expand body: split at 8+ space boundaries (not inside strings)
    # Strategy: track nesting and use statement boundary heuristics
    
    indent_unit = '    '  # 4 spaces
    result = [sig]
    
    # Process body: each statement starts after a multi-space gap
    # that's a multiple of 4 spaces (indent level)
    pos = 0
    while pos < len(body):
        # Count leading spaces
        spaces = 0
        while pos < len(body) and body[pos] == ' ':
            spaces += 1
            pos += 1
        
        if pos >= len(body):
            break
        
        # Determine indent level
        indent_level = spaces // 4  # Level 2 = inside method (8 spaces from def)
        
        # Read until we hit another 8+ space boundary, handling nesting
        stmt_start = pos
        nesting = 0
        in_quote = False
        quote_char = None
        prev_was_space_block = False
        
        while pos < len(body):
            ch = body[pos]
            
            # Handle quotes
            if not in_quote:
                if ch in ('"', "'"):
                    # Check for triple quotes
                    if pos+2 < len(body) and body[pos:pos+3] == ch*3:
                        in_quote = True
                        quote_char = ch*3
                        pos += 3
                        continue
                    else:
                        in_quote = True
                        quote_char = ch
                elif ch == '(' or ch == '[' or ch == '{':
                    nesting += 1
                elif ch == ')' or ch == ']' or ch == '}':
                    nesting -= 1
            else:
                if len(quote_char) == 3 and body[pos:pos+3] == quote_char:
                    in_quote = False
                    pos += 3
                    continue
                elif len(quote_char) == 1 and ch == quote_char and (pos == 0 or body[pos-1] != '\\'):
                    in_quote = False
            
            # Check for statement boundary: 8+ spaces at nesting 0
            if not in_quote and nesting == 0 and ch == ' ':
                # Look ahead to see if there are 8+ consecutive spaces
                sp_count = 0
                sp_pos = pos
                while sp_pos < len(body) and body[sp_pos] == ' ':
                    sp_count += 1
                    sp_pos += 1
                
                if sp_count >= 8 and sp_pos < len(body):
                    # We found a statement boundary!
                    # Extract the statement up to here
                    stmt_text = body[stmt_start:pos]
                    if stmt_text.strip():
                        result.append(indent_unit * indent_level + stmt_text.strip())
                    pos = sp_pos
                    stmt_start = pos
                    continue
            
            pos += 1
        
        # Last statement
        stmt_text = body[stmt_start:pos]
        if stmt_text.strip():
            result.append(indent_unit * indent_level + stmt_text.strip())
    
    return '\n'.join(result)

for idx, (line_name, original) in enumerate([
    ('_request_faucet', faucet_line),
    ('_ensure_minimum_balance', balance_line)
]):
    expanded = expand_method(original)
    print(f"\n=== {line_name} ===")
    print(f"Original: {len(original)} chars")
    print(f"Expanded: {len(expanded)} chars, {expanded.count(chr(10))+1} lines")
    print("Result:")
    print(expanded[:500])
    print("...")
    print(expanded[-500:])
    
    if idx == 0:
        lines[1818] = expanded
    else:
        lines[1820] = expanded

# Write back
with open('onchain_bot.py', 'w') as f:
    f.write('\n'.join(lines))

print("\nWritten! Now verifying...")

# Verify syntax
import ast
content = '\n'.join(lines)
try:
    ast.parse(content)
    print("SYNTAX OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR at line {e.lineno}: {e.msg}")

# Check classes
tree = ast.parse(content)
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
print(f"Classes: {classes}")