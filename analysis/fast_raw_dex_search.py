import zipfile
import re

print("Searching strings in all DEX files...")
z = zipfile.ZipFile("analysis/base.apk")
dex_files = [f for f in z.namelist() if f.endswith(".dex")]

uuid_pattern = re.compile(rb'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
uuids = set()

all_raw_strings = []

for dex in dex_files:
    data = z.read(dex)
    for u in uuid_pattern.findall(data):
        uuids.add(u.decode('ascii'))
    
    # Also search for substrings like 6e40, 45616c, olas1, etc.
    for m in re.finditer(rb'[a-zA-Z0-9_\-\.]{4,60}', data):
        s = m.group(0)
        if any(k in s.lower() for k in [b'6e40', b'45616c', b'olas1', b'companion', b'scooter', b'ble_']):
            try:
                all_raw_strings.append(s.decode('utf-8', 'ignore'))
            except:
                pass

print(f"Discovered UUIDs: {len(uuids)}")
for u in sorted(uuids):
    print(f"  UUID: {u}")

print(f"\nDiscovered relevant identifiers ({len(all_raw_strings)}):")
for s in sorted(set(all_raw_strings))[:60]:
    print(f"  {s}")
