#!/usr/bin/env python3
"""
Final fix for onchain_bot.py: expand inline methods at line 1819.

The monster line 1819 (5770 chars) contains 3 things:
  1. _request_faucet method (4082 chars, inline)
  2. _ensure_minimum_balance method (1671 chars, inline)
  3. class Scheduler: (at the end, no newline)

Line 1820-1824 contain Scheduler's docstring (already separate).
Line 1826 contains Scheduler's __init__ (already separate, but orphaned).

Fix approach:
  1. Split monster line into the 3 components
  2. Expand each inline method into proper multi-line code
     by adding newlines at statement boundaries
  3. Insert "class Scheduler:" as a standalone line
  4. Rejoin everything
"""

import re
import ast
import shutil
import sys

backup_file = 'onchain_bot.py.bak'
target_file = 'onchain_bot.py'

# Step 1: Read the backup (which still has the monster line)
with open(backup_file, 'r') as f:
    content = f.read()
    lines = content.split('\n')

print(f"Total lines: {len(lines)}")
monster = lines[1818]
print(f"Monster line: {len(monster)} chars")

# Step 2: Split monster line
idx_balance = monster.find('    def _ensure_minimum_balance')
idx_scheduler = monster.find('class Scheduler:')

print(f"Split points: balance@{idx_balance}, scheduler@{idx_scheduler}")

raw_faucet = monster[:idx_balance].rstrip()
raw_balance = monster[idx_balance:idx_scheduler].rstrip()

print(f"Faucet raw: {len(raw_faucet)} chars")
print(f"Balance raw: {len(raw_balance)} chars")


def find_body_boundary(line_text):
    """
    Find where the method signature ends and body begins.
    Returns (signature, body).
    
    Signature pattern: spaces + 'def name(params) -> type:'
    Body starts after ':' + 8+ spaces.
    
    We find the FIRST colon after ') -> type:' part that's followed by 8+ spaces.
    """
    # Normalize: remove trailing newline
    line = line_text.rstrip('\n')
    
    # Find the '):' that closes the param list
    # The signature ends with '):' or ') -> type:'
    # Look for the pattern ') ... :' where the colon has 8+ spaces after
    
    # Strategy: find the colon that's part of the def signature
    # The def line starts with spaces + 'def '
    # Find all colons with 8+ spaces after them
    matches = list(re.finditer(r':( {8,})', line))
    
    # We need to find the one that's AFTER the closing paren of the def
    # Find the last ')' that looks like it closes the parameter list
    # The pattern is typically: def name(self, ...) -> type:
    
    # The key: the def sig ends with '):' or ') -> type:'
    # Find the colon that has 8+ spaces after, and is preceded by a ')'
    # within a reasonable distance (< 20 chars)
    
    def_colon = None
    for m in matches:
        # Check if this colon is preceded by ')' somewhere nearby
        before = line[max(0, m.start()-25):m.start()]
        if ')' in before and not '(' in before[before.rfind(')'):]:
            # This looks like the def signature colon
            def_colon = m
            break
    
    if def_colon is None:
        # Fallback: use the first match that's after the first ')'
        first_close_paren = line.find(')')
        if first_close_paren >= 0:
            for m in matches:
                if m.start() > first_close_paren:
                    def_colon = m
                    break
    
    if def_colon is None:
        return line_text, ''
    
    spaces_after = len(def_colon.group(1))
    signature = line[:def_colon.start()].rstrip() + ':'
    body = line[def_colon.end():]
    
    return signature, body


def expand_body(body, base_spaces):
    """
    Take a flat inline body (no newlines) and expand it into proper
    multi-line indented code.
    
    base_spaces: the baseline indent for method body (e.g., 8 spaces from def)
    
    The body uses spaces to simulate indentation. Within the body:
    - Indent level 0: base_spaces from def (method body level)
    - Indent level 1: base_spaces + 4 (inside if/for/try)
    - Indent level 2: base_spaces + 8 (inside nested if/for)
    - etc.
    
    Each "statement" in the inline body is preceded by its indent level in spaces.
    Statements are delimited by the next statement at the SAME or LOWER indent level.
    """
    if not body.strip():
        return ''
    
    # Normalize: remove leading/trailing whitespace
    body = body.strip()
    
    # Build the result as a list of (indent_level, code) tuples
    result = []
    
    # We'll parse statement by statement
    # Each statement starts at a certain indent level (in spaces from body start)
    # and continues until we hit another statement at the same or lower level
    
    indent_unit = 4  # 4 spaces per indent level
    margin = 0  # body starts at column 0 relative to body scope
    
    pos = 0
    body_len = len(body)
    
    while pos < body_len:
        # Count leading spaces (relative to body start)
        spaces = 0
        while pos < body_len and body[pos] == ' ':
            spaces += 1
            pos += 1
        
        if pos >= body_len:
            break
        
        # Calculate indent level: base level + (spaces / 4)
        # But spaces are relative to body start (which is at base_spaces from def)
        # So indent 0 inside body = spaces 0 = 8 spaces from def
        # indent 1 inside body = spaces 4 = 12 spaces from def
        
        indent_from_body = spaces  # 0 = method body level, 4 = first indent, etc.
        level = indent_from_body // indent_unit
        
        # Now extract this statement
        stmt_start = pos
        
        # Track nesting to know when this statement ends
        nesting = 0  # (, [, {
        in_quote = False
        quote_char = None
        stmt_end = body_len
        
        i = pos
        while i < body_len:
            ch = body[i]
            
            # Handle quotes (simple and triple)
            if not in_quote:
                if ch in ('"', "'"):
                    if i+2 < body_len and body[i:i+3] in ('"""', "'''"):
                        in_quote = True
                        quote_char = body[i:i+3]
                        i += 3
                        continue
                    else:
                        in_quote = True
                        quote_char = ch
                elif ch in ('(', '[', '{'):
                    nesting += 1
                elif ch in (')', ']', '}'):
                    nesting -= 1
            else:
                # Try to close quote
                if len(quote_char) == 3 and body[i:i+3] == quote_char:
                    in_quote = False
                    i += 3
                    continue
                elif len(quote_char) == 1 and ch == quote_char and (i == 0 or body[i-1] != '\\'):
                    in_quote = False
            
            # Check for statement boundary (nesting=0, not in quote)
            if not in_quote and nesting == 0 and ch == ' ':
                # Look ahead for multiple spaces that could be a boundary
                # A boundary is 4+ consecutive spaces followed by a non-space
                j = i
                while j < body_len and body[j] == ' ':
                    j += 1
                sp_count = j - i
                
                if sp_count >= 4 and j < body_len:
                    # Check if this looks like a new statement at the same level
                    # or if it's just spacing within a string/expression
                    # 
                    # A new statement boundary at level 0 = 4+ spaces
                    # (because 4 spaces = one indent level from body)
                    
                    # BUT: we need to be smart - some 4-space blocks are just
                    # continuation of the same statement (e.g., the FAUCETS dict
                    # uses 12-space indentation inside the dict literal)
                    
                    # Key insight: if we're at nesting=0, the only way to have
                    # 4+ spaces is it's a statement boundary
                    # 
                    # Exception: inline comments like "# Add more..."
                    # But those are comments, they don't change nesting
                    
                    # Let's check what's at position j
                    next_ch = body[j]
                    if next_ch.isalnum() or next_ch in ('"', "'", '#', '@', '.'):
                        # This IS a statment boundary
                        stmt_end = i
                        pos = i  # We'll re-enter the loop and count spaces again
                        break
            
            i += 1
            pos = i
    
    # Hmm, this approach is getting complex. Let me try a much simpler approach.
    # I'll just insert newlines at positions where we see `        ` (8 spaces) or `            ` (12 spaces)
    # patterns that indicate statement boundaries, while being careful about strings.
    
    # Actually, let me try the simplest possible approach:
    # Replace all occurrences of specific space-count patterns that appear at 
    # statement boundaries with newline + same spaces
    
    # The body has statements at:
    # - Indent 0 (from body): 0 initial spaces (body_start column)
    # - Indent 1: 4 spaces 
    # - Indent 2: 8 spaces
    # 
    # But these are RELATIVE to the body start, which is `base_spaces` from def.
    # 
    # In the raw text, the body looks like:
    # '"""doc"""        statement1        if ...:            sub_stmt        statement2'
    # 
    # Between statements at the same level, there are `base_spaces` (e.g., 8) spaces.
    # 
    # Actually no. Let me look at the raw text more carefully.
    
    return body  # placeholder


# Let me try an even simpler approach: just use the fact that
# in the inline body, each "statement group" is separated by 
# 8+ consecutive spaces, and statement groups at indent 1+ 
# have specific space counts.

# Let me look at the actual content
print("\n=== Body structure analysis ===")

sig_f, body_f = find_body_boundary(raw_faucet)
sig_b, body_b = find_body_boundary(raw_balance)

print(f"\nFaucet signature: {sig_f[:100]}...")
print(f"Faucet body: {len(body_f)} chars")
print(f"  Body first 200: {body_f[:200]!r}")
print(f"  Body last 200: {body_f[-200:]!r}")

print(f"\nBalance signature: {sig_b[:100]}...")
print(f"Balance body: {len(body_b)} chars")
print(f"  Body first 200: {body_b[:200]!r}")

# Print all space-bounded segments in the body
def show_segments(body, label):
    # Split on 4+ spaces
    segs = re.split(r'( {4,})', body)
    print(f"\n--- {label} segments ---")
    i = 0
    while i < len(segs):
        s = segs[i]
        if s.startswith(' ') and len(s) >= 4:
            # This is a spacer
            nl = len(s)
            if i+1 < len(segs):
                print(f"  [indent +{nl}] {segs[i+1][:120]}")
            i += 2
        else:
            print(f"  [body] {s[:120]}")
            i += 1

show_segments(body_f, 'faucet')
show_segments(body_b, 'balance')

# Now let me write a proper expander
def expand_body_simple(body):
    """
    Expand inline body by inserting newlines at 4+ space boundaries.
    
    In the inline format, the body code has NO newlines. The indentation
    structure is encoded by multiple consecutive spaces.
    
    Indent pattern (relative to def line):
    - 0 spaces = body level (inside method)
    - 4 spaces = first sub-indent (inside if/for/try)
    - 8 spaces = second sub-indent
    - etc.
    
    BUT: the actual raw body text might start right after the def colon+spaces,
    and the body content uses various space counts.
    
    Let me try splitting at 4-space boundaries where they indicate real indentation.
    """
    # The body is a continuous string. We'll rebuild it by scanning.
    
    indent_unit = 4
    
    # First, find all anchor points: positions where we see 4+ spaces
    # at nesting=0 that indicate a statement boundary.
    
    # But this is fragile with dict literals having their own space-based indentation.
    # The FAUCETS dict in _request_faucet uses 12-space indentation inside the dict,
    # which happens to be one indent level. But it's inside braces {} so nesting != 0.
    
    # BETTER APPROACH: 
    # 1. Replace all 4-space boundaries that are at nesting=0 with newline+spaces
    # 2. Track nesting through () [] {} and quotes
    
    result_parts = []
    i = 0
    body_len = len(body)
    nesting = 0
    in_quote = False
    quote_char = None
    
    current_line = ''
    
    while i < body_len:
        ch = body[i]
        
        # Quote tracking
        if not in_quote:
            if ch in ('"', "'"):
                # Check for triple quote
                if i+2 < body_len and body[i:i+3] in ('"""', "'''"):
                    in_quote = True
                    quote_char = body[i:i+3]
                    current_line += ch
                    i += 1
                    continue
                else:
                    in_quote = True
                    quote_char = ch
            elif ch in ('(', '[', '{'):
                nesting += 1
            elif ch in (')', ']', '}'):
                nesting -= 1
        
        else:
            # Check for quote close
            if len(quote_char) == 3 and body[i:i+3] == quote_char:
                in_quote = False
                current_line += quote_char
                i += 3
                continue
            elif len(quote_char) == 1 and ch == quote_char and (i == 0 or body[i-1] != '\\'):
                in_quote = False
        
        # Check for 4+ space boundary at nesting=0
        if not in_quote and nesting == 0 and ch == ' ':
            # Check if this is a boundary (4+ consecutive spaces)
            j = i
            while j < body_len and body[j] == ' ':
                j += 1
            sp_count = j - i
            
            if sp_count >= 4 and j < body_len and body[j] != '\n':
                # This is a statement boundary!
                # Flush current line
                if current_line.strip():
                    result_parts.append(current_line.rstrip())
                
                # Determine indent level from spaces
                # The spaces count tells us the indent level
                # But we need to normalize: the body starts at "level 0"
                # and each 4 spaces increases indent by 1
                
                # Hmm, but the body starts at whatever column the def colon ends
                # Let me try: if current_line is empty (start of body), the spaces
                # are relative to body start. Otherwise, spaces are the new indent
                
                indent_level = sp_count // indent_unit  # 4 spaces = level 1, etc.
                actual_indent = indent_level * indent_unit
                
                # The next text at this indent level
                current_line = ' ' * actual_indent
                i = j
                continue
        
        current_line += ch
        i += 1
    
    # Flush last line
    if current_line.strip():
        result_parts.append(current_line.rstrip())
    
    return '\n'.join(result_parts)


# Test
expanded_faucet_body = expand_body_simple(body_f)
print(f"\n=== Expanded faucet body ({len(expanded_faucet_body)} chars) ===")
print(expanded_faucet_body[:1000])
print("...")
print(expanded_faucet_body[-500:])

expanded_balance_body = expand_body_simple(body_b)
print(f"\n=== Expanded balance body ({len(expanded_balance_body)} chars) ===")
print(expanded_balance_body[:1000])
print("...")
print(expanded_balance_body[-500:])