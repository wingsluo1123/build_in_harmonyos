import os

from conan import ConanFile
from conan.tools.build import can_run


class WheelTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        script = os.path.join(os.path.dirname(__file__), "test_wheel.py")
        pkg = self.dependencies["wheel"].package_folder
        # 沙箱 PATH 无 python3——绝对路径（同 packaging / biopython 的教训）
        import sys
        py = "/data/service/hnp/bin/python3" \
            if os.path.isfile("/data/service/hnp/bin/python3") else sys.executable
        self.run(f'{py} "{script}" "{pkg}"', env="conanrun")
