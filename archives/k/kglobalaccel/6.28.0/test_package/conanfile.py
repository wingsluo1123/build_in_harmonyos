#!/usr/bin/env python3
"""Conan test_package for kglobalaccel 6.28.0.

Verifies that the KF6GlobalAccel CMake package can be found and that the
public KGlobalAccel API is callable end-to-end through real consumer flows
(R34: real API usage; the executor in test.cpp runs 3 cases and prints
TEST SUMMARY).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KglobalaccelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6 base modules (Core/Gui/Widgets/DBus) come from qtbase-sql-dbus,
        # the only OHOS provider of Qt6::DBus.
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        # Make sure the Qt6 base config resolves against qtbase-sql-dbus.
        sqldbus = self.dependencies.get("qtbase-sql-dbus")
        if sqldbus:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{sqldbus.package_folder}/lib/cmake")'
            )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via LD_LIBRARY_PATH.
        # Prepend it so CMake's TryCompile can link. Must not clobber conanbuild
        # env on other hosts.
        env = Environment()
        for llvm_lib in sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
        )):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if cross_building(self):
            # The OHOS consumer cannot execute on a cross-building host: the
            # platform CI only proves that it links; the native device run is
            # what exercises the packaged API.
            self.output.info(
                "Cross build: consumer linked only; native device run still required"
            )
            return
        # E298: do not delegate to CTest via cmake.test() — the child process
        # would miss the runtime search path. Run the consumer directly with
        # the dependency lib/plugin directories injected (Environment.append
        # separates with a blank space by default, so use prepend_path here).
        env = Environment()
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
            )
            env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
            )
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
            )
        env.define("QT_QPA_PLATFORM", "offscreen")
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH can shadow the compatible
            # libc++_shared.so; /system/lib64 must win (kconfig/kcrash
            # 6.26.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_kglobalaccel"))
