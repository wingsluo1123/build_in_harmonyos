#!/usr/bin/env python3
"""Conan test_package — PreviSat 7.2.1.3 (L1 test).

PreviSat is a Qt6 GUI application (no consumable library API), so the L1 test
executes the installed binary and inspects its runtime behaviour (R34) instead
of calling a library API. The application is run with the Qt "offscreen"
platform plugin, which the packaged Qt6 provides, because the HarmonyOS PC
images have no windowing system.

Verified observables:
  1. the installed tree (binary, data/, translations/) is complete;
  2. the installed binary is an executable, signed ELF (HarmonyOS executes
     signed binaries only);
  3. the application starts headless and keeps running (all shared libraries,
     including the Qt6 Sql and Multimedia modules, resolve);
  4. the relocatable (PORTABLE_BUILD) data layout works: the application
     materialises its runtime tree (data/config, log/, cache/, Astropedia/)
     next to the executable and logs the progressive loading of its data files
     — i.e. it does not fall back to /usr/share/Astropedia;
  5. the Qt SQLite driver of the packaged Qt6 Sql module is usable: the
     application opens its satellite database without a "driver not loaded"
     failure.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PrevisatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("skipped (cannot run on this platform)")
            return
        # Qt loads its plugins (platform, sqldrivers, multimedia) from the
        # dependency packages, which the run environment does not point at.
        plugin_paths = []
        library_paths = []
        for dependency in self.dependencies.host.values():
            plugins = os.path.join(dependency.package_folder, "plugins")
            if os.path.isdir(plugins):
                plugin_paths.append(plugins)
            lib_dir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(lib_dir):
                library_paths.append(lib_dir)
        if plugin_paths:
            os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(plugin_paths)
        # Keep the dependency libraries reachable for the child process even
        # when the conanrun script is not sourced by the test script.
        if library_paths:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                library_paths + ([existing] if existing else [])
            )

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["PREVISAT_PKG"] = self.dependencies[
            self.tested_reference_str
        ].package_folder
        self.run(
            f"{bash} {os.path.join(self.recipe_folder, 'test.sh')}",
            env="conanrun",
            cwd=self.recipe_folder,
        )
