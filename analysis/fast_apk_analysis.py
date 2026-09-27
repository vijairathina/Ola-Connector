import re
import os
from androguard.core.apk import APK
from androguard.core.dex import DEX

print("Loading APK...")
apk = APK("analysis/base.apk")
print(f"Package: {apk.get_package()}")
print(f"App name: {apk.get_app_name()}")
print(f"Version Name: {apk.get_androidversion_name()}")
print(f"Version Code: {apk.get_androidversion_code()}")
print(f"Min SDK: {apk.get_min_sdk_version()}")
print(f"Target SDK: {apk.get_target_sdk_version()}")

print("\n--- PERMISSIONS ---")
for p in sorted(apk.get_permissions()):
    if any(k in p.lower() for k in ["bluetooth", "location", "nearby", "connect", "scan", "admin"]):
        print(f"  {p}")

print("\n--- SERVICES IN MANIFEST ---")
for s in apk.get_services():
    if any(k in s.lower() for k in ["ble", "bluetooth", "scooter", "vehicle"]):
        print(f"  {s}")

print("\n--- EXTRACTING DEX STRINGS & CLASSES ---")
dex_files = [f for f in apk.get_files() if f.endswith('.dex')]
print(f"DEX files: {dex_files}")

all_strings = set()
all_classes = set()

for dex_name in dex_files:
    dex_data = apk.get_file(dex_name)
    d = DEX(dex_data)
    for c in d.get_classes():
        all_classes.add(c.get_name())
    for s in d.get_strings():
        all_strings.add(s)

print(f"Total classes found: {len(all_classes)}")
print(f"Total strings found: {len(all_strings)}")

# Search for relevant classes
print("\n--- RELEVANT CLASSES (BLE / SCOOTER / BLUETOOTH) ---")
ble_classes = [c for c in all_classes if "ola" in c.lower() and any(k in c.lower() for k in ["ble", "bluetooth", "gatt", "scooter", "vehicle", "lock", "battery", "command"])]
for c in sorted(ble_classes)[:80]:
    print(f"  {c}")

# Search for UUIDs
print("\n--- UUID STRINGS FOUND ---")
uuid_regex = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
uuids = set()
for s in all_strings:
    for u in uuid_regex.findall(s):
        uuids.add(u)

for u in sorted(uuids):
    print(f"  {u}")

# Search for specific Nordic / Ola identifiers
print("\n--- NORDIC / OLA IDENTIFIERS ---")
for s in sorted(all_strings):
    if any(k in s.lower() for k in ["6e4000", "45616c", "olas1", "companion", "bleak", "ble_"]):
        if len(s) < 120:
            print(f"  {s}")

# Write all filtered strings to analysis/dex_strings.txt for quick searching
with open("analysis/dex_strings.txt", "w", encoding="utf-8") as f:
    for s in sorted(all_strings):
        if any(k in s.lower() for k in ["bluetooth", "ble", "gatt", "scooter", "battery", "range", "charging", "lock", "unlock", "telemetry", "odometer", "speed"]):
            f.write(s + "\n")

print("\nWrote filtered strings to analysis/dex_strings.txt")
