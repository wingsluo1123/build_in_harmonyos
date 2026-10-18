#!/usr/bin/env python3
"""Functional consumer test for the packaged vbindiff binary."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class VbindiffTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The consumer script decides the exit code, so the only thing chosen
        # here is which shell carries it. Keep the test executable when L1e
        # invokes conan test with only its host profile; the build context can
        # otherwise default to Linux.
        if str(self.settings.os) == "OHOS" or can_run(self):
            # Optional HNP bash is not installed on every OHOS image; honour a
            # profile-provided CONFIG_SHELL first and fall back to the system
            # POSIX shell, which is always present. The script itself uses no
            # bash-only syntax (verified with sh -n).
            default_shell = (
                "/bin/sh" if str(self.settings.os) == "OHOS" else "bash"
            )
            shell = os.environ.get("CONFIG_SHELL") or default_shell
            script = os.path.join(self.source_folder, "test_vbindiff.sh")
            # Pass the packaged vbindiff by absolute path so every assertion
            # genuinely depends on the artifact this recipe produced.
            pkg_folder = self.dependencies["vbindiff"].package_folder
            bin_path = os.path.join(pkg_folder, "bin", "vbindiff")
            self.run(f'{shell} "{script}" "{bin_path}"', env="conanrun")
