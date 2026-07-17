from conan import ConanFile
from conan.tools.build import cross_building
import os


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only compile+link verified")
            return
        tmux_bin = os.path.join(self.deps_cpp_info["tmux"].bindirs[0], "tmux")
        self.run(f"{tmux_bin} -V", env="conanrun")
