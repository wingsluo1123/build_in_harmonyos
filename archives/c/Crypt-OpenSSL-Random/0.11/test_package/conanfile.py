#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::Random Perl XS module.

Verifies that the package contains the expected artifacts and
calls the module's API (R34: test must invoke the tested package's API).
"""
import os

from conan import ConanFile


class CryptOpenSSLRandomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["crypt-openssl-random"]
        pkg_folder = dep.package_folder

        self.output.info(f"Package folder: {pkg_folder}")

        # Paths to verify
        so_path = os.path.join(pkg_folder, "lib", "auto", "Crypt", "OpenSSL", "Random", "Random.so")
        pm_path = os.path.join(pkg_folder, "lib", "Crypt", "OpenSSL", "Random.pm")

        # Verify artifacts exist
        assert os.path.isfile(so_path), f"Random.so not found at {so_path}"
        assert os.path.isfile(pm_path), f"Random.pm not found at {pm_path}"
        self.output.info(f"Found: {so_path}")
        self.output.info(f"Found: {pm_path}")

        # Verify .so is valid ELF
        with open(so_path, "rb") as f:
            magic = f.read(4)
            assert magic == b"\x7fELF", f"Random.so is not valid ELF (magic: {magic})"

        # Verify .pm has version
        with open(pm_path, "r") as f:
            content = f.read()
            assert "0.11" in content, "Random.pm does not contain version 0.11"
            assert "Crypt::OpenSSL::Random" in content, "Random.pm missing package name"

        # R34: Call the package's API via Perl
        # Set PERL5LIB to include the package's lib/ directory
        pkg_lib = os.path.join(pkg_folder, "lib")
        old_perl5lib = os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = f"{pkg_lib}:{old_perl5lib}" if old_perl5lib else pkg_lib
        try:
            # Call random_bytes() and random_status() — actual API invocation
            self.run(
                'perl -MCrypt::OpenSSL::Random=random_bytes,random_status '
                '-e \'my $bytes = random_bytes(10); '
                'die "random_bytes returned empty" unless $bytes && length($bytes) == 10; '
                'die "random_status failed" unless random_status(); '
                'print "API test passed: random_bytes(10) and random_status() OK\\n"\''
            )
        finally:
            os.environ["PERL5LIB"] = old_perl5lib
