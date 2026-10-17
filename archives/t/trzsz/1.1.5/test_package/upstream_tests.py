"""Run the two unmodified upstream discover entries and reject an empty suite."""
import os
from pathlib import Path
import re
import subprocess
import sys

source = Path(os.environ["TRZSZ_SOURCE_DIR"]).resolve()
for part, tests in (("trzsz-libs", "tests"), ("trzsz-svr", "svr-tests")):
    link = source / part / tests / "trzsz"
    if not link.is_symlink() or os.readlink(link) != "../trzsz":
        raise RuntimeError("Original test symlink missing: " + str(link))
    command = [sys.executable, "-m", "unittest", "discover", part]
    print("UPSTREAM_COMMAND " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=source, capture_output=True, text=True, timeout=120)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    summary = re.search(r"Ran (\d+) tests? in", result.stderr)
    if not summary or int(summary.group(1)) == 0:
        raise RuntimeError("Original upstream suite discovered zero tests")
    print("UPSTREAM_RESULT entry=%s run=%s rc=%d" % (part, summary.group(1), result.returncode), flush=True)
    if result.returncode or "skipped=" in result.stderr:
        raise SystemExit(1)
