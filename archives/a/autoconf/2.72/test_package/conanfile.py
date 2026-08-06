from conan import ConanFile
from conan.tools.build import can_run


class AutoconfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    exports_sources = "test.sh"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: autoconf runtime smoke skipped")
            return

        self.run("sh test.sh", env="conanbuild")
