import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")

for dex_name in z.namelist():
    if not dex_name.endswith('.dex'):
        continue
    d = DEX(z.read(dex_name))
    for c in d.get_classes():
        if c.get_name() == "Lfq/b;" or c.get_name() == "Lvv/c;":
            print(f"\nFound {c.get_name()} in {dex_name}:")
            for m in c.get_methods():
                print(f"  Method: {m.get_name()} {m.get_descriptor()}")
                code = m.get_code()
                if code:
                    for ins in code.get_bc().get_instructions()[:30]:
                        print(f"    {ins.get_name()} {ins.get_output()}")
