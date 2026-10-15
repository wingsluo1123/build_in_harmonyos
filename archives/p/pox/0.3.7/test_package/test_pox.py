#!/usr/bin/env python3
"""Exercise the packaged pox from a consumer's point of view.

Runs under the Conan run environment, so ``import pox`` must resolve into the
package payload (asserted).  The checks drive the documented public API:

1. the module imports and reports its version (0.3.7);
2. ``expandvars``/``env`` really read the process environment;
3. ``mkdir``/``walk``/``find``/``which`` perform real filesystem work on a
   temp tree (create, then locate what was created);
4. ``pattern``/``minpath`` pure-logic helpers behave as documented.
"""
import os
import sys

import pox

from pathlib import Path

EXPECTED_ROOT = Path(os.environ["POX_PACKAGE_ROOT"]).resolve()
MODULE_PATH = Path(pox.__file__).resolve()
assert EXPECTED_ROOT in MODULE_PATH.parents, (EXPECTED_ROOT, MODULE_PATH)
assert pox.__version__ == "0.3.7", pox.__version__

# 2) environment helpers read the real process environment.
os.environ["POX_CONSUMER_PROBE"] = "harmony"
assert pox.expandvars("$POX_CONSUMER_PROBE") == "harmony", \
    pox.expandvars("$POX_CONSUMER_PROBE")
# pox.env(variable, all=False) returns the value ({} when unset).
assert pox.env("POX_CONSUMER_PROBE", all=False) == "harmony", \
    pox.env("POX_CONSUMER_PROBE", all=False)

# 3) real filesystem work on a temp tree.
import shutil
import tempfile

tmp = tempfile.mkdtemp(prefix="pox-test-")
try:
    sub = os.path.join(tmp, "aa", "bb")
    made = pox.mkdir(os.path.join(tmp, "aa"))
    assert os.path.isdir(os.path.join(tmp, "aa")), made
    os.makedirs(sub, exist_ok=True)
    marker = os.path.join(sub, "needle.txt")
    with open(marker, "w") as fh:
        fh.write("x")

    dirs = pox.walk(tmp, "*", recurse=True, folders=True, files=False)
    assert os.path.join(tmp, "aa") in dirs, dirs
    found = pox.find("needle.txt", root=tmp, recurse=True)
    assert marker in found, found
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 4) pure-logic helpers.
assert pox.pattern(["PYTHON*", "DEVELOPER"]) == "PYTHON*;DEVELOPER"
assert pox.pattern([]) == ""
path = os.pathsep.join(["/a/bin", "/b/bin"])
assert pox.minpath(path).count(os.pathsep) <= path.count(os.pathsep)

print("POX-CONSUMER-OK")
