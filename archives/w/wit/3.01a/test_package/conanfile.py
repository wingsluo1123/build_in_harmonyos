#!/usr/bin/env python3
"""test_package for wit 3.01a - consumer run of the installed wit/wwt/wdf tools.

Check 1: version banners of all three installed binaries (v3.01a r7464).
Check 2: ELF header sanity (ELF64 little endian AArch64 PIE).
Check 3: functional smoke with crafted fixtures - a minimal raw Wii disc
         image and a hand built WDF v1 container: wit FTYPE file type
         detection, wdf +DUMP structure parsing and a byte exact
         wdf +CAT payload roundtrip.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class WitTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building without emulator: test_package skipped")
            return
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        self.run('"{}" test_wit.sh'.format(shell), env="conanrun")
