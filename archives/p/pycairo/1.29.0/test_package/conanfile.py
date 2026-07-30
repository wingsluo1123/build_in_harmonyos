from conan import ConanFile
from conan.tools.build import cross_building


class PycairoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: package execution is skipped.")
            return
        self.run("python3 test.py", env="conanrun")
