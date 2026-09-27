import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

for c in d.get_classes():
    cname = c.get_name()
    for m in c.get_methods():
        if m.get_name() == "onCharacteristicChanged":
            print(f"\nFound onCharacteristicChanged in {cname}:")
            code = m.get_code()
            if code:
                for ins in code.get_bc().get_instructions():
                    print(f"  {ins.get_name()} {ins.get_output()}")
