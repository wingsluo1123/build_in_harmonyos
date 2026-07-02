#!/usr/bin/env python3
"""Conan test_package — SNMP::Session Perl module.

L1 test: verify the installed Perl module can be loaded and used.
"""
import os

from conan import ConanFile


class PerlSnmpSessionTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Test that the Perl modules can be loaded and basic operations work
        test_script = (
            "use SNMP_Session;\n"
            "use BER;\n"
            "use SNMP_util;\n"
            "my $version = $SNMP_Session::VERSION;\n"
            "die 'version mismatch' unless $version eq '1.16';\n"
            "# Test BER encode (no network needed)\n"
            "my $encoded = encode_oid(1,3,6,1);\n"
            "die 'BER encode failed' unless defined $encoded && length($encoded) > 0;\n"
            "print 'SNMP::Session test OK\\n';\n"
        )
        test_file = os.path.join(self.source_folder, "test_snmp_session.pl")
        with open(test_file, "w") as f:
            f.write(test_script)
        self.run(f"perl {test_file}", env="conanrun")
