#!/usr/bin/env python3
"""Conan test_package for perdition 2.2 (application).

Consumer checks (2):
  1. `perdition --help` prints the proxy usage banner (real binary run).
  2. makegdbm gdbm roundtrip: stdin flat map -> .gdbm file -> `makegdbm -u`
     prints the entry back (real DB write+read through libgdbm).

Counts come from the single deterministic source test.sh output lines
`^ok [12]: ` (no fallback counting, no arithmetic patching).
Upstream evidence (no_tests audit) is re-emitted from
res/upstream_test_summary.json shipped by the main recipe (HMBS gate only
scans test_package stdout; build() is skipped on cache hits).
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException

CONSUMER_CHECK_COUNT = 2


class PerditionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Same shell rule as the main recipe (CI #91093): prefer the hnp
        # bash by filesystem existence (working shell on CI workers), else
        # /bin/sh (working shell on HMBS true machines). The outer SHELL
        # env is misleading on CI (SHELL=/bin/sh) and must not override.
        hnp = "/data/service/hnp/bin/bash"
        try:
            if os.path.isfile(hnp) and os.access(hnp, os.X_OK):
                bash = hnp
            else:
                bash = "/bin/sh"
        except Exception:
            bash = "/bin/sh"
        log_path = os.path.join(self.build_folder, "hmbs_test_package.log")
        cmd = "%s test.sh" % bash
        rc = 0
        try:
            self.run('%s > "%s" 2>&1' % (cmd, log_path), env="conanrun")
        except Exception:
            rc = 1
        output = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                output = f.read()
        except OSError:
            output = ""
        tail = "\n".join(output.splitlines()[-15:])
        if tail:
            self.output.info("test_perdition output tail:\n%s" % tail)
        ok_count = len(re.findall(r"^ok \d+: ", output, re.MULTILINE))
        all_passed = "ALL CHECKS PASSED" in output
        tp_passed = (rc == 0 and all_passed and ok_count == CONSUMER_CHECK_COUNT)
        tp_marker = {
            "executed": True,
            "passed": tp_passed,
            "command": "sh test.sh",
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False))

        try:
            pkg = self.dependencies[self.tested_reference_str]
            summary_path = os.path.join(str(pkg.package_folder), "res",
                                        "upstream_test_summary.json")
        except Exception:
            summary_path = ""
        upstream = None
        if summary_path and os.path.isfile(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    upstream = json.load(f)
            except (OSError, ValueError) as exc:
                self.output.warning("perdition: could not read upstream summary: %s" % exc)
                upstream = None
        if upstream is not None:
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        else:
            self.output.warning("perdition: upstream summary missing; emitting failed marker")
            ut = {
                "status": "failed",
                "framework": "autotools-make-check",
                "command": "make check (run in main recipe build())",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "upstream_test_summary.json missing in package",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut, ensure_ascii=False))
            raise ConanException("perdition: upstream test summary missing; cannot pass gate")

        if not tp_passed:
            raise ConanException(
                "perdition consumer test failed: rc=%s ok=%s/%s all_passed=%s"
                % (rc, ok_count, CONSUMER_CHECK_COUNT, all_passed))
        self.output.info("perdition consumer test_package passed")
