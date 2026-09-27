import re
from datetime import datetime

log_file = "ola Log 2026-09-27 21_00_45.txt"

with open(log_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines in log: {len(lines)}")

notifications = []
writes = []
reads = []
connects = []
services = []

notif_regex = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+Notification received from ([^,]+), value: \(0x\) ([\dA-Fa-f\-]+)')
write_regex = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s+.*write.*')

for line in lines:
    m = notif_regex.search(line)
    if m:
        t_str, ch, val_str = m.groups()
        bytes_val = bytes.fromhex(val_str.replace("-", ""))
        notifications.append((t_str, ch, bytes_val, val_str))

print(f"Total notifications captured: {len(notifications)}")

# Analyze notification packet structures
print("\n--- NOTIFICATION PACKET SAMPLES ---")
for i, (t_str, ch, b_val, hex_str) in enumerate(notifications[:25]):
    # Let's inspect bytes
    hex_spaced = " ".join(f"{b:02X}" for b in b_val)
    print(f"[{t_str}] len={len(b_val):2d} | {hex_spaced}")

# Check length distribution
from collections import Counter
lengths = Counter([len(n[2]) for n in notifications])
print(f"\nPacket Length Distribution: {dict(lengths)}")

# Check first byte (header / length indicator?)
first_bytes = Counter([n[2][0] for n in notifications])
print(f"First Byte (Prefix) Distribution: { {hex(k): v for k, v in first_bytes.items()} }")

# Check second byte (sequence number?)
second_bytes = [n[2][1] for n in notifications]
print(f"Second Byte Sample (first 20): {[hex(b) for b in second_bytes[:20]]}")

# Check 3rd, 4th, 5th, 6th bytes
# In log: 6A-B9-36-31, 6A-B9-36-32, 6A-B9-36-33...
# Notice 6A B9 36 is timestamp? Let's check epoch!
# 0x6A B9 36 31 in big endian or little endian?
# Let's check:
for t_str, ch, b_val, hex_str in notifications[:10]:
    b3_6 = b_val[2:6]
    hex_b = b3_6.hex()
    val_be = int.from_bytes(b3_6, 'big')
    val_le = int.from_bytes(b3_6, 'little')
    print(f"Time={t_str} Bytes[2:6]={hex_b} BE={val_be} LE={val_le}")
