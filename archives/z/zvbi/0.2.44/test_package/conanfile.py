#!/usr/bin/env python3
"""Consumer test for zvbi/0.2.44.

Builds a small C consumer against the installed package and exercises the
public decode/export API surface with exact oracles taken from the upstream
sources (see test_zvbi.c header for the per-check provenance).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class ZvbiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068, libabw precedent).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # The verdict is taken by running the consumer directly under the
        # package's runtime environment (env="conanrun"); ctest does not
        # inherit conan's runtime environment (opustags precedent: without
        # VirtualRunEnv + env="conanrun" the run fails to resolve the
        # dependency .so at load time and misreports "build failure").
        # Running it directly also prints every individual assertion into
        # the build log.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_zvbi"),
                 env="conanrun")
