#!/usr/bin/env python3
"""Conan test_package for plasma-activities 6.7.2.

Builds a real consumer executable against the installed PlasmaActivities
CMake package and runs it. The executable is a case runner: each case prints
TEST PASS/TEST FAIL, the run ends with TEST SUMMARY, and any failure makes
the process exit non-zero. The cases drive the offline consumer contract
that Plasma applications see on a system without kactivitymanagerd:
Consumer service status/defaults, Controller futures and Info availability.
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class PlasmaActivitiesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6 Core/DBus/Gui/Widgets provider (the superset Qt build; the
        # plain qtbase package has no DBus/Sql modules).
        self.requires("qtbase-sql-dbus/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qt = self.dependencies.get("qtbase-sql-dbus")
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        # Qt first: PlasmaActivitiesConfig.cmake runs find_dependency(Qt6Core).
        if qt:
            qt_pkg = qt.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
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

    def _sdk_llvm_libdir(self):
        """OHOS SDK llvm/lib that carries the active lld runtime deps (E132).

        Derived from the toolchain declared in the profile
        (tools.build:compiler_executables) so a worker with a different SDK
        version keeps working; falls back to the SDK install root instead of
        pinning one version.
        """
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx:
            compiler = os.path.realpath(cxx)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            )
        )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        # Cross profile (host != build): the consumer binary cannot execute
        # on the build machine; skip instead of failing with Exec format
        # error (p11-kit 0.26.2 / pachi 12.9 precedent, and the same guard
        # the recipe's _run_upstream_tests() applies).
        if not can_run(self):
            self.output.info("Cross build: skipping the consumer tests")
            return
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        # The consumer runner is a QCoreApplication; offscreen keeps Qt from
        # looking for a display on workers that ship a GUI platform plugin.
        env.define("QT_QPA_PLATFORM", "offscreen")
        # Pin the offline contract: without a reachable session bus the
        # Consumer/Controller/Info APIs must degrade to their documented
        # NotRunning behaviour regardless of what the CI worker exports.
        env.define("DBUS_SESSION_BUS_ADDRESS", "disabled:")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "consumer_e2e"),
                env="conanrun",
            )
