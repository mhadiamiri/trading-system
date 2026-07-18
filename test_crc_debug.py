#!/usr/bin/env python
"""Debug CRC formatting."""

# Test format strings
price = 45285.2
size = 0.001

price_formatted = f'{price:.8f}'
size_formatted = f'{size:.8f}'

print(f'Price: {price} -> {price_formatted}')
print(f'Size: {size} -> {size_formatted}')
print()
print(f'Price no decimal: {price_formatted.replace(".", "")}')
print(f'Size no decimal: {size_formatted.replace(".", "")}')
print()
print('Expected price part: 45285200000000 (should match 45285.2)')
print('Expected size part:  00000100 (should match 0.00100000)')
print()
print('From Kraken docs:')
print('Asks string starts with: 452852100000...')
print('This means: 45285.2 + 0.00100000 = 452852 + 1000000')
print()

# Test with full Kraken data
bids = [
    (45283.5, 0.10000000),
    (45283.4, 1.54582015),
]

asks = [
    (45285.2, 0.00100000),
    (45286.4, 1.54571953),
]

parts = []
for p, s in asks:
    price_str = f'{p:.8f}'.replace('.', '')
    size_str = f'{s:.8f}'.replace('.', '')
    parts.append(price_str + size_str)
    print(f'Ask: {p:.8f} + {s:.8f} -> {price_str}{size_str}')

for p, s in bids:
    price_str = f'{p:.8f}'.replace('.', '')
    size_str = f'{s:.8f}'.replace('.', '')
    parts.append(price_str + size_str)
    print(f'Bid: {p:.8f} + {s:.8f} -> {price_str}{size_str}')

result = ''.join(parts)
print()
print(f'First 50 chars: {result[:50]}')
print('Expected starts: 452852000000000000010000000452864000000154571953')
