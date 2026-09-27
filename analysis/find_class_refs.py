from androguard.core.apk import APK
from androguard.core.dex import DEX

apk = APK("analysis/base.apk")
for dex_name in apk.get_files():
    if not dex_name.endswith('.dex'):
        continue
    dex_data = apk.get_file(dex_name)
    d = DEX(dex_data)
    for c in d.get_classes():
        # Check all methods in class for instructions referencing 45616c3f or chargingLockedTrunkClosed
        c_str = ""
        found = False
        for m in c.get_methods():
            code = m.get_code()
            if code:
                # search in byte instructions or string references
                pass
        # Let's inspect class source or fields
        for s in ["45616c3f", "45616c4f", "46616c3f", "chargingLockedTrunkClosed"]:
            # Check if class name or field or method has it
            pass

print("Searching methods referencing UUIDs...")
for dex_name in apk.get_files():
    if not dex_name.endswith('.dex'):
        continue
    d = DEX(apk.get_file(dex_name))
    for c in d.get_classes():
        for m in c.get_methods():
            code = m.get_code()
            if not code:
                continue
            bc = code.get_bc()
            for ins in bc.get_instructions():
                op_val = ins.get_output()
                if any(k in op_val for k in ["45616c3f", "45616c4f", "46616c3f", "chargingLockedTrunkClosed"]):
                    print(f"[{dex_name}] {c.get_name()} -> {m.get_name()}: {ins.get_name()} {op_val}")
