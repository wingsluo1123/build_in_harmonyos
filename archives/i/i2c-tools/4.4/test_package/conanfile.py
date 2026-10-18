#!/usr/bin/env python3
"""Hardware-free consumer checks for the packaged i2c-tools v4.4."""

import json
import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class I2cToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "2"])

    def test(self):
        package_folder = self.dependencies["i2c-tools"].package_folder
        test_binary = os.path.join(self.build_folder, "test_i2c_api")
        cases = []

        def record(name, passed, output=""):
            cases.append((name, bool(passed)))
            self.output.info(f"TEST {name}: {'PASS' if passed else 'FAIL'}")
            if output:
                self.output.info(output.rstrip())

        runenv = VirtualRunEnv(self).vars()
        with runenv.apply():
            for tool in ("i2cdetect", "i2cdump", "i2cset", "i2cget", "i2ctransfer"):
                executable = os.path.join(package_folder, "sbin", tool)
                result = subprocess.run(
                    [executable, "-V"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                record(
                    f"{tool}_version",
                    result.returncode == 0 and re.search(r"\b4\.4\b", result.stdout) is not None,
                    result.stdout,
                )

            detect = os.path.join(package_folder, "sbin", "i2cdetect")
            result = subprocess.run(
                [detect, "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            record("i2cdetect_list_without_bus_access", result.returncode == 0, result.stdout)

            for name, argv in (
                ("i2cdetect_rejects_out_of_range_bus", [detect, "1048576"]),
                (
                    "i2cget_rejects_out_of_range_bus",
                    [os.path.join(package_folder, "sbin", "i2cget"), "1048576", "0x50"],
                ),
            ):
                result = subprocess.run(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                record(
                    name,
                    result.returncode == 1 and "I2C bus out of range" in result.stdout,
                    result.stdout,
                )

            api_output = os.path.join(self.build_folder, "test_i2c_api.output")
            self.run(
                f"{shlex.quote(test_binary)} > {shlex.quote(api_output)} 2>&1",
                env="conanrun",
                ignore_errors=True,
            )
            with open(api_output, "r", encoding="utf-8", errors="replace") as stream:
                output = stream.read()
            for case in (
                "read_byte_returns_ebadf",
                "write_byte_data_returns_ebadf",
                "read_block_data_returns_ebadf",
            ):
                record(
                    case,
                    f"PASS {case}" in output and "FAIL " not in output,
                    output,
                )

        passed = sum(1 for _, status in cases if status)
        failed = len(cases) - passed
        result = {
            "status": "pass" if failed == 0 and len(cases) == 11 else "fail",
            "framework": "Conan consumer checks",
            "hardware_required": False,
            "discovered": 11,
            "executed": len(cases),
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "xfail": 0,
            "broken": 0,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, sort_keys=True))
        if result["status"] != "pass":
            failed_names = [name for name, status in cases if not status]
            raise AssertionError("i2c-tools consumer checks failed: " + ", ".join(failed_names))
