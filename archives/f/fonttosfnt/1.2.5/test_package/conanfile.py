#!/usr/bin/env python3
"""test_package for the fonttosfnt executable -- runs the installed `fonttosfnt` binary.

Consumer verification: invoke the installed BDF->sfnt wrapper the way a real
user would (per README/man), turn the bundled minimal BDF (font.bdf, 4 glyphs)
into a real `.otb` file, and assert the emitted sfnt structure plus option and
error-path behaviour.

The output file is written into a scratch directory under $TMPDIR (created
with mktemp -d and removed again on exit) because fonttosfnt opens its -o
target "wb+" and seeks in it -- unlike a pure stream filter it cannot write to
/dev/null. Nothing is written next to this conanfile, so no artifact can be
swept into the recipe commit by a directory-level `git add` (§12.71②).

R34 / PF3: this test actually executes the package under test -- it is not a
print-only stub.
"""
import os

from conan import ConanFile


class FonttosfntTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries, so run through
        # bash. Seed PWD so bash does not start with a failing getcwd() under
        # HMDFS setgid trees (E386 family); test.sh and font.bdf live next to
        # this file.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        scratch = self.recipe_folder
        self.run(
            f'cd "{scratch}" && PWD="{scratch}" "{bash}" test.sh',
            env="conanrun",
        )
