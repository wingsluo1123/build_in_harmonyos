from __future__ import annotations

import os
import sys
from conan import ConanFile


class WqyTestConan(ConanFile):
    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["wqy"].package_folder
        ttc = os.path.join(package_folder, "res", "fonts", "wqy-zenhei.ttc")
        tests = os.path.join(self.source_folder, "test_consumer_ttc.py")
        consumer = os.path.join(self.source_folder, "consumer_ttc.py")

        self.run(
            f'"{sys.executable}" -m unittest discover -s "{self.source_folder}" '
            f'-p test_consumer_ttc.py -v',
            env=None,
        )
        self.run(f'"{sys.executable}" "{consumer}" "{ttc}"', env=None)
