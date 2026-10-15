#!/usr/bin/env python3
"""Conan test_package — myMPD 25.3.0 (consumer end-to-end tests).

Runs the consumer E2E executor (tests/run_e2e.sh) against the packaged
mympd binary.  The executor drives real consumer workflows:

  1. version output: exit 0 and the exact version string, including the
     embedded libmpdclient build proof (Libmpdclient 2.26.0 (embedded))
  2. help output: exit 0 with the usage text
  3. default configuration dump (-d)
  4. bootstrap (-c): creates the work/cache directory tree, writes the
     per-item configuration files and generates the self-signed TLS
     certificates (ca.pem / server.pem) below a scratch workdir
  5. negative control: an unknown option exits non-zero without crashing

Each case is judged independently by the executor (one TEST PASS/FAIL line
per case), followed by a TEST SUMMARY line; any failure exits non-zero and
fails test_package.  The HMBS_TEST_PACKAGE_RESULT marker carries the real
case counts.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class MympdTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["mympd"]
        mympd = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0],
                             "mympd")
        tests_dir = os.path.join(self.source_folder, "tests")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so drive the executor with the environment bash (house pattern).
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        log_file = os.path.join(self.build_folder, "run_e2e.log")
        command = (f'{bash} "{os.path.join(tests_dir, "run_e2e.sh")}" '
                   f'"{mympd}"')
        rc = self.run(f'{command} > "{log_file}" 2>&1',
                      env="conanrun", ignore_errors=True)
        passed = 0
        failed = 0
        if os.path.isfile(log_file):
            with open(log_file, encoding="utf-8", errors="replace") as log:
                for line in log:
                    self.output.info(line.rstrip())
                    if line.startswith("TEST PASS:"):
                        passed += 1
                    elif line.startswith("TEST FAIL:"):
                        failed += 1
        test_pkg = {
            "executed": True,
            "passed": rc == 0 and failed == 0 and passed > 0,
            "command": "bash tests/run_e2e.sh <mympd>",
            "discovered": passed + failed,
            "passedCount": passed,
            "failedCount": failed,
            "rc": rc,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(test_pkg, ensure_ascii=False))
        if not test_pkg["passed"]:
            raise ConanException(f"consumer e2e tests failed: rc={rc}, "
                                 f"passed={passed}, failed={failed}")
