import os

from conan import ConanFile


class ApitraceTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["apitrace"].package_folder
        self.run(f"bash test_apitrace.sh {pkg_folder}", env="conanrun")
        self.output.info("apitrace: OK")
