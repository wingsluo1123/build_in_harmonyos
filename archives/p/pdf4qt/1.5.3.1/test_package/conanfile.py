#!/usr/bin/env python3
"""Test package — pdf4qt 1.5.3.1 core library functional test.

Verifies that Pdf4QtLibCore can be linked and its API called on OHOS/arm64.
Uses direct compilation instead of CMakeDeps to avoid qtbase cmake name mismatch.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain


class TestPdf4QtConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get dependency info
        pdf4qt = self.dependencies["pdf4qt"]
        qtbase = self.dependencies["qtbase"]

        # Build paths
        pdf4qt_inc = os.path.join(pdf4qt.cpp_info.includedirs[0], "Pdf4QtLibCore")
        qt_inc = qtbase.cpp_info.includedirs[0]
        qt_lib = qtbase.cpp_info.libdirs[0]
        pdf4qt_lib = pdf4qt.cpp_info.libdirs[0]

        test_src = os.path.join(self.source_folder, "test_main.cpp")
        test_bin = os.path.join(self.build_folder, "test_pdf4qt")

        # Compile the test program
        self.run(
            f"clang++ -std=c++20 -stdlib=libc++ -fPIC "
            f"-I{pdf4qt_inc} -I{qt_inc} -I{qt_inc}/QtCore "
            f"{test_src} "
            f"-L{pdf4qt_lib} -lPdf4QtLibCore -lblend2d "
            f"-L{qt_lib} -lQt6Core -lQt6Gui -lQt6Xml "
            f"-Wl,-rpath,{pdf4qt_lib} -Wl,-rpath,{qt_lib} "
            f"-o {test_bin}"
        )

        # Run the test to verify pdf4qt library is functional
        self.run(f"{test_bin}")
