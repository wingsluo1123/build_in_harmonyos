#!/usr/bin/env python3
"""Conan test_package for semtag 0.2.0 — shell tool consumer test.

Both scripts drive the packaged tool itself (`bash <pkg>/bin/semtag ...`)
inside throw-away Git repositories built by the test, so the assertions
exercise semtag's real tag parsing, version bumping and tag creation rather
than a stub.

The interpreter is passed explicitly instead of relying on the shebang: the
packaged script starts with `#!/data/service/hnp/bin/bash` (HarmonyOS path,
knowledge entry E037), which does not exist on a non-HarmonyOS build host. The
shebang itself, and that the hnp bash really runs the packaged script, are
asserted in test_semtag_ohos.sh — those assertions report SKIP when the hnp
bash is absent instead of silently passing.

The scripts build their fixtures with printf, never with here-documents: on
the HarmonyOS device here-documents are backed by temp files under the
read-only /tmp (knowledge draft E547-draft-3028).
"""

import os

from conan import ConanFile


class SemtagTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["semtag"].package_folder
        semtag_bin = os.path.join(pkg_folder, "bin", "semtag")

        generic = os.path.join(self.recipe_folder, "test_semtag.sh")
        self.run(f'sh "{generic}" "{semtag_bin}"')

        ohos = os.path.join(self.recipe_folder, "test_semtag_ohos.sh")
        self.run(f'sh "{ohos}" "{semtag_bin}"')
