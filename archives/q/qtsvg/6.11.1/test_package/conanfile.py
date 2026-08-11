#!/usr/bin/env python3
"""Conan test_package for qtsvg 6.11.1.

Verifies that the Qt6Svg/Qt6SvgWidgets libraries can be found via CMake
and that the QSvgRenderer API is callable (R34: real API usage).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtsvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require qtbase so its package folder is available
        # for path setup in generate().
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # qtbase uses cmake_find_mode=none, so CMakeDeps doesn't add its
        # lib/cmake to CMAKE_PREFIX_PATH. Without this, find_package(Qt6 Svg)
        # can't resolve. Also add the tested package's lib/cmake so its own
        # Qt6SvgConfig.cmake / Qt6SvgWidgetsConfig.cmake are found.
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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Qt6 may require the offscreen platform plugin for headless tests.
        # The test binary needs LD_LIBRARY_PATH pointing at the qtsvg and
        # qtbase package lib dirs to load libQt6Svg/libQt6SvgWidgets.
        #
        # NOTE: this Qt module build produces un-versioned shared libraries
        # (libQt6SvgWidgets.so records a build-tree-relative DT_NEEDED of
        # "../../lib/libQt6Svg.so"). The dynamic loader resolves that
        # relative path from the process CWD (the test build dir), so we
        # mirror the expected layout under test_package/lib to make the
        # relative NEEDED resolvable.
        tp_lib = os.path.join(self.build_folder, "..", "..", "lib")
        qtsvg_pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        if qtsvg_pkg and qtsvg_pkg.package_folder:
            src_lib = os.path.join(qtsvg_pkg.package_folder, "lib")
            os.makedirs(tp_lib, exist_ok=True)
            for name in os.listdir(src_lib):
                if name.startswith("libQt6Svg") and name.endswith(".so"):
                    link = os.path.join(tp_lib, name)
                    if not os.path.lexists(link):
                        os.symlink(os.path.join(src_lib, name), link)

        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            # Run the test binary directly (R34: test must exercise the package)
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_qtsvg"),
                env="conanrun",
            )
