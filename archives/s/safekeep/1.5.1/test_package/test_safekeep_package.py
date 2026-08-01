import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


package_folder = Path(sys.argv[1])
run_upstream_local = "--run-upstream-local" in sys.argv[2:]
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
    "-r now",
    "safekeep --server",
    "SAFEKEEP_TEST_OHOS_LOCAL",
    "SAFEKEEP_TEST_CLIENT",
    "SAFEKEEP_TEST_SERVER",
    "--reps=N",
]:
    if marker not in test_text:
        raise SystemExit(f"missing upstream safekeep-test marker: {marker}")

print("safekeep command, support files, and upstream safekeep-test are packaged")

if run_upstream_local:
    for exe in ("safekeep", "rdiff-backup", "find", "xargs", "md5sum", "diff"):
        if not shutil.which(exe):
            raise SystemExit(f"missing test executable: {exe}")

    tmp_base = Path(os.environ.get("TMPDIR") or Path.cwd() / "tmp")
    tmp_base.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="safekeep-upstream-", dir=str(tmp_base)))
    env = os.environ.copy()
    env["SAFEKEEP_TEST_OHOS_LOCAL"] = "1"
    env["TMPDIR"] = str(workdir / "tmp")
    env["TEMP"] = env["TMPDIR"]
    env["TMP"] = env["TMPDIR"]
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, str(upstream_test), "--local", "--reps=1"],
        cwd=str(workdir),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout, end="")
    if result.returncode:
        raise SystemExit(f"safekeep upstream local test failed with exit code {result.returncode}")

    print("safekeep upstream local test: 1/1 passed")
