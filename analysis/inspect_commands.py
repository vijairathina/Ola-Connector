import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

cmd_classes = []
for c in d.get_classes():
    cname = c.get_name()
    if "domain/domainModels/ble/command" in cname or "core/repo/ble/command" in cname:
        cmd_classes.append(c)

print(f"Found {len(cmd_classes)} command classes:")
for c in sorted(cmd_classes, key=lambda x: x.get_name()):
    print(f"\n--- {c.get_name()} ---")
    for f in c.get_fields():
        print(f"  FIELD: {f.get_name()} : {f.get_descriptor()}")
    for m in c.get_methods():
        print(f"  METHOD: {m.get_name()} {m.get_descriptor()}")
        code = m.get_code()
        if code:
            for ins in code.get_bc().get_instructions():
                if "const" in ins.get_name():
                    print(f"    {ins.get_name()} {ins.get_output()}")
