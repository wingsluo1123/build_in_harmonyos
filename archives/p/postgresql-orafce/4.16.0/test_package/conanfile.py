#!/usr/bin/env python3
"""Test package for postgresql-orafce 4.16.0

Verifies that the orafce extension shared library is a valid ELF
and can be loaded. Also checks that the .control and
SQL definition files are present in the package.
"""
import os
import ctypes
import struct

from conan import ConanFile


class PostgresqlOrafceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed for this test

    def test(self):
        dep = self.dependencies["postgresql-orafce"]
        pkg_folder = dep.package_folder

        # 1. Check orafce.so exists and is a valid ELF
        so_path = os.path.join(pkg_folder, "lib", "postgresql", "orafce.so")
        assert os.path.isfile(so_path), f"orafce.so not found at {so_path}"

        # Verify it's an ELF file by checking magic bytes
        with open(so_path, "rb") as f:
            magic = f.read(4)
            assert magic == b'\x7fELF', f"orafce.so is not an ELF file (magic: {magic})"
            self.output.info("orafce.so verified as ELF shared object")

        # 2. Check ELF class (64-bit for aarch64)
        with open(so_path, "rb") as f:
            f.seek(4)
            ei_class = struct.unpack("B", f.read(1))[0]
            assert ei_class == 2, f"Expected 64-bit ELF (class=2), got class={ei_class}"
            self.output.info(f"ELF class: {'64-bit' if ei_class == 2 else '32-bit'}")

        # 3. Try dlopen to verify it's loadable
        try:
            lib = ctypes.CDLL(so_path)
            self.output.info("dlopen(orafce.so) succeeded")
            if hasattr(lib, "_PG_init"):
                self.output.info("_PG_init symbol found - valid PostgreSQL extension")
            del lib
        except OSError as e:
            self.output.info(f"dlopen failed (expected on non-PostgreSQL systems): {e}")

        # 4. Check orafce.control exists
        control_path = os.path.join(pkg_folder, "share", "postgresql", "extension", "orafce.control")
        assert os.path.isfile(control_path), f"orafce.control not found at {control_path}"
        with open(control_path) as f:
            content = f.read()
            assert "orafce" in content, "orafce.control does not mention 'orafce'"
        self.output.info(f"orafce.control verified: {content[:100]}")

        # 5. Check SQL definition files exist
        ext_dir = os.path.join(pkg_folder, "share", "postgresql", "extension")
        sql_main = os.path.join(ext_dir, "orafce--4.16.sql")
        assert os.path.isfile(sql_main), f"orafce--4.16.sql not found at {sql_main}"
        self.output.info("orafce--4.16.sql verified")

        # Count SQL files
        sql_files = [f for f in os.listdir(ext_dir) if f.endswith(".sql")]
        self.output.info(f"Found {len(sql_files)} SQL files in extension directory")
        assert len(sql_files) > 0, "No SQL files found in extension directory"

        # 6. Verify .so file is readable and has expected size (>100KB for a full extension)
        so_size = os.path.getsize(so_path)
        self.output.info(f"orafce.so size: {so_size} bytes")
        assert so_size > 100000, f"orafce.so too small ({so_size} bytes), expected >100KB"

        # 7. Use self.run() to verify the shared library file is readable
        self.run(f'test -r "{so_path}"')

        self.output.info("All tests passed!")
