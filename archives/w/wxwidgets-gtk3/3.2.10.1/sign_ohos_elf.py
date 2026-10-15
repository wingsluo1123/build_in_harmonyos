"""Sign native OHOS package ELF files after installation at their final paths."""
import pathlib
import shutil
import subprocess
import sys

prefix = pathlib.Path(sys.argv[1]).resolve()
sign_tool = shutil.which("binary-sign-tool")
objcopy = shutil.which("llvm-objcopy")
if not sign_tool or not objcopy:
    raise SystemExit("Native OHOS packaging requires binary-sign-tool and llvm-objcopy")
count = 0
for directory in (prefix / "bin", prefix / "lib"):
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        subprocess.run([objcopy, "--remove-section", ".codesign", str(path)], check=True)
        subprocess.run([sign_tool, "sign", "-inFile", str(path), "-outFile", str(path),
                        "-selfSign", "1"], check=True)
        path.chmod(path.stat().st_mode | 0o111)
        count += 1
print("Signed native OHOS package ELF files:", count)
