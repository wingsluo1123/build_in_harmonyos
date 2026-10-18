import io
import json
import os
import re
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

class SiconosTestConan(ConanFile):
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
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        checks = 0
        for name in ("test_siconos", "test_dynamics"):
            output = io.StringIO()
            self.run('"{}"'.format(os.path.join(self.cpp.build.bindir, name)),
                     env="conanrun", stdout=output)
            log = output.getvalue()
            self.output.info(log)
            result = re.search(r"CONSUMER_CHECKS=(\d+) FAILURES=(\d+)", log)
            if not result or int(result.group(2)) or not int(result.group(1)):
                raise ConanException("Missing or failed consumer assertions")
            checks += int(result.group(1))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True, "passed": True, "consumer_passed": checks,
            "consumer_total": checks, "command": "test_siconos; test_dynamics"}))
        report = os.path.join(self.dependencies["siconos"].package_folder,
                              "reports", "upstream-results.json")
        with open(report, encoding="utf-8") as stream:
            result = json.load(stream)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            {key: value for key, value in result.items() if key != "groups"}))
