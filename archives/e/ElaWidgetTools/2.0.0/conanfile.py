#!/usr/bin/env python3
"""Conan recipe for ElaWidgetTools 2.0.0.

ElaWidgetTools is a Fluent-UI component library for Qt-Widget applications.
It depends on Qt5 (qtbase 5.15.2) which is installed as a system package
on HarmonyOS (not available as a Conan package).

The recipe uses CMAKE_PREFIX_PATH to locate the system-installed Qt5.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ElaWidgetToolsConan(ConanFile):
    name = "elawidgettools"
    version = "2.0.0"
    description = "Fluent-UI for Qt-Widget, based on Qt Fluent Design style component library"
    license = "MIT"
    homepage = "https://github.com/Liniyous/ElaWidgetTools"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt5 is a system-installed dependency (not a Conan package)
        qt5_path = os.path.expanduser("~/usr/local/Qt5")
        tc.variables["CMAKE_PREFIX_PATH"] = qt5_path
        # Qt5 on HarmonyOS uses libc++; ElaWidgetTools must match
        tc.variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-stdlib=libc++"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-stdlib=libc++"
        # Build static or shared library based on the shared option
        if self.options.shared:
            tc.variables["ELAWIDGETTOOLS_BUILD_STATIC_LIB"] = "OFF"
        else:
            tc.variables["ELAWIDGETTOOLS_BUILD_STATIC_LIB"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ElaWidgetTools"]
        # Library installed to ElaWidgetTools/lib/, not standard lib/
        self.cpp_info.libdirs = ["ElaWidgetTools/lib"]
        self.cpp_info.includedirs = ["ElaWidgetTools/include"]
