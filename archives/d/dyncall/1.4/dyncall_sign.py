"""Sign only task/package-owned ELF copies; use real executable providers."""
import os
import shutil
import subprocess
from pathlib import Path


def tool(name):
    entry = shutil.which(name)
    if not entry:
        raise RuntimeError("Required native OHOS tool unavailable: " + name)
    return str(Path(entry).resolve(strict=True))


def sign_elf(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.read_bytes()[:4] != b"\x7fELF":
        raise RuntimeError("Missing or redirected ELF: " + str(path))
    input_copy = path.with_name(path.name + ".dyncall-sign-input")
    signed = path.with_name(path.name + ".dyncall-signed")
    if input_copy.exists() or signed.exists():
        raise RuntimeError("Stale signing sibling")
    try:
        shutil.copy2(path, input_copy)
        subprocess.run([tool("binary-sign-tool"), "sign", "-inFile", str(input_copy),
                        "-outFile", str(signed), "-selfSign", "1"],
                       check=True, capture_output=True, timeout=40)
        result = subprocess.run([tool("llvm-readelf"), "--elf-output-style=GNU", "-S", str(signed)],
                                check=True, capture_output=True, timeout=20)
        if result.stdout.count(b".codesign") != 1:
            raise RuntimeError("Expected exactly one ELF .codesign section")
        os.chmod(signed, path.stat().st_mode)
        os.replace(signed, path)
    finally:
        for temporary in (input_copy, signed):
            if temporary.exists(): temporary.unlink()
