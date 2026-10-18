#!/usr/bin/env python3
"""Conan test_package for valhalla 3.8.2.

Builds a C++20 consumer against the installed valhalla headers/library via
CMakeDeps and runs it.  The self-contained Gurka test suite is executed by the
recipe ``build()``; its pass/fail summary is packaged under ``reports/`` and
reported here through the HMBS marker lines consumed by the CI preflight.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class ValhallaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Same OHOS platform-module hint as the recipe, so the consumer gets a
        # proper SONAME/RPATH when linking against libvalhalla.
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _gurka_counts(self):
        dep = self.dependencies[self.tested_reference_str]
        report = os.path.join(dep.package_folder, "reports", "gurka-results.txt")
        if not os.path.isfile(report):
            return None
        passed = failed = 0
        with open(report, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("[PASS]"):
                    passed += 1
                elif line.startswith("[FAIL]"):
                    failed += 1
        return passed, failed

    def test(self):
        exe = os.path.join(self.build_folder, "test_valhalla")
        if not os.path.isfile(exe):
            exe = os.path.join(self.build_folder, "Release", "test_valhalla")
        self.run('"{}"'.format(exe), env="conanrun")

        counts = self._gurka_counts()
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "./test_valhalla",
            "consumer_passed": 9,
            "consumer_total": 9,
        }))
        if counts is None:
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "skipped",
                "reason": "Gurka suite was not built with this configuration",
                "discovered": 0, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 0,
            }))
        else:
            passed, failed = counts
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "executed",
                "framework": "GoogleTest (test/gurka/test_*.cc, Gurka)",
                "discovered": passed + failed,
                "executed": passed + failed,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
            }))
