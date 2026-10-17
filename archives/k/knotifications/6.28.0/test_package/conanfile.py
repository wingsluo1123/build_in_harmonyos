#!/usr/bin/env python3
"""Conan test_package for knotifications 6.28.0.

Verifies that KF6Notifications resolves through CMake on a fresh consumer
and that the public API (KNotification event/title/text/icon/flags/urgency/
hints/urls/actions surface) works against the packaged binary (R34: real
API usage), plus the SONAME/DT_NEEDED regression check on the produced
shared library (test_knotifications_ohos).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KnotificationsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Mirror the recipe pins so the graph resolves to the same
        # binaries and the Qt6/KF6 configs are resolvable. kconfig is
        # needed at runtime (libKF6Notifications.so DT_NEEDED links
        # KF6ConfigCore).
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # KF6Notifications ships its own config (cmake_find_mode=none) and
        # its find_dependency(Qt6Gui) chain plus the KF6 component configs
        # must be resolvable, so put every dependency's cmake dirs on the
        # search path (kcalendarcore 6.26.0 test_package precedent).
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
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
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH, which makes CMake's TryCompile fail. Prepend
        # every SDK revision present (same glob as the main recipe) so the
        # probe links on any worker (kcontacts 6.28.0 precedent).
        env = Environment()
        for sdk_llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        env = Environment()
        # The loader must find libKF6Notifications.so and its DT_NEEDED
        # set (bare basenames, kconfig 6.26.0.1 / qtbase) through
        # LD_LIBRARY_PATH: the dependency lib dirs are the candidate list
        # the test executables and test_knotifications_ohos resolve
        # against.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_knotifications")
        ohos_test_exe = os.path.join(self.cpp.build.bindirs[0],
                                     "test_knotifications_ohos")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )
            self.run(test_exe, cwd=self.cpp.build.bindirs[0])
            self.run(ohos_test_exe, cwd=self.cpp.build.bindirs[0])
