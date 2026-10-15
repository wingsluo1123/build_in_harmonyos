#!/usr/bin/env python3
"""test_package for xaric/0.13.9.

Drives the installed xaric through a PTY (xaric's main() refuses to run
without a TTY on stdin) and asserts the version output and the installed
help data.  See test_xaric.sh for the per-check assertions and the
OHOS-specific rationale.
"""
import os
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XaricTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["xaric"].package_folder
        bindir = os.path.join(package_folder, "bin")
        datadir = os.path.join(package_folder, "share", "xaric")
        binary = os.path.join(bindir, "xaric")
        # The artifact checks run on every host, cross builds included, so the
        # test keeps depending on the packaged output even where the binary
        # cannot be executed here (R34).
        self._check_artifacts(binary, datadir)
        if not can_run(self):
            self.output.info(
                "Cross build: packaged xaric verified as an AArch64 ELF; the "
                "PTY run in test_xaric.sh executes on the device")
            return
        script = os.path.join(self.recipe_folder, "test_xaric.sh")
        self.run('sh "%s" "%s" "%s"' % (script, bindir, datadir), env="conanrun")

    def _check_artifacts(self, binary, datadir):
        for path in (binary, os.path.join(datadir, "help", "help")):
            if not os.path.isfile(path):
                raise ConanException("xaric package is missing %s" % path)
        if not os.access(binary, os.X_OK):
            raise ConanException("packaged xaric is not executable: %s" % binary)
        with open(binary, "rb") as handle:
            ident = handle.read(20)
        if ident[:4] != b"\x7fELF":
            raise ConanException("packaged xaric is not an ELF binary")
        # e_machine lives at offset 18 (Elf64_Half): 0xB7 is EM_AARCH64.
        machine = struct.unpack_from("<H", ident, 18)[0]
        if machine != 0xB7:
            raise ConanException(
                "packaged xaric has e_machine=0x%X, expected 0xB7 (AArch64)"
                % machine)
        self.output.info("packaged xaric: AArch64 ELF present, help data installed")
