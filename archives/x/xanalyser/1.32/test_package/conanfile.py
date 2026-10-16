#!/usr/bin/env python3
"""Conan test_package — xanalyser 1.32.

R34 substantive consumer test: xanalyser is a GUI application (it ships no
linkable library), so the consumer test executes the packaged binary
(``bin/xanalyser``) instead of compiling a consumer program:

  * packaged-artifact completeness (program + man page + Motif app-defaults
    resource file),
  * OHOS-specific platform properties of the produced ELF (musl aarch64
    interpreter, AArch64 machine, Conan-managed Motif/X11 load closure),
  * the real runtime behaviour of the program (dynamic loader resolves the
    whole libXm/libXt/X11 chain, then upstream's Xt path reports the missing
    display and exits - it must not hang and must not die in the loader).

All checks are performed by executing the binary and inspecting its output
(no assert macros) in test_xanalyser.sh; removing the package artifacts makes
the test fail, so it also passes the CI L1e destructive reverse check.
"""
import os
import shutil

from conan import ConanFile


class XanalyserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = ("test_xanalyser.sh",)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["xanalyser"].package_folder
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_xanalyser.sh"
        )
        self.output.info(f"running consumer test: sh {script} {pkg_folder} {readelf}")
        # env="conanrun" supplies LD_LIBRARY_PATH with the packaged
        # Motif/X11/libxpm libraries.
        self.run(f'sh "{script}" "{pkg_folder}" "{readelf}"', env="conanrun")
