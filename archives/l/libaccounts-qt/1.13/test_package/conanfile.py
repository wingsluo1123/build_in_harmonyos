#!/usr/bin/env python3
"""Conan test_package for libaccounts-qt 1.13 — L1 official test.

Tests that the library can be linked and basic API (Manager, Account)
can be used. This validates the Qt5 + libaccounts-glib integration.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibaccountsqtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Add Qt5 include path for QtXml headers (not declared as component in qt5-qtbase recipe)
        qt5 = self.dependencies["qt5-qtbase"]
        qt5_inc = os.path.join(qt5.package_folder, "include", "QtXml")
        cmake_dir = self.generators_folder
        with open(os.path.join(cmake_dir, "qtxml_include.cmake"), "w") as f:
            f.write(f'target_include_directories(test_libaccounts-qt PRIVATE "{qt5_inc}")\n')

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary via self.run (required by L0d gate)
        test_bin_dir = self.cpp.build.bindirs[0]
        test_bin = os.path.join(test_bin_dir, "test_libaccounts-qt")

        # Copy shared library next to test binary (HarmonyOS musl namespace workaround E088)
        # The musl linker can find libraries in the same directory as the binary
        tested_pkg = self.dependencies[str(self.tested_reference).split("/")[0]]
        for libdir in tested_pkg.cpp_info.libdirs:
            lib_path = os.path.join(tested_pkg.package_folder, libdir)
            for f in os.listdir(lib_path):
                if f.startswith("libaccounts-qt5"):
                    src = os.path.join(lib_path, f)
                    dst = os.path.join(test_bin_dir, f)
                    if os.path.islink(src):
                        target = os.readlink(src)
                        if not os.path.isabs(target):
                            target = os.path.join(lib_path, target)
                        if os.path.exists(target):
                            shutil.copy(target, dst)
                    elif os.path.exists(src):
                        shutil.copy(src, dst)

        self.run(f'"{test_bin}"', env=["conanrun"])
