#!/usr/bin/env python3
"""test_package for the bdftopcf executable — runs the installed `bdftopcf` binary.

Consumer verification: invoke the installed font compiler the way a real user
would (per README/man), compile a bundled minimal BDF (font.bdf, 2 glyphs) into
PCF, and assert the emitted PCF stream plus option and error-path behaviour
(7 assertions, all artifact-free: `-o /dev/null` and stdout pipes only, because
OHOS `/tmp` is read-only and stray files in this folder get swept into the
commit by a directory-level `git add`).

R34 / PF3: this test actually executes the package under test — it is not a
print-only stub.
"""
import os

from conan import ConanFile


class BdftopcfTestConan(ConanFile):
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
