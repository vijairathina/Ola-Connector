import zipfile
from androguard.core.dex import DEX

z = zipfile.ZipFile("analysis/base.apk")
d = DEX(z.read("classes3.dex"))

state_enums = [
    "LockHexState",
    "SteeringHexState",
    "TrunkHexState",
    "DriveHexState",
    "OTAHexState",
    "SeedKeyAckState",
    "ProximityState"
]

print("--- ENUM VALUES ---")
for c in d.get_classes():
    cname = c.get_name()
    for enum_name in state_enums:
        if cname.endswith(f"/{enum_name};"):
            print(f"\n{cname}:")
            for m in c.get_methods():
                if m.get_name() == "<clinit>":
                    code = m.get_code()
                    if code:
                        for ins in code.get_bc().get_instructions():
                            print(f"  {ins.get_name()} {ins.get_output()}")

print("\n--- STATE PARSER IMPLEMENTATION (fr/a.b) ---")
for c in d.get_classes():
    if c.get_name() == "Lfr/a;":
        for m in c.get_methods():
            print(f"Method: {m.get_name()} {m.get_descriptor()}")
            code = m.get_code()
            if code:
                for ins in code.get_bc().get_instructions()[:120]:
                    print(f"  {ins.get_name()} {ins.get_output()}")
