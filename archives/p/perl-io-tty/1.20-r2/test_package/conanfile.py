#!/usr/bin/env python3
"""Test package for perl-io-tty — verifies the Perl XS module builds correctly.

Tests:
  1. Verify Tty.so exists and is a valid ELF shared object
  2. Verify pure Perl modules exist (IO/Tty.pm, IO/Pty.pm, IO/Tty/Constant.pm)
  3. Load IO::Tty::Constant and check terminal constants (R34: calls package API)
"""
import os

from conan import ConanFile


class PerlIoTtyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-io-tty"]
        pkg_lib = os.path.join(pkg.package_folder, "lib")

        # 1. Verify Tty.so exists and is a valid ELF
        so_path = os.path.join(pkg_lib, "auto/IO/Tty/Tty.so")
        assert os.path.exists(so_path), f"Tty.so not found at {so_path}"
        self.run(f"file {so_path}")
        self.run(f"readelf -h {so_path} | grep 'Type:.*DYN'")

        # 2. Verify pure Perl modules exist
        for mod in ["IO/Tty.pm", "IO/Pty.pm", "IO/Tty/Constant.pm"]:
            mod_path = os.path.join(pkg_lib, mod)
            assert os.path.exists(mod_path), f"{mod} not found at {mod_path}"

        # 3. Load IO::Tty::Constant and check constants (R34: calls package API)
        perl = "/data/service/hnp/bin/perl"
        test_script = os.path.join(self.source_folder, "test.pl")
        self.run(f"PERL5LIB={pkg_lib} {perl} {test_script}")
