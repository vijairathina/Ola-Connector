import re
import json
from androguard.misc import AnalyzeAPK

print("Starting APK Analysis...")
a, d, dx = AnalyzeAPK("analysis/base.apk")

print(f"Package: {a.get_package()}")
print(f"App name: {a.get_app_name()}")
print(f"Version Name: {a.get_androidversion_name()}")
print(f"Version Code: {a.get_androidversion_code()}")
print(f"Min SDK: {a.get_min_sdk_version()}")
print(f"Target SDK: {a.get_target_sdk_version()}")

permissions = a.get_permissions()
print(f"\nPermissions count: {len(permissions)}")
bt_perms = [p for p in permissions if "bluetooth" in p.lower() or "location" in p.lower() or "nearby" in p.lower()]
print("Bluetooth & Location Permissions:")
for p in bt_perms:
    print(f"  - {p}")

print("\nSearching classes for bluetooth/ble/scooter...")
bt_classes = []
for cls in dx.get_classes():
    cname = cls.name
    if "com/olaelectric" in cname and any(k in cname.lower() for k in ["ble", "bluetooth", "scooter", "vehicle", "gatt", "telemetry", "lock"]):
        bt_classes.append(cname)

print(f"Found {len(bt_classes)} relevant classes in com.olaelectric:")
for c in sorted(bt_classes)[:50]:
    print(f"  {c}")

# Search for UUID patterns in strings
print("\nSearching for UUID strings...")
uuid_regex = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
found_uuids = set()
for s in dx.get_strings():
    val = s.get_value()
    for match in uuid_regex.findall(val):
        found_uuids.add(match)

print(f"Found {len(found_uuids)} UUIDs:")
for u in sorted(found_uuids):
    print(f"  {u}")

# Search for 6e40 or similar Nordic / custom BLE patterns
print("\nSearching for 6e40 or 4561 patterns...")
for s in dx.get_strings():
    val = s.get_value()
    if any(k in val.lower() for k in ["6e40", "45616c", "olas1", "ola_scooter", "scooter"]):
        if len(val) < 100:
            print(f"  String: {val}")

print("\nDone initial scan.")
