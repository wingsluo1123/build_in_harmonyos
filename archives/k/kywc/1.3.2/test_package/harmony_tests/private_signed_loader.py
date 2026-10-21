"""One actual OHOS signed-loader scenario for the kywc consumer test."""
import hashlib
import os
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

if os.uname().sysname != "HarmonyOS" or os.uname().machine != "aarch64":
    raise RuntimeError("Actual HarmonyOS PC AArch64 required")
source = Path(sys.argv[1]).resolve(strict=True)
data = source.read_bytes()
if (len(data) < 64 or data[:6] != b"\x7fELF\x02\x01"
        or struct.unpack_from("<H", data, 18)[0] != 183
        or struct.unpack_from("<H", data, 16)[0] not in (2, 3)):
    raise RuntimeError("Real executable ELF64/little-endian/AArch64 required")
offset = struct.unpack_from("<Q", data, 40)[0]
size, count, strings_index = struct.unpack_from("<HHH", data, 58)
if size < 64 or count == 0 or strings_index >= count or offset + size * count > len(data):
    raise RuntimeError("Malformed ELF section table")
strings_offset, strings_size = struct.unpack_from("<QQ", data, offset + strings_index * size + 24)
if strings_offset + strings_size > len(data):
    raise RuntimeError("Malformed ELF string table")
strings = data[strings_offset:strings_offset + strings_size]
signed = False
for index in range(count):
    entry = offset + index * size
    name_offset = struct.unpack_from("<I", data, entry)[0]
    if name_offset >= len(strings):
        raise RuntimeError("Malformed ELF section name")
    if strings[name_offset:].split(b"\0", 1)[0] == b".codesign":
        section_offset, section_size = struct.unpack_from("<QQ", data, entry + 24)
        signed = section_size > 0 and section_offset + section_size <= len(data)
if not signed:
    raise RuntimeError("Actual nonempty OHOS codesign section required")
parent = None
for value in (os.environ.get("TMPDIR"), "/data/storage/el2/base/cache"):
    if not value:
        continue
    candidate = Path(value)
    if (candidate.is_absolute() and candidate.is_dir() and candidate.resolve() == candidate
            and candidate.stat().st_uid == os.getuid() and os.access(candidate, os.W_OK | os.X_OK)):
        parent = candidate
        break
if parent is None:
    raise RuntimeError("Actual owned writable POSIX parent required")
with tempfile.TemporaryDirectory(prefix="kywc-ohos-signed-", dir=str(parent)) as directory:
    root = Path(directory)
    if root.is_symlink() or root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise RuntimeError("Unsafe private inode root")
    relocated = root / "actual-kywc-consumer"
    with relocated.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
        identity = os.fstat(output.fileno())
    relocated.chmod(0o700)
    if identity.st_uid != os.getuid() or relocated.is_symlink() or relocated.read_bytes() != data:
        raise RuntimeError("Private inode/byte identity mismatch")
    result = subprocess.run([str(relocated)], capture_output=True, timeout=90)
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    if (result.returncode != 0 or b"TEST SUMMARY:" not in result.stdout
            or b", 0 failed" not in result.stdout):
        raise RuntimeError("Real installed libkywc consumer scenario failed")
    digest = hashlib.sha256(data).hexdigest()
if root.exists():
    raise RuntimeError("Private scenario directory not cleaned")
print("HARMONY_TEST_COUNT=1")
print("HARMONY_TEST_PASS=1/1")
print("ACTUAL_SIGNED_ELF_SHA256=" + digest)
