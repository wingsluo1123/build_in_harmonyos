import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class TlsrptTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        script = os.path.join(self.source_folder, "check_reports.py")
        executable = os.path.join(self.cpp.build.bindirs[0], "test_tlsrpt")
        command = " ".join(shlex.quote(part) for part in (sys.executable, script, executable))
        rc = self.run(command, env="conanrun", ignore_errors=True)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": rc == 0, "command": command,
            "consumer_total": 14, "consumer_passed": 14 if rc == 0 else 0,
        }), flush=True)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests", "discovered": 0, "executed": 0,
            "passed": 0, "failed": 0, "skipped": 0,
            "reason": "v0.5.0 Makefile.am has no TESTS/check_PROGRAMS; demo.c is an example, not an automated test suite",
        }), flush=True)
        if rc:
            raise ConanException("tlsrpt functional consumer tests failed")
