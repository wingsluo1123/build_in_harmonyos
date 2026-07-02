#!/usr/bin/env python3
"""Conan test_package — Set::IntSpan Perl module.

L1 test: verify the installed Perl module can be loaded and used.
"""
import os

from conan import ConanFile


class PerlSetIntSpanTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Test that the Perl module can be loaded and basic operations work
        test_script = (
            "use Set::IntSpan;\n"
            "my $set = Set::IntSpan->new('1-10,20-25');\n"
            "die 'cardinality mismatch' unless $set->cardinality() == 16;\n"
            "die 'member check failed' unless $set->member(5);\n"
            "die 'non-member check failed' if $set->member(15);\n"
            "print 'Set::IntSpan test OK\\n';\n"
        )
        test_file = os.path.join(self.source_folder, "test_intspan.pl")
        with open(test_file, "w") as f:
            f.write(test_script)
        self.run(f"perl {test_file}", env="conanrun")
