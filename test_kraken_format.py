#!/usr/bin/env python
"""Test Kraken CRC format."""

# From Kraken docs, the first ask is:
# {"price": "45285.2", "qty": "0.00100000"}

# Let me trace through exactly what Kraken does:
price_json = "45285.2"  # As Kraken sends it in JSON
size_json = "0.00100000"  # As Kraken sends it in JSON

# Remove decimals
price_no_dec = price_json.replace('.', '')
size_no_dec = size_json.replace('.', '')

print(f"Price (from JSON): {price_json} -> {price_no_dec}")
print(f"Size (from JSON):  {size_json} -> {size_no_dec}")
print(f"Combined: {price_no_dec + size_no_dec}")
print()

# Kraken's expected string starts with: 452852100000
# But we get: 4528520001000000
# Difference: 452852100000 vs 4528520001000000

# Wait... let me check if the size has leading zeros
print("If I interpret '0.00100000' as:")
print("  Option 1: Remove decimal point only -> '0001000000'")
print("  Option 2: Remove decimal AND leading zeros -> '10000000'")
print()
print("Kraken expected: '452852100000' (12 chars)")
print("My result:      '4528520001000000' (16 chars)")
print()
print("Hmm, the expected 12 chars suggests:")
print("  '452852' (6 chars) + '100000' (6 chars)")
print()
print("But '0.00100000'.replace('.', '') = '0001000000' (10 chars)")
print()
print("Unless Kraken is doing something different with the size...")

# Let me check: what if they format size as 8 decimal places
# but without the leading zero before decimal?
size_formatted = f'{float(size_json):.8f}'
print(f"\nSize formatted to 8 decimals: {size_formatted}")
print(f"Remove decimal: {size_formatted.replace('.','')}")

# What if they drop the leading zero entirely?
size_no_leading_zero = size_json.lstrip('0').replace('.', '')
print(f"\nSize with leading zero stripped: {size_json} -> {size_no_leading_zero}")
print(f"Combined: {price_no_dec + size_no_leading_zero}")

# That would give: 452852 + 10000000 = 45285210000000 (14 chars)
# Still not 12 chars!

# Let me try another interpretation: what if they use 6 decimal places for size?
size_6_dec = f'{float(size_json):.6f}'.replace('.', '')
print(f"\nSize at 6 decimals: {size_6_dec}")

# 0.001000 -> 0001000 (7 chars)
# Combined: 452852 + 0001000 = 4528520001000 (13 chars) - close!
