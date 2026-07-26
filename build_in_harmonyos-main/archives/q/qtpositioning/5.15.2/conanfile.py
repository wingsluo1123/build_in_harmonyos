#!/usr/bin/env python3
"""Conan recipe for QtPositioning 5.15.2 — Qt5 Positioning module (qmake).

Build system: qmake (Qt5 addon module)
Platform: aarch64-linux-ohos (HarmonyOS PC)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
import os


class QtpositioningConan(ConanFile):
    name = "qtpositioning"
    version = "5.15.2"
    description = "Qt5 Positioning module - provides position data access via QML and C++ API"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/qt/qtlocation"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt/5.15.13")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: OHOS platform support — pass mkspec via env for cross-compilation
        if self.settings.os == "OHOS":
            # qmake reads QMAKESPEC to determine target platform
            # The ohos-aarch64 mkspec is provided by the Qt5 package
            qt_root = self.dependencies["qt"].package_folder
            qt_mkspecs = os.path.join(qt_root, "mkspecs")
            if os.path.isdir(os.path.join(qt_mkspecs, "ohos-aarch64-clang")):
                self.run_env.define("QMAKESPEC", os.path.join(qt_mkspecs, "ohos-aarch64-clang"))
            else:
                # Fallback: use default mkspecs path from Qt installation
                self.run_env.define("QMAKESPEC", qt_mkspecs)

    def build(self):
        apply_conandata_patches(self)
        # Qt5 addon module build: qmake → make
        # Note: positioning.pro is in src/positioning/ under source_folder
        qt_root = self.dependencies["qt"].package_folder
        qmake_bin = os.path.join(qt_root, "bin", "qmake")
        pro_file = os.path.join(self.source_folder, "src", "positioning", "positioning.pro")
        self.run(f"{qmake_bin} {pro_file}")
        self.run("make -j1")

    def package(self):
        self.run("make install INSTALL_ROOT={}".format(self.package_folder))
        # Also copy any .prl, .la, .pc files
        for pattern in ["*.prl", "*.la", "*.pc"]:
            copy(self, pattern, src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["Qt5Positioning"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_target_name", "Qt5::Positioning")
        self.cpp_info.set_property("pkg_config_name", "Qt5Positioning")
