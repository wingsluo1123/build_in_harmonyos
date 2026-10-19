#!/usr/bin/env python3
"""Conan test_package for futuresql 0.1.1.

Consumer end-to-end check (rule12): links FutureSQL6::FutureSQL from the
packaged library and exercises the public API against an in-memory SQLite
database opened through the packaged QSQLITE driver plugin.

qtbase-sql-dbus sets cmake_find_mode=none and ships Qt's own Qt6Config.cmake,
so the recipe writes conan_cmakedeps_paths.cmake itself and points
CMAKE_PREFIX_PATH at the Qt package (kcodecs/6.26.0 test_package precedent).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class FuturesqlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # FutureSQL6Config.cmake requires Qt6Sql; only qtbase-sql-dbus ships it
        # together with the QSQLITE driver plugin used by the test.
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        tested_name = self.tested_reference_str.split("/")[0]
        pkg = self.dependencies.get(tested_name)
        qt = self.dependencies.get("qtbase-sql-dbus")

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if qt and qt.package_folder:
            qt_pkg = qt.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if pkg and pkg.package_folder:
            pkg_folder = pkg.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_folder}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg_folder}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _test_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
            )
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
            )
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
            )
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def test(self):
        # Skip in cross-builds: an Exec format error would otherwise look like
        # a package defect (same guard as _run_upstream_tests in the recipe).
        if not can_run(self):
            return
        binary = os.path.join(self.cpp.build.bindir, "test_package")
        with self._test_env().vars(self).apply():
            self.run(f'"{binary}"', env="conanrun")
