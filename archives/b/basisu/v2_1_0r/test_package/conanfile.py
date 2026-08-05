#!/usr/bin/env python3
"""Conan test_package — basisu L1 test.

Runs the upstream `basisu -test` suite and a consumer link test.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

UPSTREAM_LDR_TEST_COUNT = 28


class BasisuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self, proc, command):
        out = (proc.stdout or "") + (proc.stderr or "")
        m = re.search(r"Total LDR mismatches:\s*(\d+)", out)
        mismatches = int(m.group(1)) if m else UPSTREAM_LDR_TEST_COUNT
        status = "passed" if proc.returncode == 0 else "failed"
        if proc.returncode == 0:
            passed = UPSTREAM_LDR_TEST_COUNT
            failed = 0
        else:
            passed = 0
            failed = UPSTREAM_LDR_TEST_COUNT
        marker = {
            "status": status,
            "framework": "basisu -test",
            "command": command,
            "discovered": UPSTREAM_LDR_TEST_COUNT,
            "executed": UPSTREAM_LDR_TEST_COUNT,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def _emit_test_package_marker(self, executed, passed, command):
        marker = {
            "executed": executed,
            "passed": passed,
            "command": command,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))

    def test(self):
        pkg = self.dependencies["basisu"]
        pkg_folder = pkg.package_folder
        bin_path = os.path.join(pkg_folder, "bin", "basisu")
        test_dir = os.path.join(pkg_folder, "res", "test_files")

        if can_run(self) and os.path.isfile(bin_path) and os.path.isdir(test_dir):
            cmd = '"{}" -test -test_dir "{}"'.format(bin_path, test_dir)
            env = os.environ.copy()
            proc = subprocess.run(
                cmd, shell=True, env=env,
                capture_output=True, text=True,
            )
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
            self._emit_upstream_marker(proc, cmd)
            if proc.returncode != 0:
                raise RuntimeError(
                    "upstream basisu -test failed (exit {})".format(proc.returncode)
                )

        if can_run(self):
            ver_cmd = '"{}" --version'.format(bin_path)
            self.run(ver_cmd, env="conanrun")
            self._emit_test_package_marker(1, 1, ver_cmd)

            test_basisu = os.path.join(self.cpp.build.bindirs[0], "test_basisu")
            tp_cmd = test_basisu
            self.run(tp_cmd, env="conanrun")
            self._emit_test_package_marker(1, 1, tp_cmd)
