import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            script = os.path.join(os.path.dirname(__file__), "test_pycountry.py")
            # The Conan sandbox PATH has no python3 — use an absolute path.
            py = "/data/service/hnp/bin/python3" if os.path.isfile(
                "/data/service/hnp/bin/python3"
            ) else sys.executable
            # The package folder is passed so the script can prove that what it
            # imported really came from the packaged tree. This machine also has
            # an importable pycountry in the user site directory (installed while
            # measuring the xkeyboard-config suite), so without that check the
            # test would still pass with the package folder emptied — which the
            # CI destructive negative test (R34/L1e) does deliberately.
            # PYTHONNOUSERSITE=1 keeps the user site out of sys.path so the two
            # environments cannot disagree.
            pkg = self.dependencies["pycountry"].package_folder
            self.run(f'PYTHONNOUSERSITE=1 {py} "{script}" "{pkg}"', env="conanrun")
