import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

for c in d.get_classes():
    cname = c.get_name()
    if "domain/domainModels/ble/encrypt" in cname or "core/repo/ble/encrypt" in cname:
        print(f"\nClass: {cname}")
        for f in c.get_fields():
            print(f"  Field: {f.get_name()} : {f.get_descriptor()}")
        for m in c.get_methods():
            print(f"  Method: {m.get_name()} {m.get_descriptor()}")
            code = m.get_code()
            if code:
                for ins in code.get_bc().get_instructions():
                    if "const-string" in ins.get_name():
                        print(f"    str: {ins.get_output()}")
