#!/usr/bin/env python3
"""Conan test_package — shfs 0.35

L1 consumer test. Runs test_shfs.sh, which drives the packaged shfsmount /
shfsumount binaries plus the two upstream capability probes shipped in res/shfs:
9 cases / 9 assertions (2 upstream + 2 HarmonyOS-specific + 5 CLI contract).

R34: every case really executes the packaged binaries — no API-only stubs.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class ShfsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["shfs"].package_folder
        script = os.path.join(self.recipe_folder, "test_shfs.sh")
        # OHOS: /bin/sh is toybox ash; prefer a real bash so the harness behaves
        # identically under CI and by hand. Probe candidates instead of trusting a
        # bare env var — an unset/bogus CONFIG_SHELL must not pick a missing binary.
        candidates = (os.environ.get("CONFIG_SHELL"), shutil.which("bash"),
                      "/data/service/hnp/bin/bash", "/bin/sh")
        shell = next((c for c in candidates if c and os.path.exists(c)), None)
        if shell is None:
            raise ConanInvalidConfiguration("no usable shell found for test_shfs.sh")
        self.run(f'"{shell}" "{script}" "{pkg}"', env="conanrun")
