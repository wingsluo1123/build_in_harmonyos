#!/usr/bin/env python3
"""Conan test_package — qt-mariadb 5.15.2.

Verifies the plugin .so file exists and has expected exported symbols.
Cannot fully load the plugin (requires running Qt5 app + ELF signing).
"""
import os

from conan import ConanFile


class QtMariadbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Nothing to compile — the test verifies the pre-built .so
        pass

    def test(self):
        # Find the plugin .so in the package
        pkg = self.dependencies["qt-mariadb"].package_folder
        plugin_dir = os.path.join(pkg, "plugins", "sqldrivers")
        plugin_path = os.path.join(plugin_dir, "libqsqlmysql.so")

        if not os.path.isfile(plugin_path):
            raise Exception(f"Plugin not found: {plugin_path}")
        self.output.info(f"Plugin found: {plugin_path}")

        # Verify the .so links against libmariadb (not libmysqlclient)
        self.run(f"readelf -d {plugin_path} | grep -q libmariadb",
                 env="conanrun")

        # Verify exported symbols (qt_plugin_instance)
        self.run(f"nm -D {plugin_path} | grep -q qt_plugin_instance",
                 env="conanrun")

        self.output.info("All checks passed")
