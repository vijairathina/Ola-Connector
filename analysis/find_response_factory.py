import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

target_classes = [
    "Ldomain/domainModels/ble/response/SocResponse;",
    "Ldomain/domainModels/ble/response/SportModeRangeResponse;",
    "Ldomain/domainModels/ble/response/ScooterSteeringStateResponse;",
    "Ldomain/domainModels/ble/response/TimeToChargeResponse;"
]

for c in d.get_classes():
    cname = c.get_name()
    for m in c.get_methods():
        code = m.get_code()
        if not code:
            continue
        for ins in code.get_bc().get_instructions():
            op = ins.get_output()
            if any(tc in op for tc in target_classes) and "new-instance" in ins.get_name():
                print(f"Instantiated in: {cname} -> {m.get_name()}")
                for ins2 in code.get_bc().get_instructions():
                    print(f"    {ins2.get_name()} {ins2.get_output()}")
                break
