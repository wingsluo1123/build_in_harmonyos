"""Full GNUmakefile runtime suite; no optional LLVM bridge or benchmarks.

Keep every upstream architecture/option filter and run all seven C2M modes
and eight bootstrap variants. Counts bind exact case IDs, not grep summaries.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

p = argparse.ArgumentParser()
for name in ("source", "build", "launcher", "cc", "ar"):
    p.add_argument("--" + name, required=True)
a = p.parse_args()
def executable(name):
    found = shutil.which(name)
    if not found:
        raise RuntimeError("Configured native executable is absent: " + name)
    path = Path(found).resolve(strict=True)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError("Native executable is not an executable ordinary file")
    return str(path)

# OHOS Python's posix_spawn path does not reliably search bare LLVM names.
# Resolve configured tools once, then pass absolute argv[0] paths to Python
# and the corresponding safely quoted paths to GNUmake.
a.cc = executable(a.cc)
a.ar = executable(a.ar)
make = executable("make")
source = Path(a.source).resolve(strict=True)
build = Path(a.build).resolve(strict=True)
env = os.environ.copy()
env["MIR_TASK_ROOT"] = str(build)
env["MIR_TASK_SOURCE_ROOT"] = str(source)
env["MIR_TARGET_CC"] = a.cc
# GNU Make 4.4 FIFO jobservers are forbidden on some OHOS filesystems.
# Serialize make only, not MIR's own parallel generation/bootstrap tests.
env["MAKEFLAGS"] = "-j1"
env["MFLAGS"] = "-j1"
env["TMPDIR"] = str(build / "tmp")
(build / "tmp").mkdir(exist_ok=True)
search = subprocess.run([a.cc, "-E", "-v", "-x", "c", "-"], input=b"",
                        capture_output=True, env=env, check=True)
paths = [Path(x.strip()) for x in search.stderr.decode().splitlines() if x.strip().startswith("/")]
headers = [x for x in paths if (x / "stdio.h").is_file() and (x / "stdlib.h").is_file()]
target = [x for x in paths if (x / "bits/setjmp.h").is_file()]
if len(headers) != 1 or len(target) != 1:
    raise RuntimeError("Native compiler sysroot is ambiguous")
env["C2M_SYSTEM_INCLUDE"] = str(headers[0])
env["C2M_TARGET_INCLUDE"] = str(target[0])
cc = " ".join(shlex.quote(x) for x in (sys.executable, a.launcher))
common = [make, "-C", str(source), "-f", "GNUmakefile", "-j1", "CC=" + cc,
          "AR=" + shlex.quote(a.ar), "GITCOMMIT=release_v1_0_0", "BUILD_DIR=" + str(build),
          "COPTFLAGS=-O3 -UNDEBUG"]
leaf = ["varr-test", "dlist-test", "bitmap-test", "htab-test", "reduce-test",
        "simplify-test", "scan-test", "io-test", "hello-test",
        *["interp-test" + str(i) for i in range(1, 17)],
        "gen-test-loop", "gen-test-sieve", "gen-test-get-thunk-addr", "gen-issue219-test",
        *["gen-test" + str(i) for i in range(1, 17)], "readme-example-test",
        "mir-bin-run-test", "mir2c-test", "c2mir-simple-test",
        "c2mir-bootstrap-test0", "c2mir-bootstrap-test1", "c2mir-bootstrap-test",
        "c2mir-bootstrap-test3", "c2mir-parallel-bootstrap-test", "c2mir-bb-bootstrap-test",
        "c2mir-bootstrap-test4", "c2mir-bootstrap-test5"]
modes = {"c2mir-interp-test": "use-c2m-interp", "c2mir-gen-test": "use-c2m-gen",
         "c2mir-bb-gen-test": "use-c2m-gen-bb", "c2mir-gen-test0": "use-c2m-gen-O0",
         "c2mir-gen-test1": "use-c2m-gen-O1", "c2mir-gen-test3": "use-c2m-gen-O3",
         "c2mir-parallel-gen-test": "use-c2m-parallel-gen"}
registered = list(leaf)
passed = []
for group, driver in modes.items():
    planenv = env.copy()
    planenv["MIR_TEST_LIST_ONLY"] = "1"
    plan = subprocess.run(["/bin/sh", str(source / "c-tests/runtests.sh"),
                           str(source / "c-tests" / driver), str(build / "c2m")],
                          cwd=source, env=planenv, capture_output=True, check=True)
    items = [x.split(" ", 1)[1] for x in plan.stdout.decode().splitlines() if x.startswith("CASE_REGISTER ")]
    if not items or len(items) != len(set(items)):
        raise RuntimeError("Empty or duplicate upstream case inventory")
    registered.extend(group + "/" + str((source / Path(x)).relative_to(source)) for x in items)
if len(registered) != len(set(registered)) or len(registered) != 7544:
    raise RuntimeError("Configured full native upstream inventory differs from 7544")
(build / "upstream-inventory.json").write_text(json.dumps({"count": len(registered), "tests": registered}, indent=2) + "\n")
print("INVENTORY_COUNT=" + str(len(registered)), flush=True)

def command(args, label, timeout=1800):
    print("COMMAND", label, repr(args), flush=True)
    result = subprocess.run(args, cwd=source, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout, check=False)
    sys.stdout.buffer.write(result.stdout)
    sys.stdout.flush()
    print(label + "_RC=" + str(result.returncode), flush=True)
    if result.returncode:
        raise RuntimeError(label + " returned " + str(result.returncode))
    return result.stdout.decode(errors="replace")

try:
    build_text = command(common + ["all"], "build_all", 900)
    if "-DC2MIR_PARALLEL" not in build_text:
        raise RuntimeError("Native thread probe did not enable parallel MIR support")
    for group in leaf:
        text = command(common + [group], group)
        if "bootstrap" in group and re.search(r"\bFAIL\b", text):
            raise RuntimeError("Bootstrap comparison failed: " + group)
        passed.append(group)
        print("LEAF_TEST_PASS", group, flush=True)
    for group in modes:
        text = command(common + [group], group)
        begins = [x.split(" ", 1)[1] for x in text.splitlines() if x.startswith("CASE_BEGIN ")]
        successes = [x.split(" ", 1)[1] for x in text.splitlines() if x.startswith("CASE_PASS ")]
        actual = [group + "/" + str((source / Path(x)).relative_to(source)) for x in successes]
        expected = [x for x in registered if x.startswith(group + "/")]
        if begins != successes or sorted(actual) != sorted(expected):
            raise RuntimeError("Full group identities do not match: " + group)
        passed.extend(actual)
    if sorted(passed) != sorted(registered):
        raise RuntimeError("Full upstream results do not match inventory")
    print("UPSTREAM_N_OF_N_PASS 7544 (7544/7544 PASS)", flush=True)
finally:
    (build / "upstream-results.json").write_text(json.dumps({"count": len(passed), "passed": passed,
        "status": "PASS" if sorted(passed) == sorted(registered) else "FAIL"}, indent=2) + "\n")
