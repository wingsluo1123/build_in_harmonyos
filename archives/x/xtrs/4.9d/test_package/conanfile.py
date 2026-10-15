#!/usr/bin/env python3
"""Conan test_package for xtrs 4.9d.

Upstream has no automated tests, so the consumer test drives the three
headless CLI tools (hex2cmd, cmddump, mkdisk) with deterministic inputs, then
checks that the X11 emulator binary loads and reaches its display init (it
cannot run further without an X display, which is the documented runtime
limitation).
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 5


class XtrsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        for prog in ("xtrs", "mkdisk", "hex2cmd", "cmddump"):
            if not os.path.isfile(os.path.join(bindir, prog)):
                raise ConanException("required program not found: %s"
                                     % os.path.join(bindir, prog))

        here = os.path.dirname(os.path.abspath(__file__))
        workdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        bash = self._bash()
        inner = ('BIN_DIR=%s FIXTURE_DIR=%s TMPDIR=%s %s %s'
                 % (shlex.quote(bindir), shlex.quote(here),
                    shlex.quote(workdir), shlex.quote(bash),
                    shlex.quote(os.path.join(here, "test_xtrs.sh"))))
        if self.settings.os == "OHOS":
            command = "%s -c %s" % (shlex.quote(bash), shlex.quote(inner))
        else:
            command = inner
        rc = self.run(command, ignore_errors=True, env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": "test_xtrs.sh (hex2cmd/cmddump/mkdisk + xtrs load)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "xtrs ships no automated test suite (hand-written "
                      "Makefile; no make check/ctest/tests)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0,
            "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("xtrs test failed (rc=%s)" % rc)
