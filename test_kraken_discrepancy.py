#!/usr/bin/env python
"""Test Kraken checksum with corrected values."""

import binascii

# Test with size 0.1 instead of 0.00100000
price = '45285.2'
size = '0.1'  # Changed from 0.00100000

combined = price.replace('.', '') + size.replace('.', '')
print(f'With size 0.1: {combined} (len={len(combined)})')
print(f'Kraken expected: 452852100000 (len=12)')
print(f'Match: {combined == "452852100000"}')
print()

# Now test with the full data using corrected sizes
asks_corrected = [
    ('45285.2', '0.1'),
    ('45286.4', '1.54571953'),
    ('45286.6', '1.54571109'),
    ('45289.6', '1.54560911'),
    ('45290.2', '0.15890660'),
    ('45291.8', '1.54553491'),
    ('45294.7', '0.04454749'),
    ('45296.1', '0.3538'),  # Truncated
    ('45297.5', '0.09945542'),
    ('45299.5', '0.18772827'),
]

bids_corrected = [
    ('45283.5', '0.1'),
    ('45283.4', '1.54582015'),
    ('45282.1', '0.1'),
    ('45281.0', '0.1'),
    ('45280.3', '1.54592586'),
    ('45279.0', '0.0799'),  # Truncated
    ('45277.6', '0.03310103'),
    ('45277.5', '0.3'),
    ('45277.3', '1.54602737'),
    ('45276.6', '0.15445238'),
]

# Build the strings
parts = []
for p, s in asks_corrected:
    parts.append(p.replace('.', '') + s.replace('.', ''))
for p, s in bids_corrected:
    parts.append(p.replace('.', '') + s.replace('.', ''))

result = ''.join(parts)
crc = binascii.crc32(result.encode('ascii'))

print(f'Computed with corrected sizes: {crc}')
print(f'Expected:                        3310070434')
print(f'Match: {crc == 3310070434}')
