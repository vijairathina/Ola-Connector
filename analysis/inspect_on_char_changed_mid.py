import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

for c in d.get_classes():
    if "BleManagerImpl" in c.get_name() and "connectDevice" in c.get_name():
        for m in c.get_methods():
            if m.get_name() == "onCharacteristicChanged":
                code = m.get_code()
                if code:
                    for idx, ins in enumerate(code.get_bc().get_instructions()):
                        if 80 <= idx <= 200:
                            print(f"  [{idx:3d}] {ins.get_name()} {ins.get_output()}")
