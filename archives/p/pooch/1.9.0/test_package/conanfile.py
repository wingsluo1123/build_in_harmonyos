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
            pkg = self.dependencies["pooch"].package_folder
            test_script = os.path.join(os.path.dirname(__file__), "check_pooch.py")
            # 显式拼 PYTHONPATH（两条实测教训）：①Conan 1 时代的 env_info 不会进
            # conanrun 环境；②Conan 2 的 self.run(env=…) 只接受 list →
            # 这里用 bash 内联 export 后再 exec。
            sites = []
            for name in ("pooch", "platformdirs", "packaging", "requests",
                         "chardet", "idna", "urllib3", "certifi"):
                try:
                    dep = self.dependencies[name]
                except Exception:
                    continue
                site = os.path.join(dep.package_folder, "lib", "python3.12",
                                    "site-packages")
                if os.path.isdir(site):
                    sites.append(site)
            py = os.pathsep.join(sites)
            cmd = ('bash -c \'PYTHONPATH="{}" TMPDIR=/data/storage/el2/base/cache '
                   'exec "{}" "{}" "{}"\''.format(py, sys.executable,
                                                  test_script, pkg))
            self.run(cmd, env="conanrun")
