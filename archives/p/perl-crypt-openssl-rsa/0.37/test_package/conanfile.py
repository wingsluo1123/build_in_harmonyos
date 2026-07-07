#!/usr/bin/env python3
"""Conan test_package — Crypt::OpenSSL::RSA (Perl XS module).

Verifies that the packaged .so and .pm files are present in the correct
locations, and exercises the core RSA API (generate_key, sign, verify,
encrypt, decrypt) to ensure the package is functional.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanException


class PerlcryptopensslrsaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-crypt-openssl-rsa"]
        pkg_folder = dep.package_folder

        # Check that RSA.so exists in the auto path
        so_files = glob.glob(os.path.join(pkg_folder, "**", "RSA.so"), recursive=True)
        if not so_files:
            raise ConanException("RSA.so not found in package")
        so_path = so_files[0]
        self.output.info(f"Found RSA.so at: {so_path}")

        # Check that RSA.pm exists
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "RSA.pm"), recursive=True)
        if not pm_files:
            raise ConanException("RSA.pm not found in package")
        self.output.info(f"Found RSA.pm at: {pm_files[0]}")

        # Verify the .so is a valid ELF shared object
        self.run(f"file {so_path}")

        # Functional test: exercise core RSA API (R34 — must call actual API)
        # On OHOS, RSA_wrapper.pm delegates to rsa_helper (SELinux workaround).
        # On Linux, the XS .so is loaded directly.
        # Write test script to a temp file to avoid shell quoting issues
        # ($-variables and nested double quotes break perl -e "...").
        import tempfile
        perl_script = (
            "use Crypt::OpenSSL::RSA;\n"
            "my $rsa = Crypt::OpenSSL::RSA->generate_key(1024);\n"
            'my $sig = $rsa->sign("hello world");\n'
            'my $ok = $rsa->verify("hello world", $sig);\n'
            'die "verify failed\n" unless $ok;\n'
            'my $ct = $rsa->encrypt("secret");\n'
            'my $pt = $rsa->decrypt($ct);\n'
            'die "decrypt mismatch: got [$pt]\n" unless $pt eq "secret";\n'
            'print "ALL RSA API TESTS PASSED\n";\n'
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pl", delete=False
        ) as f:
            f.write(perl_script)
            script_path = f.name
        try:
            self.run(f'perl "{script_path}"', env="conanrun")
            self.output.info("RSA API functional test passed")
        except Exception as e:
            self.output.error(f"RSA API functional test failed: {e}")
            raise ConanException(
                f"RSA API functional test failed — module is not usable. Error: {e}"
            )
        finally:
            os.unlink(script_path)
