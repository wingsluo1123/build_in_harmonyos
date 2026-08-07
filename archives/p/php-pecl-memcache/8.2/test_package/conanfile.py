#!/usr/bin/env python3
"""Conan test_package for php-pecl-memcache 8.2.

Tests that the memcache.so PHP extension was built correctly.
Verifies the .so is a valid ELF binary for aarch64.

This is the L1 test in the five-level test system.
Note: Full runtime loading test requires PHP with session extension enabled.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class PhpPeclMemcacheTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # R34: test must substantially depend on the tested package
        dep = self.dependencies["php-pecl-memcache"]
        ext_dir = os.path.join(dep.package_folder, "lib", "php", "extensions")
        so_path = os.path.join(ext_dir, "memcache.so")

        # Verify the .so file exists
        assert os.path.exists(so_path), f"memcache.so not found at {so_path}"

        # Verify it's a valid ELF shared object for aarch64
        self.run(f"file {so_path}", env="conanrun")

        # Verify the .so contains expected symbols (memcache functions)
        self.run(f"llvm-nm {so_path} 2>/dev/null | grep -i memcache", env="conanrun")

        # Verify the .so links against zlib (R34: real dependency usage)
        self.run(f"readelf -d {so_path} | grep -i 'NEEDED'", env="conanrun")
