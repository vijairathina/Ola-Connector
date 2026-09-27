import re

with open("ola Log 2026-09-27 21_00_45.txt", "r", encoding="utf-8") as f:
    text = f.read()

notif_regex = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+Notification received from ([^,]+), value: \(0x\) ([\dA-Fa-f\-]+)')
packets = []
for m in notif_regex.finditer(text):
    t_str, ch, val_str = m.groups()
    b = bytes.fromhex(val_str.replace("-", ""))
    packets.append((t_str, b))

print(f"Total: {len(packets)} packets")

# Packet format:
# byte 0: length of payload (0x0C, 0x0D, 0x0E, 0x10, 0x13)
# byte 1: sequence counter (modulo 256)
# bytes 2..5: Unix epoch timestamp in seconds (big endian)
# bytes 6+: payload data
records = []
for t_str, b in packets:
    plen = b[0]
    seq = b[1]
    ts = int.from_bytes(b[2:6], 'big')
    payload = b[6:plen+1] if plen < len(b) else b[6:]
    records.append((t_str, seq, ts, plen, payload))

# Let's inspect the payload types: what are the first bytes of payload?
payload_types = {}
for t_str, seq, ts, plen, payload in records:
    ptype = payload[:3].hex()
    if ptype not in payload_types:
        payload_types[ptype] = []
    payload_types[ptype].append((t_str, seq, ts, payload.hex()))

print(f"Unique payload header types (first 3 bytes of payload): {len(payload_types)}")
for ptype, items in payload_types.items():
    print(f"Type {ptype} (count={len(items)}): e.g. {items[0][3]}")
