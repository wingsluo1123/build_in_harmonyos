#!/usr/bin/env python3
"""Conan recipe for killbots 26.04.0 on HarmonyOS PC (aarch64).

killbots is a KDE Gear game (a port of the classic BSD console game
robots). It is a Qt6/KF6 QGraphics application built on the KDEGames6
library (libkdegames 26.04.0, published on the ohpcd registry).

OHOS-specific adaptations (applied in build()):
  - KF6 DocTools removed from OPTIONAL_COMPONENTS and the doc/ handbook
    build + kdoctools_install(po) dropped: kdoctools is not part of the
    published KF6 6.18/6.26 closure; the DocBook handbook is not a
    runtime requirement for the game (klickety 26.04.0 precedent).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection
    (OHOS is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation.
  -     Dependencies resolved from the ohpcd registry: qtbase 6.11.1,
    qtsvg 6.11.1, KF6 6.18.0 framework set + libkdegames 26.04.0,
    ecm 6.26.0 (tool_requires, KDE 6.18 baseline).
  - karchive/6.18.0 pinned with override=True (klickety 26.04.0 precedent).
  - ECM_MODULE_PATH set manually + conan_cmakedeps_paths.cmake written
    manually (cmake_find_mode=none packages).
  - -Wl,-z,max-page-size=0x1000 linker pin (OHOS musl loader workaround).
  - Host tools (moc/uic/rcc/kconfig_compiler) are OHOS binaries: build
    env prepends /system/lib64 + SDK llvm/lib + dependency lib dirs.
  - Qt6::Xml added (needed by killbots src/CMakeLists.txt, klickety
    precedent does not need it).

Upstream test suite: enginetest (Qt Test framework, 4 test functions:
testValidCells, testRandomEmptyCell, testMoveIsValid, testMoveIsSafe).
Consumer-side verification provided by test_package.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KillbotsConan(ConanFile):
    name = "killbots"
    version = "26.04.0"
    description = "KDE killbots game - evade killer robots (Qt6/KF6)"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/games/killbots"
    url = "https://invent.kde.org/games/killbots"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtsvg/6.11.1")
        # karchive/6.18.0 override: kiconthemes + kpackage pre-built binaries
        # on ohpcd depend on karchive/6.18.0 (klickety 26.04.0 precedent).
        # zlib is pulled transitively by karchive/6.18.0 (no explicit dep).
        self.requires("karchive/6.18.0", override=True)
        self.requires("kconfig/6.18.0")
        self.requires("kconfigwidgets/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("kdbusaddons/6.18.0")
        self.requires("ki18n/6.18.0")
        # kiconthemes/6.18.0.1 (not 6.18.0): published on ohpcd with matching
        # settings (clang 15 libc++ 17) so conan create consumes the remote
        # binary directly — avoids local rebuild + ctest (kpixmapsequenceloadertest
        # needs shared-mime-info, unavailable on OHOS).
        # override=True: kxmlgui/6.18.0 依赖 kiconthemes/6.18.Z，Conan 默认解析为
        # 6.18.0（最低匹配版本），用 override 强制升级到 6.18.0.1。
        self.requires("kiconthemes/6.18.0.1", override=True)
        self.requires("kwidgetsaddons/6.18.0")
        self.requires("kxmlgui/6.18.0")
        self.requires("libkdegames/26.04.0")

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
        # OHOS 无 kdoctools，从 CMakeLists.txt 移除 DocTools 依赖和 doc/ 子目录
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_lists) as f:
            content = f.read()
        content = content.replace("    DocTools\n", "")
        content = content.replace("add_subdirectory(doc)\n", "")
        content = content.replace("kdoctools_install(po)\n", "")
        with open(cmake_lists, "w") as f:
            f.write(content)
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
