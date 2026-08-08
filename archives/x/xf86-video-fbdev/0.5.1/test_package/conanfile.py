#!/usr/bin/env python3
"""Conan test_package for xf86-video-fbdev — verifies the driver module.

This test verifies the fbdev_drv.so module is a valid ELF shared object
targeting AArch64. Since the driver is an X.Org plugin that expects the
X server to provide symbols at runtime, dlopen is not used (unresolved
symbols are expected for a plugin).

Instead, we use readelf to inspect the .so binary and verify:
1. It is a valid ELF shared object
2. It targets AArch64 (EM_AARCH64 = 183)
3. It exports the FBDEV symbol (XF86ModuleData)
4. It is a shared library (DYN type)
"""
import os
from conan import ConanFile
from conan.tools.files import copy


class Xf86VideoFbdevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy the driver module to the build directory for testing
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "fbdev_drv.so",
             src=os.path.join(self.dependencies["xf86-video-fbdev"].package_folder, "lib"),
             dst=bin_dir)

    def test(self):
        so_path = os.path.join(self.build_folder, "bin", "fbdev_drv.so")

        # Verify the .so file exists
        assert os.path.exists(so_path), f"fbdev_drv.so not found at {so_path}"
        self.output.info(f"Found fbdev_drv.so at {so_path}")

        # Test 1: Verify it's a valid ELF file using readelf
        self.run(f"readelf -h {so_path}", env="conanrun")

        # Test 2: Verify AArch64 architecture (EM_AARCH64 = 183)
        self.run(f"readelf -h {so_path} | grep -q 'AArch64'", env="conanrun")

        # Test 3: Verify it's a shared library (DYN type)
        self.run(f"readelf -h {so_path} | grep -q 'DYN'", env="conanrun")

        # Test 4: Verify FBDEV symbol is exported (XF86ModuleData)
        self.run(f"readelf --dyn-syms {so_path} | grep -q 'FBDEV'", env="conanrun")

        self.output.info("All ELF validation tests passed!")
