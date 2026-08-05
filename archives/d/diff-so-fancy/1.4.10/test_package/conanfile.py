import os

from conan import ConanFile
from conan.tools.build import can_run


class DiffSoFancyTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        executable = os.path.join(
            self.dependencies["diff-so-fancy"].package_folder,
            "bin",
            "diff-so-fancy",
        )
        test_script = os.path.join(self.source_folder, "test_diff_so_fancy.py")
        self.run(
            f'python3 "{test_script}" "{executable}"',
            env="conanrun",
        )
