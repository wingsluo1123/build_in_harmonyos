#!/usr/bin/env python3
"""Conan test_package for oed — portable OpenBSD ed(1) line editor CLI.

oed is a command-line tool, so the L1 test drives the installed `ed`
executable end to end (R34): real editing jobs (line addressing, regex
substitution, undo, global commands, large buffers) plus the HarmonyOS
specific scratch-file fallback path, since OHOS mounts /tmp read-only.
See test_package/test.sh for the individual assertions.
"""
import os

from conan import ConanFile


class OedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries; use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
