#!/usr/bin/env python3
"""Conan test_package for gptfdisk 1.0.10 (L1 official test).

gptfdisk ships four CLI tools (gdisk/cgdisk/sgdisk/fixparts); there is no
library API to link against, so the consumer test executes the packaged
binaries and asserts real behaviour (R34 substantive dependency):

  1. all four binaries are packaged and non-empty;
  2. test_gptfdisk_e2e.py drives sgdisk end-to-end on a scratch 64 MiB image
     (zap -> new partition -> type/name -> print -> info -> backup -> wipe ->
     restore -> print), asserts the on-disk GPT ("EFI PART") and protective
     MBR (0x55AA) signatures, pipes gdisk a p/q session, and smoke-runs
     fixparts and cgdisk (the latter through its documented no-TTY error
     path);
  3. ohos_specific_test.py (R53) asserts HarmonyOS-specific ELF properties
     with a pure-Python parser (no readelf/file dependency): ELF64 +
     e_machine=AArch64(183), PT_INTERP=/lib/ld-musl-aarch64.so.1, the OHOS
     .codesign section, no RPATH/RUNPATH, and no dynamic NEEDED for the
     system-name libraries (libuuid/libpopt/libncurses - all statically
     linked, R26).
"""
import os

from conan import ConanFile


class GptfdiskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = ("ohos_specific_test.py", "test_gptfdisk_e2e.py")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(pkg.package_folder, "bin")
        for tool in ("gdisk", "cgdisk", "sgdisk", "fixparts"):
            path = os.path.join(bindir, tool)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise Exception("expected CLI not packaged: {}".format(path))
            self.output.info("CLI packaged: {} ({} bytes)".format(
                tool, os.path.getsize(path)))

        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"
        self.run('"{}" "{}" "{}"'.format(
            python, os.path.join(self.source_folder, "ohos_specific_test.py"), bindir))
        self.run('"{}" "{}" "{}"'.format(
            python, os.path.join(self.source_folder, "test_gptfdisk_e2e.py"), bindir))
