#!/usr/bin/env python3
"""Conan test_package for perl-package-deprecationmanager — L1 smoke test.

Verifies that Package::DeprecationManager can be loaded and used after installation.
"""
import os

from conan import ConanFile


class PerlPackageDeprecationManagerTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Smoke test: load Package::DeprecationManager with -deprecations parameter
        # The VirtualRunEnv generator sets PERL5LIB from the recipe's runenv_info
        self.run(
            'perl -e "use Package::DeprecationManager -deprecations => {'
            " 'TestModule' => '0.01' }; "
            'print \\"Package::DeprecationManager OK\\n\\";"',
            env="conanrun",
        )
