#!/usr/bin/env python3
"""Conan recipe for QtPositioning 5.15.2 — Qt5 Positioning module (qmake).

Build system: qmake (Qt5 addon module)
Platform: aarch64-linux-ohos (HarmonyOS PC)
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv
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
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Always create VirtualBuildEnv for env="conanbuild" support in build()
        build_env = VirtualBuildEnv(self)
        # R32: OHOS platform support — pass mkspec via env for cross-compilation
        if self.settings.os == "OHOS":
            # qmake reads QMAKESPEC to determine target platform for OHOS cross-compilation
            qt_root = self.dependencies["qt5-qtbase"].package_folder
            qt_mkspecs = os.path.join(qt_root, "mkspecs")
            ohos_mkspec = os.path.join(qt_mkspecs, "harmonyos-clang")
            if os.path.isdir(ohos_mkspec):
                # Set QMAKESPEC via buildenv_info() for the build context
                # (build_env.environment().define() does not persist to generated files)
                self.buildenv_info.define("QMAKESPEC", ohos_mkspec)
            else:
                raise ConanInvalidConfiguration(
                    f"OHOS mkspec (harmonyos-clang) not found in qt5-qtbase package. "
                    "qmake would use default mkspec and produce host-arch binary. "
                    "The qt5-qtbase/5.15.2 must include harmonyos-clang mkspec for OHOS cross-compilation."
                )
        # Generate the conanbuild environment file for all platforms
        build_env.generate()

    def build(self):
        apply_conandata_patches(self)
        # Qt5 addon module build: qmake → make
        # Note: positioning.pro is in src/positioning/ under source_folder
        qt_root = self.dependencies["qt5-qtbase"].package_folder
        qmake_bin = os.path.join(qt_root, "bin", "qmake")
        pro_file = os.path.join(self.source_folder, "src", "positioning", "positioning.pro")
        # Pass shared/static config to qmake based on Conan options
        config_flag = ""
        if not self.options.shared:
            config_flag = "CONFIG+=static"
        self.run(f"{qmake_bin} {pro_file} {config_flag}", env="conanbuild")
        self.run("make -j1", env="conanbuild")

    def package(self):
        self.run(f"make install INSTALL_ROOT=\"{self.package_folder}\"")

    def package_info(self):
        self.cpp_info.libs = ["Qt5Positioning"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.requires = ["qt5-qtbase::qt5-qtbase"]
        self.cpp_info.set_property("cmake_target_name", "Qt5::Positioning")
        self.cpp_info.set_property("pkg_config_name", "Qt5Positioning")
