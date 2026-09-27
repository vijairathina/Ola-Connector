import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

for c in d.get_classes():
    cname = c.get_name()
    if cname == "Ldomain/domainModels/ble/response/IResponse;":
        print(f"\nFound {cname}:")
        for f in c.get_fields():
            print(f"  FIELD: {f.get_name()} : {f.get_descriptor()}")
        for m in c.get_methods():
            print(f"  METHOD: {m.get_name()} {m.get_descriptor()}")
            code = m.get_code()
            if code:
                for ins in code.get_bc().get_instructions():
                    if "const-string" in ins.get_name():
                        print(f"    str: {ins.get_output()}")

    # Find classes extending IResponse
    if c.get_superclassname() == "Ldomain/domainModels/ble/response/IResponse;":
        print(f"\nSubclass of IResponse: {cname}")
        for f in c.get_fields():
            print(f"  FIELD: {f.get_name()} : {f.get_descriptor()}")
        for m in c.get_methods():
            print(f"  METHOD: {m.get_name()} {m.get_descriptor()}")
            code = m.get_code()
            if code:
                for ins in code.get_bc().get_instructions():
                    if "const-string" in ins.get_name():
                        print(f"    str: {ins.get_output()}")
