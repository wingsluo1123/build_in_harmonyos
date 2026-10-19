#!/usr/bin/env python3
"""Conan test_package for threadweaver 6.28.0.

Verifies that KF6ThreadWeaver can be found via CMake and that the packaged
API works end-to-end through real consumer flows (R34: real API usage; the
executor in test.cpp runs 3 cases and prints TEST SUMMARY).
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class ThreadweaverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the SDK's
        # llvm/lib directory; CI workers may not export it via LD_LIBRARY_PATH
        # (observed on OpenHarmonyPCDeveloper-CI-021). Prepend it so CMake's
        # TryCompile can link. Must not clobber conanbuild env on other hosts.
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        env = Environment()
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
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
        # would miss the runtime search path (observed elsewhere as "Error
        # loading shared library libKF6ThreadWeaver.so"). Run the consumer
        # directly with the dependency lib/plugin directories injected
        # (Environment.append separates with a blank space by default, so use
        # prepend_path here).
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
        # threadweaver is a QtCore-level framework: the consumer runs on
        # QCoreApplication with no QPA platform plugin involved.
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_threadweaver"))
