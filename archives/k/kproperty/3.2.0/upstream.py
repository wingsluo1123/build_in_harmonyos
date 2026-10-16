"""Run every registered upstream entry, failing if the inventory drifts."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

source, build, package, toolchain, ecm = map(Path, sys.argv[1:6])
prefixes = sys.argv[6]
ctest = shutil.which("ctest")
if not ctest:
    sibling = Path(sys.executable).with_name("ctest")
    if sibling.is_file():
        ctest = str(sibling)
if not ctest:
    raise RuntimeError("CTest executable unavailable")
env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
env["QT_DEBUG_PLUGINS"] = "1"
resource = package / "share/kproperty3/icons/kproperty_breeze.rcc"
if not resource.is_file() or not resource.stat().st_size:
    raise RuntimeError("installed icon resource missing")
env["XDG_DATA_DIRS"] = str(package / "share") + os.pathsep + env.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
env["LD_LIBRARY_PATH"] = os.pathsep.join([str(package / "lib"), str(build / "bin"),
                                         str(build / "lib"), env.get("LD_LIBRARY_PATH", "")])
env["KPROPERTY_TEST_TOOLCHAIN"] = str(toolchain)
env["KPROPERTY_TEST_PREFIX"] = prefixes
env["KPROPERTY_TEST_ECM_DIR"] = str(ecm)
env["KPROPERTY_TEST_QT_CORE_DIR"] = str(build / "qt-cmake" / "Qt5Core")
listing = subprocess.run([ctest, "--test-dir", str(build), "--show-only=json-v1"],
                         text=True, capture_output=True, env=env, timeout=30, check=True)
tests = json.loads(listing.stdout)["tests"]
names = {item["name"] for item in tests}
if names != {"KPropertyTest", "KPropertySetTest", "HeadersTest"}:
    raise RuntimeError(f"upstream CTest inventory drift: {sorted(names)}")
process = subprocess.Popen([ctest, "--test-dir", str(build), "--verbose", "--output-on-failure",
                            "--parallel", "1", "--timeout", "60"],
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
token = Path(f"/proc/{process.pid}/stat").read_text().rsplit(") ", 1)[1].split()[19]
print(f"KPROPERTY_CTEST_PID={process.pid} START={token}", flush=True)
output, _ = process.communicate(timeout=350)
print(output, flush=True)
if process.returncode or "100% tests passed, 0 tests failed out of 3" not in output:
    raise RuntimeError("complete upstream suite did not pass")
print("KPROPERTY_UPSTREAM_PASS=3/3 registered-entries (three QtTest methods plus all-header compilation)", flush=True)
