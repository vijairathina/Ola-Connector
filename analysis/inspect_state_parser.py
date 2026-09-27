import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

# Let's find fr/a and VehicleState and any classes in core/repo/ble/state/
state_classes = []
for c in d.get_classes():
    cname = c.get_name()
    if any(k in cname for k in ["VehicleState", "core/repo/ble/state", "domain/domainModels/ble", "Lfr/a", "Lfr/"]):
        state_classes.append(c)

print(f"Found {len(state_classes)} state classes:")
for c in state_classes:
    cname = c.get_name()
    print(f"\n--- {cname} ---")
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
