#!/usr/bin/env python3
"""Conan test_package for rfcdiff 1.49 — shell tool L1 test.

Both scripts drive the packaged tool itself (`bash <pkg>/bin/rfcdiff ...`) on
real Internet-Draft fixtures, so the assertions exercise rfcdiff's actual
header/footer stripping, awk based diff rendering and temp-dir handling rather
than a stub.

The interpreter is passed explicitly instead of relying on the shebang: the
packaged script starts with `#!/data/service/hnp/bin/bash` (HarmonyOS path,
knowledge entry E165), which does not exist on a non-HarmonyOS build host. The
shebang itself, and that the shebang interpreter really runs the packaged
script, are asserted in test_rfcdiff_ohos.sh — that assertion reports SKIP
when the interpreter is absent instead of silently passing.
"""

import os
import shutil

from conan import ConanFile


class RfcdiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["rfcdiff"].package_folder
        rfcdiff_bin = os.path.join(pkg_folder, "bin", "rfcdiff")
        work = os.path.join(self.build_folder, "rfcdiff-work")
        os.makedirs(work, exist_ok=True)

        try:
            generic = os.path.join(self.recipe_folder, "test_rfcdiff.sh")
            self.run(f'bash "{generic}" "{rfcdiff_bin}" "{work}"')

            ohos = os.path.join(self.recipe_folder, "test_rfcdiff_ohos.sh")
            self.run(f'bash "{ohos}" "{rfcdiff_bin}" "{work}"')
        finally:
            shutil.rmtree(work, ignore_errors=True)
