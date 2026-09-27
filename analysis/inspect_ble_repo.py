import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

ble_classes = []
for c in d.get_classes():
    cname = c.get_name()
    if "core/repo/ble" in cname:
        ble_classes.append(c)

print(f"Found {len(ble_classes)} classes in core/repo/ble:")
for c in sorted(ble_classes, key=lambda x: x.get_name()):
    print(f"  {c.get_name()}")

print("\n--- Inspecting BleManagerImpl and key classes ---")
for c in ble_classes:
    cname = c.get_name()
    if any(k in cname for k in ["BleManagerImpl", "BleProtocol", "Command", "Packet", "Gatt", "Signal", "Telemetry", "Lock"]):
        print(f"\n==================== {cname} ====================")
        for f in c.get_fields():
            print(f"  FIELD: {f.get_name()} : {f.get_descriptor()}")
        for m in c.get_methods():
            print(f"  METHOD: {m.get_name()} {m.get_descriptor()}")
            code = m.get_code()
            if code:
                bc = code.get_bc()
                for ins in bc.get_instructions():
                    if "const-string" in ins.get_name():
                        print(f"    str: {ins.get_output()}")
