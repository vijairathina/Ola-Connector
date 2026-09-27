import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
dex_data = z.read("classes3.dex")
d = DEX(dex_data)

target_str = "45616c3f-b5a3-f393-e0a9-e50e24dcca9e"
str_idx = None
for idx, s in enumerate(d.get_strings()):
    if s == target_str:
        str_idx = idx
        print(f"Found string index for {target_str}: {str_idx}")
        break

for c in d.get_classes():
    cname = c.get_name()
    for m in c.get_methods():
        code = m.get_code()
        if not code:
            continue
        bc = code.get_bc()
        for ins in bc.get_instructions():
            op = ins.get_output()
            if target_str in op or (str_idx is not None and f"string@{str_idx}" in op):
                print(f"MATCH: {cname} -> {m.get_name()}: {ins.get_name()} {op}")
                # Print all strings in this method
                for ins2 in bc.get_instructions():
                    if "const-string" in ins2.get_name():
                        print(f"   ins: {ins2.get_output()}")
