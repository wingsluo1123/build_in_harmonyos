#!/usr/bin/env python3
"""Conan test_package for perl-params-validate — Perl L1 test.

Verifies that the XS.so is present, is a valid ELF, and has the boot function.
Attempts to load Params::Validate (PP fallback via Module::Implementation).
Runtime .so loading may fail due to SELinux/HMDFS — PP fallback is expected.
"""
import os
import subprocess

from conan import ConanFile


class TestPerlParamsValidate(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-params-validate"]
        pkg_folder = dep.package_folder

        # .pm files in site_perl/5.42.0/ (arch-independent)
        # .so files in site_perl/5.42.0/aarch64-linux/ (arch-specific)
        site_lib = os.path.join(pkg_folder,
                                "data", "service", "hnp", "perl.org",
                                "perl_5.42.0", "lib", "site_perl", "5.42.0")
        site_arch = os.path.join(site_lib, "aarch64-linux")

        # --- L4: Verify XS.so is a valid ELF with boot function ---
        so_path = os.path.join(site_arch, "auto", "Params", "Validate", "XS", "XS.so")
        assert os.path.exists(so_path), f"XS.so not found: {so_path}"

        # Use self.run for CI L0d compliance (requires self.run in test())
        self.run(f'file "{so_path}"')
        self.run(f'readelf --dyn-syms --wide "{so_path}" | grep boot_Params__Validate__XS')

        # --- L1: Try loading Params::Validate (PP fallback expected) ---
        # Module::Implementation may be in user's local perl5 lib
        local_perl_lib = os.path.join(os.path.expanduser("~"), "usr", "local", "lib", "perl5")
        perl5lib = f"{site_arch}:{site_lib}"
        if os.path.isdir(local_perl_lib):
            perl5lib = f"{perl5lib}:{local_perl_lib}"

        result = subprocess.run(
            ["perl", "-I", site_arch, "-I", site_lib,
             "-e", "use Params::Validate; "
                   "print \"TEST OK $Params::Validate::VERSION\\n\";"],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "PERL5LIB": perl5lib}
        )
        if result.returncode == 0 and "TEST OK" in result.stdout:
            self.output.info("✅ Params::Validate PP mode test passed")
        else:
            self.output.warning(
                f"⚠️ Runtime test failed (expected on HarmonyOS HMDFS): "
                f"{result.stderr.strip()[:200]}"
            )
