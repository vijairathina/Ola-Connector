import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")

for dex_name in z.namelist():
    if not dex_name.endswith('.dex'):
        continue
    d = DEX(z.read(dex_name))
    for c in d.get_classes():
        cname = c.get_name()
        for m in c.get_methods():
            code = m.get_code()
            if not code:
                continue
            for ins in code.get_bc().get_instructions():
                op = ins.get_output()
                if "SocResponse" in op:
                    print(f"[{dex_name}] {cname} -> {m.get_name()}: {ins.get_name()} {op}")
