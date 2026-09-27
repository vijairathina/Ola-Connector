import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

resp_classes = []
for c in d.get_classes():
    cname = c.get_name()
    if "domain/domainModels/ble/response" in cname or "domain/domainModels/ble/state" in cname:
        resp_classes.append(c)

print(f"Found {len(resp_classes)} response and state classes:")
for c in sorted(resp_classes, key=lambda x: x.get_name()):
    print(f"\n--- {c.get_name()} ---")
    for f in c.get_fields():
        print(f"  FIELD: {f.get_name()} : {f.get_descriptor()}")
    for m in c.get_methods():
        print(f"  METHOD: {m.get_name()} {m.get_descriptor()}")
