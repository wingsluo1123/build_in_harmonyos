#!/usr/bin/env python3
"""Conan test_package for qcustomplot 2.1.1.

Consumes the packaged deliverable exactly as an OHOS Qt application would:
find_package(QCustomPlot) locates the packaged CMake config, the executable
links the installed libQCustomPlot.so and drives the public plotting API end
to end (graphs, axes, tickers, legend, items, colour map, raster export,
PDF capability). Qt runs with the offscreen platform plugin because the
device session has no compositor.

Every case is reported independently as TEST PASS / TEST FAIL, the run ends
with "E2E TEST SUMMARY: N passed, M failed", and a non-zero exit status is
returned if any case failed.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QcustomplotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tested = self.dependencies["qcustomplot"]
        tc.variables["QCP_PACKAGE_DIR"] = os.fspath(
            tested.package_folder).replace("\\", "/")
        self._write_cmake_paths()
        tc.generate()

    def _write_cmake_paths(self):
        """Make the real Qt6Config and the qcustomplot CMake package visible.

        Both qtbase and qcustomplot use cmake_find_mode=none, so CMakeDeps
        emits no config for either; the installed QCustomPlotConfig.cmake and
        Qt's own Qt6Config.cmake are located through CMAKE_PREFIX_PATH.
        """
        prefixes = []
        libraries = []
        includes = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized and normalized not in collection:
                collection.append(normalized)

        tested = self.dependencies["qcustomplot"]
        if tested.package_folder:
            add_unique(prefixes, os.path.join(tested.package_folder, "lib", "cmake"))
            add_unique(prefixes, tested.package_folder)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
            add_unique(prefixes, dep.package_folder)
            add_unique(libraries, os.path.join(dep.package_folder, "lib"))
            add_unique(includes, os.path.join(dep.package_folder, "include"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        qt = self.dependencies.get("qtbase")
        if qt and qt.package_folder:
            qt_pkg = qt.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')

        os.makedirs(self.generators_folder, exist_ok=True)
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def _runtime_env(self):
        env = Environment()
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # The sandbox LD_LIBRARY_PATH may carry a libc++_shared.so that is
            # incompatible with the SDK one; /system/lib64 goes ahead of it.
            # Prepended before the dependency loop on purpose: each prepend
            # puts the entry at the front, so the package lib dirs below still
            # win over /system/lib64 when the same library name exists in both.
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
            env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
            env.prepend_path(
                "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        env = self._runtime_env()
        # GUI toolkits refuse to start without writable XDG locations; the
        # build folder is writable on the device (the user volume /tmp is not).
        home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            # L0d (CI): test() must execute a process through self.run(); run
            # the same consumer executable directly under the same env so the
            # per-case output is part of the test_package log.
            candidates = glob.glob(
                os.path.join(self.build_folder, "**", "test_qcustomplot_e2e"),
                recursive=True,
            )
            if not candidates:
                raise ConanException(
                    "test_qcustomplot_e2e executable not found under %s"
                    % self.build_folder
                )
            self.run('"%s"' % candidates[0])
