import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class VintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            pkg = self.dependencies["vint"].package_folder
            test_script = os.path.join(os.path.dirname(__file__), "check_vint.py")
            cmd = ('bash -c \'TMPDIR=/data/storage/el2/base/cache '
                   'exec "{}" "{}" "{}"\''.format(sys.executable, test_script, pkg))
            self.run(cmd, env="conanrun")
