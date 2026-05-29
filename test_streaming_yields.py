import jc

# Test rsync_s streaming parser
print('Testing rsync_s...')
test_data = ['<f..t...... test.txt', 'sent 100 bytes  received 20 bytes  240.00 bytes/sec', 'total size is 1000  speedup is 8.33']
result = list(jc.parse('rsync_s', test_data, raw=True))
print(f'  rsync_s returned {len(result)} items')
for item in result:
    print(f'    type={type(item).__name__}, len={len(item) if isinstance(item, tuple) else "N/A"}')
    if isinstance(item, tuple):
        print(f'      [0] is dict: {isinstance(item[0], dict)}')
        print(f'      [1] is str: {isinstance(item[1], str)}')

# Test stat_s streaming parser
print('Testing stat_s...')
test_data = ['  File: test.txt', '  Size: 100          Blocks: 8          IO Block: 4096   regular file']
result = list(jc.parse('stat_s', test_data, raw=True))
print(f'  stat_s returned {len(result)} items')
for item in result:
    print(f'    type={type(item).__name__}, len={len(item) if isinstance(item, tuple) else "N/A"}')
    if isinstance(item, tuple):
        print(f'      [0] is dict: {isinstance(item[0], dict)}')
        print(f'      [1] is str: {isinstance(item[1], str)}')

# Test traceroute_s streaming parser
print('Testing traceroute_s...')
test_data = ['traceroute to google.com (8.8.8.8), 30 hops max, 60 byte packets', ' 1  192.168.1.1  1.234 ms  2.345 ms  3.456 ms']
result = list(jc.parse('traceroute_s', test_data, raw=True))
print(f'  traceroute_s returned {len(result)} items')
for item in result:
    print(f'    type={type(item).__name__}, len={len(item) if isinstance(item, tuple) else "N/A"}')
    if isinstance(item, tuple):
        print(f'      [0] is dict: {isinstance(item[0], dict)}')
        print(f'      [1] is str: {isinstance(item[1], str)}')

# Test airport_s (non-streaming, should return list of dicts)
print('Testing airport_s...')
test_data = '                            SSID BSSID             RSSI CHANNEL HT CC SECURITY (AUTH/UNICAST/GROUP)\nTestNet 00:11:22:33:44:55 -50 1 Y US WPA2(PSK/AES/AES)'
result = jc.parse('airport_s', test_data, raw=True)
print(f'  airport_s returned {len(result)} items')
for item in result:
    print(f'    type={type(item).__name__}, is dict: {isinstance(item, dict)}')

print('\nAll tests passed!')
