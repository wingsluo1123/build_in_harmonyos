#!/usr/bin/env python3
"""Conan test_package — Perl module JSON::MaybeXS 1.004008.

L1 test: Verify the Perl module can be loaded and used for JSON
encoding/decoding after installation.

R34: Test calls actual JSON::MaybeXS API (encode_json, decode_json)
to validate functionality, not just a stub print.
"""
import os

from conan import ConanFile


class PerljsonmaybexsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["perl-json-maybexs"].package_folder
        perl_lib = os.path.join(pkg_folder, "lib")
        test_script = os.path.join(os.path.dirname(__file__), "test_maybexs.sh")

        # R34: Run test script that loads JSON::MaybeXS and calls
        # encode_json + decode_json (actual API calls)
        self.run(f'sh "{test_script}" "{perl_lib}"', env="conanrun")
        self.output.info("JSON::MaybeXS test passed (module loaded and API verified)")
