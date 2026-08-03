#!/usr/bin/env python3
"""Conan test_package for chicken 5.4.0 — compiler toolchain smoke test (R34).

Verifies the CHICKEN toolchain end-to-end (实质调用被测包 API/二进制):
  1. csi -version                (interpreter runs and reports version)
  2. csc compiles test_hello.scm  (compiler driver invokes the chicken compiler)
  3. the compiled binary executes (factorial + string ops + assertions)
"""
import os

from conan import ConanFile


class ChickenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["chicken"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        csc = os.path.join(bin_dir, "csc")
        csi = os.path.join(bin_dir, "csi")
        src = os.path.join(self.source_folder, "test_hello.scm")
        out = os.path.join(self.build_folder, "test_hello")

        # 1. Interpreter runs and reports version (executes the csi binary)
        self.run(f'"{csi}" -version', env="conanrun")

        # 2. Compiler driver compiles a real Scheme program (uses csc + chicken)
        self.run(f'"{csc}" -o "{out}" "{src}"', env="conanrun")

        # 3. Compiled binary runs and validates factorial/string results
        self.run(f'"{out}"', env="conanrun")
