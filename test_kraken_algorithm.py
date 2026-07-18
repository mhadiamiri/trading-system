#!/usr/bin/env python
"""Test Kraken checksum algorithm variations."""

import binascii

# Test data from Kraken docs
test_cases = [
    ("45285.2", "0.00100000"),
    ("0.1", "0.1"),
    ("0.100000", "0.100000"),
]

print("Testing different interpretations of Kraken's format:\n")

for price, size in test_cases:
    print(f"Price: {price}, Size: {size}")

    # Method 1: Simple replace (current)
    m1 = price.replace('.', '') + size.replace('.', '')
    print(f"  Method 1 (simple replace): {m1}")

    # Method 2: Strip leading zeros, then replace
    p_stripped = price.lstrip('0')
    s_stripped = size.lstrip('0')
    m2 = p_stripped.replace('.', '') + s_stripped.replace('.', '')
    print(f"  Method 2 (strip leading zeros): {m2}")

    # Method 3: Replace decimals first, then strip leading zeros from entire string
    m3_raw = price.replace('.', '') + size.replace('.', '')
    m3 = m3_raw.lstrip('0')
    print(f"  Method 3 (replace then strip): {m3}")

    # Method 4: Parse as float, format with precision
    try:
        p_float = float(price)
        s_float = float(size)
        p_formatted = f"{p_float:.8f}".replace('.', '')
        s_formatted = f"{s_float:.8f}".replace('.', '')
        m4 = p_formatted + s_formatted
        print(f"  Method 4 (format to 8 decimals): {m4}")
    except:
        print(f"  Method 4: ERROR")

    print()

# Now let me try to reverse-engineer from Kraken's expected string
target = "452852100000"
print(f"Target string: {target} (len={len(target)})")
print()

# Try to split into price and size
# If price starts with "45285" and has decimal after 2nd digit...
# Price could be "45285.2" -> "452852" (6 chars)
# Then size would be "100000" (6 chars)

price_part = "452852"  # From 45285.2
size_part = "100000"  # Unknown source

print(f"Price part: {price_part} -> 45285.2 ✓")
print(f"Size part: {size_part} -> ???")

# What gives "100000"?
candidates = ["0.1", "0.10", "0.100000", "0.10000000"]
print("\nSize candidates that give '100000':")
for c in candidates:
    result = c.replace('.', '')
    if result == "100000":
        print(f"  {c} -> {result} ✓ MATCH!")
    else:
        print(f"  {c} -> {result}")

# What about stripping?
print("\nWith leading zero stripped:")
for c in candidates:
    stripped = c.lstrip('0')
    result = stripped.replace('.', '')
    if result == "100000":
        print(f"  {c} -> {stripped} -> {result} ✓ MATCH!")

# Test with the full Kraken data
print("\n" + "="*60)
print("Testing full Kraken data with Method 2 (strip leading zeros):")
print("="*60)

kraken_asks = [
    ("45285.2", "0.00100000"),
    ("45286.4", "1.54571953"),
    ("45286.6", "1.54571109"),
    ("45289.6", "1.54560911"),
    ("45290.2", "0.15890660"),
    ("45291.8", "1.54553491"),
    ("45294.7", "0.04454749"),
    ("45296.1", "0.35380000"),
    ("45297.5", "0.09945542"),
    ("45299.5", "0.18772827"),
]

kraken_bids = [
    ("45283.5", "0.10000000"),
    ("45283.4", "1.54582015"),
    ("45282.1", "0.10000000"),
    ("45281.0", "0.10000000"),
    ("45280.3", "1.54592586"),
    ("45279.0", "0.07990000"),
    ("45277.6", "0.03310103"),
    ("45277.5", "0.30000000"),
    ("45277.3", "1.54602737"),
    ("45276.6", "0.15445238"),
]

parts = []
for p, s in kraken_asks:
    p_stripped = p.lstrip('0')
    s_stripped = s.lstrip('0')
    result = p_stripped.replace('.', '') + s_stripped.replace('.', '')
    parts.append(result)
    print(f"Ask: {p} + {s} -> {result[:20]}... (len={len(result)})")

for p, s in kraken_bids:
    p_stripped = p.lstrip('0')
    s_stripped = s.lstrip('0')
    result = p_stripped.replace('.', '') + s_stripped.replace('.', '')
    parts.append(result)
    print(f"Bid: {p} + {s} -> {result[:20]}... (len={len(result)})")

combined = ''.join(parts)
crc = binascii.crc32(combined.encode('ascii'))
print(f"\nMethod 2 CRC: {crc}")
print(f"Expected CRC: 3310070434")
print(f"Match: {crc == 3310070434}")
