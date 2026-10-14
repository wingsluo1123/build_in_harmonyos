#!/usr/bin/env python3
"""Conan consumer test for tabixpp 1.1.2.

Builds and runs test_tabixpp.cpp against the packaged libtabix to verify a
downstream consumer can include tabix.hpp, link the library, and drive the
public Tabix API (getHeader / setRegion / getNextLine) over a bgzf-compressed,
tabix-indexed VCF produced at test time with the htslib C API (BGZF +
tbx_index_build, no CLI tools needed).
The test binary emits HMBS_TEST_PACKAGE_RESULT with its real counters.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TabixppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_tabixpp")
            self._sign(executable)
            self.run('"{}"'.format(executable), env="conanrun")

    @staticmethod
    def _sign(executable):
        """OHOS requires ELF binaries to be code-signed before execution."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(executable):
            return
        if not os.path.isfile(signer):
            return
        signed = executable + ".signed"
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", executable], check=False)
        subprocess.run(
            [signer, "sign", "-inFile", executable, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
