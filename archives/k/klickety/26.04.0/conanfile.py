#!/usr/bin/env python3
"""Conan recipe for klickety 26.04.0 on HarmonyOS PC (aarch64).

klickety is the KDE SameGame/Clickomania adaptation (a color-matching
puzzle game). It is a Qt6/KF6 QGraphics application built on the
KDEGames6 library (libkdegames 26.04.0, published on the ohpcd registry).

    OHOS-specific adaptations (patches/0001-cmake.patch + 0002-src-cmake.patch):
  - KF6 DocTools removed from OPTIONAL_COMPONENTS and the doc/ handbook
    build + kdoctools_install(po) dropped: kdoctools is not part of the
    published KF6 6.18/6.26 closure; the DocBook handbook is not a
    runtime requirement for the game (kfourinline 26.04.0 precedent).
  - KF6 KIO removed from REQUIRED_COMPONENTS (kio/6.14.0 pulls kconfig/6.14.0
    which conflicts with the KF6 6.18 closure; kio/6.26.0 pulls kconfig/6.26.0
    which conflicts too). KIO functionality is not required by klickety; patch
    also removes KF6::KIOWidgets from the link list in src/CMakeLists.txt.
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
    (OHOS is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation.
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1,
    qtsvg 6.11.1, KF6 6.18.0 framework set + libkdegames 26.04.0.1,
    ecm 6.26.0 (tool_requires).
  - karchive/6.18.0 pinned with override=True (libkdegames 26.04.0 graph
    precedent).
  - ECM_MODULE_PATH set manually + conan_cmakedeps_paths.cmake written
    manually (cmake_find_mode=none packages).
  - -Wl,-z,max-page-size=0x1000 linker pin (OHOS musl loader workaround).
  - Host tools (moc/uic/rcc/kconfig_compiler) are OHOS binaries: build
    env prepends /system/lib64 + SDK llvm/lib + dependency lib dirs.

Upstream registers no test suite (N=0: no tests/, autotests/ or add_test()
in the 26.04.0 tarball). Consumer-side verification is provided by
test_package (klickety --version smoke test).
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KlicketyConan(ConanFile):
    name = "klickety"
    version = "26.04.0"
    description = "KDE SameGame/Clickomania adaptation - color-matching puzzle game"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/games/klickety"
    url = "https://invent.kde.org/games/klickety"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("karchive/6.18.0", override=True)
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        self.requires("kiconthemes/6.18.0")
        # kio: not listed explicitly. kio/6.14.0 drags kconfig/6.14.0
        # which conflicts with the KF6 6.18 closure pinned above;
        # kio/6.26.0 drags kconfig/6.26.0 which conflicts too. KIO
        # functionality is optional in klickety — patch 0001 drops
        # the find_package(KF6 KIO) requirement + the KF6::KIOWidgets
        # link from src/CMakeLists.txt (kfourinline 26.04.0 / audiocd
        # 26.04.3 precedent for the same KF6 closure limitation).
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("libkdegames/26.04.0.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        qt_extra = []
        for dep_name in ("qtsvg",):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                qt_extra
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
                self.runenv_info.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
