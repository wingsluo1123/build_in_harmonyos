#!/usr/bin/env python3
"""Conan test_package — somagic 1.1 consumer verification.

somagic is a command-line tool suite (no library, no public headers), so the
consumer test drives the four installed executables end-to-end (R34): it runs
them through their real CLI surface and asserts on actual behavior —
the --version/--help banners plus the deterministic device-free error paths
that exercise both linked libraries (libgcrypt firmware CRC validation and the
libusb-1.0 init / device enumeration).

The assertions live in test.sh; this recipe only drives the shell that runs it
(OHOS /system/bin/sh is mksh and cannot launch ELF binaries, so bash is used,
matching the qdl/lsm/aa3d precedent). The script is given the absolute package
bin directory so it never depends on the ambient PATH.
"""

import os

from conan import ConanFile


class SomagicTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def configure(self):
        # Same reason as the main recipe's generate(): without this conf Conan
        # emits a deactivation preamble at the top of conanrunenv-<id>.sh that
        # forks one `printenv` per exported variable as soon as the script is
        # sourced. On a fork-starved worker that preamble itself returns EAGAIN
        # before the test command starts. Switching to the function form makes
        # `source` a pure function definition with zero forks while still
        # exporting the full run environment. It must be set in configure():
        # this package declares VirtualRunEnv explicitly, and explicit
        # generators run before generate(), so a conf set there would be too late.
        self.conf.define("tools.env:deactivation_mode", "function")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.recipe_folder, "test.sh")
        bin_dir = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin"
        )
        self.run(f'"{shell}" "{script}" "{bin_dir}"', env="conanrun")
