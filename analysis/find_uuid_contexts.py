import zipfile
import re

z = zipfile.ZipFile("analysis/base.apk")
dex_files = [f for f in z.namelist() if f.endswith(".dex")]

targets = [
    b"45616c3f",
    b"45616c4f",
    b"46616c3f",
    b"6e400001",
    b"6e400002",
    b"6e400003",
    b"e50e24dcca9e"
]

for dex in dex_files:
    data = z.read(dex)
    for t in targets:
        pos = 0
        while True:
            idx = data.find(t, pos)
            if idx == -1:
                break
            start = max(0, idx - 150)
            end = min(len(data), idx + 150)
            snippet = data[start:end]
            # Clean snippet for printing
            printable = "".join(chr(b) if 32 <= b <= 126 else f"\\x{b:02x}" for b in snippet)
            print(f"[{dex}] Found {t.decode()} at {idx}:\n  {printable}\n")
            pos = idx + len(t)
