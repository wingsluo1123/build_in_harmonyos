#!/usr/bin/env python3
"""Consumer test for libassuan 3.0.2.

Builds test_libassuan against the packaged libassuan and runs a real Assuan
client/server ECHO/BYE transaction over a Unix socketpair.  test.c prints one
"CASE PASS" line per distinct functional check; this file counts exactly those
lines as the deterministic executed/passed figure for HMBS_TEST_PACKAGE_RESULT
(the test binary exits non-zero on any failure, so a green run has passedCount
== discovered == 5).

The upstream `make check` result is emitted by the recipe's build() (the
automake serial driver in the patched tests/Makefile.in prints
HMBS_UPSTREAM_TEST_RESULT directly), so test_package only has to report its own
consumer-test evidence here.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibassuanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    # test.c emits exactly these real functional checks.
    _CONSUMER_CASES = 5

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        # HMBS pins SHELL/CONFIG_SHELL to /bin/sh on the device; the HNP bash
        # cannot getcwd() on HMDFS build trees, so never fall back to it.
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        if "hnp/bin/bash" in shell:
            shell = "/bin/sh"
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_libassuan")
        log_path = os.path.join(self.build_folder, "test_package.log")
        try:
            self.run(
                "{} -c '\"{}\"' > {} 2>&1".format(
                    shell, test_binary, log_path
                ),
                env="conanrun",
            )
        except ConanException:
            pass

        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)

        passed = out.count("CASE PASS")
        discovered = self._CONSUMER_CASES
        marker = {
            "executed": True,
            "passed": discovered > 0 and passed == discovered,
            "command": "./test_libassuan (socketpair Assuan ECHO/BYE transaction)",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise ConanException(
                "test_package failed: {}/{} consumer cases passed".format(
                    passed, discovered
                )
            )
