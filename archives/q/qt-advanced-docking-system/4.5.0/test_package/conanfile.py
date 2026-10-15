#!/usr/bin/env python3
"""Conan test_package for qt-advanced-docking-system 4.5.0.

Consumer-side test (R34): it links the packaged library through the exported
CMake target `ads::qtadvanceddocking-qt6` and exercises the real QtADS API
(dock manager, dock areas, floating dock container, perspectives,
save/restore round trip) — it does not merely print a string.

qtbase is declared with cmake_find_mode="none", so CMakeDeps cannot emit a
usable Qt6 target for the link interface. Like the other Qt6 packages in this
repo, this test_package pins Qt's own cmake package dir on CMAKE_PREFIX_PATH
through generate() and requires qtbase explicitly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QtAdvancedDockingSystemTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicit so the package folder is available in generate() for the
        # Qt6 config bootstrap below.
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Generates qtadvanceddocking-qt6-config.cmake (CMakeDeps) plus the
        # libxcb config; run first so the hand-written paths file below wins.
        #
        # qtbase declares cmake_find_mode="none" (it ships its own
        # Qt6Config.cmake) and sets neither cmake_file_name nor
        # cmake_target_name, so CMakeDeps would name the transitive dependency
        # "qtbase" and reference the non-existent "qtbase::qtbase" target.
        # Map both onto the real Qt6 config/target:
        #   cmake_file_name   -> find_dependency(Qt6)  (satisfiable, and skipped
        #                        entirely when the consumer already did
        #                        find_package(Qt6), since the generated loop is
        #                        guarded by `if(NOT Qt6_FOUND)`)
        #   cmake_target_name -> Qt6::Widgets, which transitively brings in
        #                        Qt6::Gui and Qt6::Core
        # This is the same consumer-side property pattern used by libfm-qt and
        # pcmanfm-qt for qtbase.
        cmake_deps = CMakeDeps(self)
        cmake_deps.set_property("qtbase", "cmake_find_mode", "none")
        cmake_deps.set_property("qtbase", "cmake_file_name", "Qt6")
        cmake_deps.set_property("qtbase", "cmake_target_name", "Qt6::Widgets")
        cmake_deps.generate()

        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        if qtbase is not None:
            qt_pkg = qtbase.package_folder
            lines = [
                'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
                # The toolchain skips its own 'find_paths' block when this
                # file exists, so the generators folder (holding the
                # CMakeDeps config for the tested package and libxcb) must be
                # added here as well.
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            paths_file = os.path.join(self.generators_folder,
                                      "conan_cmakedeps_paths.cmake")
            with open(paths_file, "a") as f:
                f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # The offscreen QPA plugin ships with qtbase; OHOS has no X11/Wayland
        # display, so every GUI object is created headless.
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.append("LD_LIBRARY_PATH",
                   [os.path.join(p.package_folder, "lib")
                    for p in self.dependencies.values() if p.package_folder])
        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0],
                                  "test_qt_advanced_docking_system"),
                     env="conanrun")
