import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

classes_to_inspect = [
    "Ldomain/domainModels/ble/response/SocResponse;",
    "Ldomain/domainModels/ble/response/SportModeRangeResponse;",
    "Ldomain/domainModels/ble/response/TimeToChargeResponse;",
    "Ldomain/domainModels/ble/response/VehicleStatusInfoResponse;",
    "Ldomain/domainModels/ble/response/ScooterSteeringStateResponse;",
    "Ldomain/domainModels/ble/response/SeedKeyResponse;",
    "Ldomain/domainModels/ble/response/SeedKeyAckResponse;"
]

for c in d.get_classes():
    if c.get_name() in classes_to_inspect:
        print(f"\n==================== {c.get_name()} ====================")
        for m in c.get_methods():
            if m.get_name() in ["parse", "<init>", "cachedIndex"]:
                print(f"--- Method: {m.get_name()} {m.get_descriptor()} ---")
                code = m.get_code()
                if code:
                    for ins in code.get_bc().get_instructions():
                        print(f"  {ins.get_name()} {ins.get_output()}")
