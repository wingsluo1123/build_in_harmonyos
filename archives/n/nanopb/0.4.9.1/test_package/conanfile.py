#!/usr/bin/env python3
"""Conan consumer test for nanopb 0.4.9.1."""

import os
import shlex
import shutil
import stat

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NanopbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os).lower() == "ohos":
            self._sign_test_binary()

    def test(self):
        self.run("ctest --output-on-failure", env="conanrun")

    def _sign_test_binary(self):
        binary = None
        for root, _, filenames in os.walk(self.build_folder):
            if "test_nanopb" in filenames:
                binary = os.path.join(root, "test_nanopb")
                break
        if not binary:
            raise RuntimeError("test_package did not produce test_nanopb")

        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise RuntimeError("OHOS test package requires llvm-objcopy and binary-sign-tool")

        mode = os.stat(binary).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(binary, mode)
        self.run(
            f"{shlex.quote(objcopy)} --remove-section .codesign "
            f"{shlex.quote(binary)} 2>/dev/null || true"
        )
        signed = binary + ".nanopb-signed"
        try:
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(binary)} "
                f"-outFile {shlex.quote(signed)} -selfSign 1"
            )
            with open(signed, "rb") as source, open(binary, "wb") as target:
                shutil.copyfileobj(source, target)
        finally:
            if os.path.exists(signed):
                os.unlink(signed)
        if not (os.stat(binary).st_mode & stat.S_IXUSR):
            raise RuntimeError("signed OHOS test package binary is not executable")
