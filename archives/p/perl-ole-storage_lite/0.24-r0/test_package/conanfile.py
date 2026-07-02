#!/usr/bin/env python3
"""Conan test_package — perl-ole-storage_lite L1 test.

Verifies that OLE::Storage_Lite Perl module can be loaded and reports version.
"""
from conan import ConanFile


class PerlolestorageliteTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # L1: verify Perl module loads and prints version
        self.run('perl -e "use OLE::Storage_Lite; print OLE::Storage_Lite->VERSION, qq(\\n)"', env="conanrun")
