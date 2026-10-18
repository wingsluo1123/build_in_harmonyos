"""Sign each native linked ELF, without changing compiler probe output."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(os.environ["MIR_TASK_ROOT"]).resolve(strict=True)
source = Path(os.environ["MIR_TASK_SOURCE_ROOT"]).resolve(strict=True)
args = sys.argv[1:]
compiler = shutil.which(os.environ["MIR_TARGET_CC"])
if not compiler:
    raise RuntimeError("Configured target C compiler is absent")
linked = not any(flag in args for flag in ("-c", "-E", "-S")) and any(
    Path(arg).suffix in (".c", ".cc", ".cpp", ".o", ".s", ".a") for arg in args)
p = None
if linked:
    destination = args[args.index("-o") + 1] if "-o" in args else "a.out"
    if destination != "-":
        p = Path(destination).absolute()
        # check-threads.sh links __tmp.out in the owned source directory;
        # ordinary products are out-of-source. Neither permits foreign output.
        for parent in (p, *p.parents):
            if parent.is_symlink():
                raise RuntimeError("Redirected linked output")
        p = p.resolve()
        if not any(p.is_relative_to(allowed) for allowed in (root, source)):
            raise RuntimeError("Linked output is outside the task source/build roots")
result = subprocess.run([compiler, *args], check=False)
if result.returncode:
    raise SystemExit(result.returncode)
if p is None:
    raise SystemExit(0)
header = p.read_bytes()[:20]
if header[:4] != b"\x7fELF" or int.from_bytes(header[16:18], "little") not in (2, 3):
    raise SystemExit(0)
signed = p.with_name(p.name + ".signed")
if signed.exists():
    raise RuntimeError("Signing output already exists")
signer = shutil.which("binary-sign-tool")
inspector = shutil.which("llvm-readelf")
if not signer or not inspector:
    raise RuntimeError("OHOS ELF signer or inspector is absent")
result = subprocess.run([signer, "sign", "-inFile", str(p), "-outFile", str(signed),
                         "-selfSign", "1"], capture_output=True, check=False)
if result.returncode:
    sys.stderr.buffer.write(result.stdout + result.stderr)
    raise SystemExit(result.returncode)
result = subprocess.run([inspector, "-S", str(signed)], capture_output=True, check=True)
if b".codesign" not in result.stdout:
    raise RuntimeError("OHOS signing section is absent")
os.chmod(signed, p.stat().st_mode)
os.replace(signed, p)
