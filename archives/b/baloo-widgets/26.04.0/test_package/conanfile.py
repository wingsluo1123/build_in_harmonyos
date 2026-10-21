#!/usr/bin/env python3
"""Conan test_package for baloo-widgets 26.04.0.

Verifies that libKF6BalooWidgets is consumable via CMake
(find_package(KF6 COMPONENTS BalooWidgets)) and that the public widget API is
callable with an offscreen Qt platform (R34: real API usage, no print-only
shell test).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class BalooWidgetsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # The recipe uses cmake_find_mode=none, so the project's own
        # KF6BalooWidgetsConfig.cmake has to be reachable through the prefix
        # path; the same file carries every dependency prefix (qtbase and the
        # KF6 packages also ship cmake_find_mode=none configs).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % dep.package_folder)
                lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder)
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % dep.package_folder)
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH",
                                 os.path.join(dep.package_folder, "lib", "plugins"))
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")

        # kconfig/6.14.0's libKF6ConfigGui.so was built without SONAME, so its
        # DT_NEEDED keeps the build-tree path "../../bin/libKF6ConfigCore.so".
        # dlopen() takes such an entry verbatim relative to the working
        # directory, so mirror the dependency libraries into <runroot>/bin and
        # start the binary two levels below it.
        runroot = os.path.join(self.build_folder, "runroot")
        compat = os.path.join(runroot, "bin")
        workdir = os.path.join(runroot, "work", "sub")
        os.makedirs(compat, exist_ok=True)
        os.makedirs(workdir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder or "", "lib")
            if not dep.package_folder or not os.path.isdir(libdir):
                continue
            for name in sorted(os.listdir(libdir)):
                link = os.path.join(compat, name)
                if ".so" not in name or os.path.lexists(link):
                    continue
                try:
                    os.symlink(os.path.join(libdir, name), link)
                except OSError:
                    pass

        exe = os.path.abspath(os.path.join(self.cpp.build.bindirs[0], "test_baloo_widgets"))
        with env.vars(self).apply():
            self.run(exe, cwd=workdir, env="conanrun")
