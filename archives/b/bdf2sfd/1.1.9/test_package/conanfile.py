#!/usr/bin/env python3
"""test_package for the bdf2sfd executable — runs the installed `bdf2sfd` binary.

Consumer verification: invoke the installed converter the way a real user would
(per README), convert a bundled minimal BDF (font.bdf, 2 glyphs) into SFD on the
fly, and assert the emitted SFD structure plus -v/-h/-f/-p option behaviour.

R34 / PF3: this test actually executes the package under test — it is not a
print-only stub. All assertions run on captured command output, so nothing is
written to disk (OHOS /tmp is read-only).
"""
import os

from conan import ConanFile


class Bdf2SfdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries → wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Seed PWD so bash does not start with a failing getcwd() under HMDFS
        # setgid trees (E386 family); test.sh and font.bdf live next to this file.
        scratch = self.recipe_folder
        self.run(
            f'cd "{scratch}" && PWD="{scratch}" "{bash}" test.sh',
            env="conanrun",
        )
