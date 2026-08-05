#!/usr/bin/env python3
"""Conan test_package — abiword-plugin-docbook 3.0.8

L1 test: verify the plugin .so is a valid ELF with expected exported symbols.
"""
import os
import ctypes
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


class AbiwordPluginDocbookTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["abiword-plugin-docbook"].package_folder
        plugin_dir = os.path.join(pkg_folder, "lib", "abiword", "plugins")

        # Find the docbook plugin .so
        if os.path.isdir(plugin_dir):
            plugins = os.listdir(plugin_dir)
            eml_so = [p for p in plugins if "docbook" in p.lower() and p.endswith(".so")]
        else:
            eml_so = []

        if not eml_so:
            # Fallback: search for docbook.so anywhere in the package
            import glob
            eml_so = [os.path.basename(p) for p in glob.glob(
                os.path.join(pkg_folder, "**", "*docbook*.so*"), recursive=True
            )]

        if not eml_so:
            # Try listing the package contents for debugging
            self.output.info("Package contents:")
            for root, dirs, files in os.walk(pkg_folder):
                for f in files:
                    self.output.info(f"  {os.path.join(root, f)}")
            raise AssertionError("DocBook plugin .so not found in package")

        so_path = os.path.join(plugin_dir if os.path.isdir(plugin_dir) else pkg_folder, eml_so[0])
        self.output.info(f"DocBook plugin found: {so_path}")

        # Method 1: Use readelf to verify it's a valid ELF with exported symbols
        self.output.info("Verifying ELF validity and exported symbols via readelf...")
        try:
            result = subprocess.run(
                ["readelf", "-s", so_path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                # Check for expected plugin symbols
                for sym in ["abi_plugin_register", "abi_plugin_unregister",
                           "abi_plugin_supports_version"]:
                    if sym in result.stdout:
                        self.output.info(f"  [ok] Exported symbol found: {sym}")
                    else:
                        self.output.warning(f"  [warn] Expected symbol not found in readelf: {sym} (ctypes check will follow)")
                # Count total exported symbols
                sym_count = len([l for l in result.stdout.splitlines()
                                 if "FUNC" in l and "GLOBAL" in l])
                self.output.info(f"  Total exported FUNC symbols: {sym_count}")
            else:
                self.output.warning(f"readelf failed (rc={result.returncode}): {result.stderr} (ctypes check will follow)")
        except FileNotFoundError:
            self.output.info("readelf not available, skipping ELF verification")

        # Method 2: Use ctypes to attempt loading the .so
        self.output.info("Attempting to load .so with ctypes.CDLL...")
        try:
            lib = ctypes.CDLL(so_path)
            self.output.info("  [ok] .so loaded successfully via ctypes.CDLL")

            # Verify ABI version support symbol — must exist and return 1
            if not hasattr(lib, "abi_plugin_supports_version"):
                raise AssertionError("abi_plugin_supports_version symbol not found in .so")
            lib.abi_plugin_supports_version.argtypes = [ctypes.c_uint32] * 3
            lib.abi_plugin_supports_version.restype = ctypes.c_int
            result = lib.abi_plugin_supports_version(3, 0, 0)
            self.output.info(f"  [ok] abi_plugin_supports_version(3,0,0) returned {result}")
            if result != 1:
                raise AssertionError(f"abi_plugin_supports_version(3,0,0) returned {result}, expected 1")

            # Verify registration symbol exists
            if not hasattr(lib, "abi_plugin_register"):
                raise AssertionError("abi_plugin_register symbol not found in .so")
            self.output.info("  [ok] abi_plugin_register symbol is available")

            # Verify unregister symbol exists
            if not hasattr(lib, "abi_plugin_unregister"):
                raise AssertionError("abi_plugin_unregister symbol not found in .so")
            self.output.info("  [ok] abi_plugin_unregister symbol is available")

        except OSError as e:
            raise AssertionError(f"Failed to load .so via ctypes.CDLL: {e}")
