"""Run the actual compiler and sign only its successfully linked ELF output."""
import json
from pathlib import Path
import struct
import subprocess
import sys

cfg = json.loads(Path(sys.argv[1]).read_text())
args = sys.argv[2:]
driver_args = ["--driver-mode=g++"] if cfg["language"] == "CXX" else []
rc = subprocess.run([cfg["compiler"], *driver_args, *args]).returncode
if rc:
    sys.exit(rc)
output = None
for i, value in enumerate(args):
    if value == "-o" and i + 1 < len(args):
        output = Path(args[i + 1])
    elif value.startswith("-o") and len(value) > 2:
        output = Path(value[2:])
if output is None and not any(x in args for x in ("-c", "-E", "-S", "--version", "-v")):
    output = Path("a.out")
if output is not None and output.is_file():
    with output.open("rb") as f:
        header = f.read(18)
    if len(header) == 18 and header[:4] == b"\x7fELF":
        kind = struct.unpack("<H" if header[5] == 1 else ">H", header[16:18])[0]
        if kind in (2, 3):
            subprocess.run([cfg["objcopy"], "--remove-section", ".codesign", str(output)], check=True)
            subprocess.run([cfg["signer"], "sign", "-inFile", str(output), "-outFile", str(output), "-selfSign", "1"], check=True)
