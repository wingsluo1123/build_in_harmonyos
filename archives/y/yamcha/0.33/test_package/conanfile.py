#!/usr/bin/env python3
"""Installed-package consumer tests for yamcha 0.33."""

import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class YamchaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # HMDFS does not support GNU make's FIFO jobserver.
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    @staticmethod
    def _run_checked(argv):
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=180, check=False
        )
        if result.returncode != 0:
            raise AssertionError(
                f"command failed ({result.returncode}): {argv!r}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result.stdout + result.stderr

    def test(self):
        if not can_run(self):
            self.output.warning("cross-build: installed-package tests skipped")
            return

        dependency = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dependency.package_folder, "bin")
        yamcha = os.path.join(bindir, "yamcha")
        if not os.path.isfile(yamcha):
            raise AssertionError("bin/yamcha was not installed")

        version_text = self._run_checked([yamcha, "--version"])
        if "0.33" not in version_text:
            raise AssertionError(f"yamcha did not report version 0.33: {version_text}")

        help_text = self._run_checked([yamcha, "--help"])
        if "Usage" not in help_text:
            raise AssertionError(f"yamcha --help is missing usage text: {help_text}")

        api_test = os.path.join(self.cpp.build.bindirs[0], "yamcha_api_test")
        self.run(f'"{api_test}"', env="conanrun")
