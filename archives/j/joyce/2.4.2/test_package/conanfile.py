#!/usr/bin/env python3
"""Conan test_package for joyce 2.4.2.

joyce is an application (Amstrad PCW emulator plus bundled LibDsk disk-image
tools).  This consumer test genuinely executes an installed binary - the
dskconv disk-format utility (a real CLI tool built and installed by the
bundled LibDsk tools subdirectory).

The test logic lives in the sibling test source file ``test.sh`` (required by
the CI L0c gate).  ``test()`` invokes that script through Conan's
``self.run()`` (required by the CI L0d anti-stub gate); the script's
deterministic ``RESULT: <passed> passed, <failed> failed`` summary line is the
single source of truth for the HMBS_TEST_PACKAGE_RESULT counts.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = os.path.join(
            self.dependencies["joyce"].package_folder,
            self.dependencies["joyce"].cpp_info.bindirs[0],
        )
        dskconv = os.path.join(bindir, "dskconv")
        if not os.path.isfile(dskconv):
            raise ConanException("dskconv not found in package: %s" % dskconv)

        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        script = os.path.join(self.recipe_folder, "test.sh")
        # Run from a writable cwd: on OHOS the recipe/build folder may live on
        # HMDFS where getcwd() can fail; HMBS injects a writable TMPDIR/TMP/TEMP.
        cwd = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(cwd, exist_ok=True)
        except OSError:
            cwd = self.build_folder
        logfile = os.path.join(cwd, "test_package.log")

        # self.run() executes the test source file for real.  Redirect to a log
        # so the RESULT summary can be parsed deterministically; ignore_errors
        # lets us parse the summary before deciding pass/fail.
        cmd = '"%s" "%s" "%s" > "%s" 2>&1' % (shell, script, dskconv, logfile)
        self.run(cmd, env="conanrun", cwd=cwd, ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test.sh log:\n" + "\n".join(out.splitlines()[-16:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException(
                "test.sh produced no RESULT line - harness broken; log tail:\n%s"
                % "\n".join(out.splitlines()[-16:])
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "%s %s %s" % (shell, script, dskconv),
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, separators=(",", ":"))
        )
        if not ok:
            raise RuntimeError(
                "joyce consumer smoke tests: %d/%d passed" % (passed, discovered)
            )
