"""Sign only the caller's freshly built native ELF output."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

p = Path(sys.argv[1]).absolute()
if p.is_symlink() or not p.is_file() or p.read_bytes()[:4] != b"\x7fELF":
    raise RuntimeError("Expected a newly produced regular ELF")
objcopy = shutil.which("llvm-objcopy")
signer = shutil.which("binary-sign-tool")
readelf = shutil.which("llvm-readelf")
if not all((objcopy, signer, readelf)):
    raise RuntimeError("Actual OHOS signing tools are missing")
signed = p.with_name(p.name + ".signed")
if signed.exists():
    raise RuntimeError("Unexpected signing output already exists")
subprocess.run([objcopy, "--remove-section", ".codesign", str(p)], check=True, timeout=60)
subprocess.run([signer, "sign", "-inFile", str(p), "-outFile", str(signed), "-selfSign", "1"],
               check=True, timeout=60)
if signed.is_symlink() or not signed.is_file() or signed.read_bytes()[:4] != b"\x7fELF":
    raise RuntimeError("Signer did not produce a regular ELF")
sections = subprocess.run([readelf, "-SW", str(signed)], check=True, capture_output=True,
                          text=True, timeout=60).stdout
sizes = re.findall(r"(?m)^\s*\[\s*\d+\]\s+\.codesign\s+\S+\s+"
                   r"[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\b", sections)
if len(sizes) != 1 or int(sizes[0], 16) == 0:
    raise RuntimeError("Expected one nonempty codesign section")
os.replace(signed, p)
os.chmod(p, 0o755)
