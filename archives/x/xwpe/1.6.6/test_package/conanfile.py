import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["xwpe"].package_folder
            # 把 ncurses 包目录也传过去：检查③要按「该包是否提供 .so」决定 NEEDED 的期望
            nc = self.dependencies["ncurses"].package_folder
            test_script = os.path.join(os.path.dirname(__file__), "check_xwpe.py")
            cmd = ('bash -c \'TMPDIR=/data/storage/el2/base/cache '
                   'exec "{}" "{}" "{}" "{}"\''.format(sys.executable, test_script, pkg, nc))
            self.run(cmd, env="conanrun")
