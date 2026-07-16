#!/usr/bin/env python3
"""Conan test_package for boost 1.84.0 — header-only test.

Tests that boost headers are available and usable.
R34: test must actually use the boost API (not just print a string).

Uses direct compilation instead of CMake to avoid profile compiler path issues
on local OHOS environments where /data/service/hnp/bin/clang++ may not exist.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BoostTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get boost include directory from the dependency package folder
        boost_pkg = self.dependencies["boost"].package_folder
        include_dir = os.path.join(boost_pkg, "include")
        
        cppstd = self.settings.compiler.cppstd
        test_src = os.path.join(self.source_folder, "test.cpp")
        test_bin = os.path.join(self.build_folder, "test_boost")
        
        # Compile test using clang++ from PATH (not profile's compiler path)
        self.run(f"clang++ -std=c++{cppstd} -O2 -I{include_dir} {test_src} -o {test_bin}")
        if can_run(self):
            self.run(f'"{test_bin}"', env="conanrun")
