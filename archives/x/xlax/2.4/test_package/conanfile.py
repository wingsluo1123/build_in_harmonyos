#!/usr/bin/env python3
"""Consumer test for the packaged xlax executable.

xlax is an Xt/Athena-widgets desktop tool; HarmonyOS PC has no X server, so
the test drives the installed binary through the headless paths the
adaptation provides: --version, the new --selftest (12 programmatic checks
over the linked libXt / libXaw / libXmu / libX11 code) and the expected
no-display failure, which proves the packaged binary really loads and
initialises the X11 stack recorded in its DT_NEEDED entries.

The test always runs the shell harness (no can_run guard): CI's destructive
negative gate (L1e) moves the package artifacts away and re-runs this test,
which must then fail because the binary it invokes is gone.
"""
import os
import shutil

from conan import ConanFile


class XlaxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_xlax.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["xlax"].package_folder
        executable = os.path.join(package_folder, "bin", "xlax")
        script = os.path.join(self.source_folder, "test_xlax.sh")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(shell):
            shell = shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"
        self.run(
            f'"{shell}" "{script}" "{executable}" "{package_folder}"',
            env="conanrun",
        )
