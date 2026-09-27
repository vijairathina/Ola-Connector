import re
from androguard.core.apk import APK
from androguard.core.dex import DEX

apk = APK("analysis/base.apk")
dex_files = [f for f in apk.get_files() if f.endswith('.dex')]

relevant_classes = []
ble_methods = []

for dex_name in dex_files:
    d = DEX(apk.get_file(dex_name))
    for c in d.get_classes():
        cname = c.get_name()
        # Look for BLE management classes
        if any(term in cname.lower() for term in ["ble", "bluetooth", "gatt", "scooterble", "vehicleble", "blemanager", "commandmanager"]):
            relevant_classes.append(cname)
            for m in c.get_methods():
                mname = m.get_name()
                ble_methods.append(f"{cname} -> {mname} {m.get_descriptor()}")

print(f"Total BLE-related classes found: {len(relevant_classes)}")
for c in sorted(set(relevant_classes))[:80]:
    print(c)

print(f"\nTotal BLE-related methods found: {len(ble_methods)}")
for m in sorted(set(ble_methods))[:50]:
    print(m)
