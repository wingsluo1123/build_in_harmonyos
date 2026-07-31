import os
import sys
from pathlib import Path


package_folder = Path(sys.argv[1])
script = package_folder / "bin" / "safekeep"
share = package_folder / "share" / "safekeep"
upstream_test = share / "safekeep-test"
config = share / "safekeep.conf"
doc = share / "doc" / "safekeep.txt"
sample = share / "samples" / "sample.backup"

for path in (script, upstream_test, config, doc, sample):
    if not path.is_file():
        raise SystemExit(f"missing packaged file: {path}")

if not os.access(script, os.X_OK):
    raise SystemExit(f"safekeep is not executable: {script}")

text = script.read_text(encoding="utf-8")
expected_markers = [
    "#!/usr/bin/env python3",
    'VERSION = "1.5.1"',
    "def usage(exitcode=None):",
    "rdiff-backup",
    "if __name__ == '__main__':",
]
for marker in expected_markers:
    if marker not in text:
        raise SystemExit(f"missing safekeep script marker: {marker}")

test_text = upstream_test.read_text(encoding="utf-8")
for marker in [
    "def localTest(tmproot):",
    "def remoteTest(tmproot, client, server):",
    "rdiff-backup -r now",
    "safekeep --server",
    "SAFEKEEP_TEST_CLIENT",
    "SAFEKEEP_TEST_SERVER",
    "--reps=N",
]:
    if marker not in test_text:
        raise SystemExit(f"missing upstream safekeep-test marker: {marker}")

print("safekeep command, support files, and upstream safekeep-test are packaged")
