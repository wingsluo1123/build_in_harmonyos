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
            pkg = self.dependencies["ppft"].package_folder
            test_script = os.path.join(os.path.dirname(__file__), "check_ppft.py")
            # ppft 零运行期依赖；仍按两条实测教训显式拼 PYTHONPATH
            # （Conan 1 的 env_info 不进 conanrun；Conan 2 的 run(env=…) 只接受 list）
            site = os.path.join(pkg, "lib", "python3.12", "site-packages")
            cmd = ('bash -c \'PYTHONPATH="{}" TMPDIR=/data/storage/el2/base/cache '
                   'exec "{}" "{}" "{}"\''.format(site, sys.executable,
                                                  test_script, pkg))
            self.run(cmd, env="conanrun")
