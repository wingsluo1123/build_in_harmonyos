#!/usr/bin/env python3
"""Conan test_package for mps 0.20.16.

mps is a pure-Python CLI tool (application). build() does no C linking;
test() runs test_mps.py (real imports and helper-function checks, R34)
plus a packaged bin/mps existence check. Markers are parsed from the
script's deterministic RESULT trailer line (single source, no string
counting fallbacks).
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class MpsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def _emit_upstream_no_tests(self):
        data = {
            "status": "no_tests",
            "framework": "pytest",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "mps 0.20.16 upstream ships no test suite: sdist has no tests/test directory, no test_*.py, no pytest/unittest registration (see test_package/MANIFEST.yml audit)",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data)
        self.output.info(msg)

    def test(self):
        mps_bin = os.path.join(self.dependencies["mps"].package_folder, "bin", "mps")
        if not os.path.isfile(mps_bin):
            raise ConanException("mps binary not found in package: %s" % mps_bin)
        script = os.path.join(self.recipe_folder, "test_mps.py")
        logfile = os.path.join(self.build_folder, "test_package.log")
        self.run('python3 "%s" > "%s" 2>&1' % (script, logfile), env="conanrun", ignore_errors=True)
        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_mps.py log:\n" + "\n".join(out.splitlines()[-16:]))
        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException("test_mps.py produced no RESULT line -- harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "python3 test_mps.py",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self._emit_upstream_no_tests()
        if not ok:
            raise ConanException("test_mps.py failed: %d/%d cases failed" % (failed, discovered))
        self.output.info("mps test_package passed")
