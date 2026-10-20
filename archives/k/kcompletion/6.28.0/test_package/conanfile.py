#!/usr/bin/env python3
"""Conan test_package for kcompletion 6.28.0.

Verifies that KF6Completion can be found via CMake and that real APIs are
callable end to end (R34): the completion engine matches and cycles items,
sorted/case-insensitive and weighted modes behave as documented, KLineEdit
and KComboBox perform inline completion offscreen, and KEmailValidator
reports the documented validation states.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KcompletionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kcodecs/6.26.0.1")
        self.requires("kconfig/6.26.0.1")
        self.requires("kwidgetsaddons/6.28.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        for dep_name in ("kcodecs", "kconfig", "kwidgetsaddons"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # The host cmake (/data/service/hnp/bin/cmake) runs during configure;
        # the OHOS sandbox LD_LIBRARY_PATH contains an incompatible
        # libc++_shared.so which shadows the compatible one, so prepend
        # /system/lib64 (ksanecore 26.04.0 / kconfig 6.26.0 precedent).
        env = Environment()
        if self.settings.os == "OHOS":
            # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
            # llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH (observed on OpenHarmonyPCDeveloper-CI-021).
            # Prepend every SDK llvm/lib in sorted order, matching the main
            # recipe's _cmake_build_env(), so the consumer's TryCompile links
            # against the same SDK set as the package build.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The OHOS sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one, so prepend
            # /system/lib64 (same order as the main recipe: after the SDK
            # dirs, so it ends up first).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # Mirror the main recipe's _library_runtime_env(): every dependency
        # contributes its lib dir plus the three Qt plugin import paths. The
        # consumer binary builds a QApplication, so QT_QPA_PLATFORM_PLUGIN_PATH
        # must point at qtbase's plugins/platforms even when qtbase's compiled-in
        # prefix does not resolve (relocated or GC'd cache), and QML2_IMPORT_PATH
        # covers the QML dirs of any KF6 dep that ships one.
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
                env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        if self.settings.os == "OHOS":
            # Same runtime prepends as build() and the main recipe, so the
            # consumer binary resolves the compatible libc++ and the SDK's
            # libxml2.so.16 on every OHOS host.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        with env.vars(self).apply():
            # Single execution path: the binary prints one PASS/FAIL line per
            # check and a TEST SUMMARY, and exits non-zero on failure. The
            # ctest entry in test_package/CMakeLists.txt is not run a second
            # time (previously cmake.test() ran it again under a different
            # environment). No env="conanrun": this package only generates
            # CMakeDeps, so there is no VirtualRunEnv launcher to apply; the
            # environment above is the complete runtime setup.
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kcompletion"),
            )
