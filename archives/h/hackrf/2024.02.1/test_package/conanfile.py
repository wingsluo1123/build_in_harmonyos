from conan import ConanFile
from conan.tools.build import can_run


class TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            self.run("hackrf_info --help", env="conanrun")
