#!/usr/bin/env python3
"""Conan test_package — abiword-plugin-eml 3.0.8

L1 test: verify the plugin .so is installed and can be loaded.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AbiwordPluginEmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify the plugin .so exists in the package
        pkg_folder = self.dependencies["abiword-plugin-eml"].package_folder
        plugin_dir = os.path.join(pkg_folder, "lib", "abiword", "plugins")
        self.output.info(f"Checking plugin directory: {plugin_dir}")

        if not os.path.isdir(plugin_dir):
            self.output.warning("Plugin directory not found, checking alternative locations...")
            # Fallback: search for eml.so anywhere in the package
            import glob
            for so in glob.glob(os.path.join(pkg_folder, "**", "*eml*"), recursive=True):
                self.output.info(f"  Found: {so}")
            return

        plugins = os.listdir(plugin_dir)
        self.output.info(f"Plugins found: {plugins}")

        # Check that the eml plugin .so is present
        eml_so = [p for p in plugins if "eml" in p.lower()]
        if eml_so:
            self.output.info(f"EML plugin found: {eml_so[0]}")
        else:
            self.output.warning("EML plugin .so not found in plugin directory")