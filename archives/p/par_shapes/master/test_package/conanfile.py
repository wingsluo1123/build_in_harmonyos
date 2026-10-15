#!/usr/bin/env python3
"""Conan test_package for par_shapes master — Conan L1 consumer test.

Builds test_par_shapes.c against the packaged header (CMakeDeps resolves
par_shapes::par_shapes) and runs a 12-case executor. The consumer defines
PAR_SHAPES_IMPLEMENTATION itself, so the test cannot pass when the package
is missing or its header is stale (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

# OHOS: /system/bin/sh (mksh) may fail to exec an ELF file directly; wrap in bash.
_SHELL_FALLBACK = "/data/service/hnp/bin/bash"


class ParShapesTestConan(ConanFile):
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

    def test(self):
        shell = os.environ.get("CONFIG_SHELL", _SHELL_FALLBACK)
        exe = os.path.join(self.cpp.build.bindirs[0], "test_par_shapes")
        # `bash -c '<binary>'` execs the ELF; passing the binary as bash's
        # argument would make bash interpret it as a shell script instead.
        self.run(f"{shell} -c '\"{exe}\"'", env="conanrun")
