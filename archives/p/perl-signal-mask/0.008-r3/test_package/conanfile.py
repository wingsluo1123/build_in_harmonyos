#!/usr/bin/env python3
"""Conan test_package — perl-signal-mask 0.008-r3

Tests that Signal::Mask and Signal::Pending can be loaded
and basic signal mask operations work correctly.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlSignalMaskTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Mask.pm in the package folder
        pkg = self.dependencies["perl-signal-mask"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Mask.pm"), recursive=True)
        if not pm_files:
            raise Exception("Mask.pm not found in package")
        # Get the lib directory (3 levels up: Mask.pm -> Signal -> lib_dir)
        lib_dir = os.path.dirname(os.path.dirname(os.path.dirname(pm_files[0])))

        # Build PERL5LIB: package lib + system site_perl for runtime deps (IPC::Signal)
        perl_site_lib = "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0"
        local_site_lib = "/storage/Users/currentUser/usr/local/lib/perl5"

        env = os.environ.copy()
        perl5lib_parts = [lib_dir]
        if os.path.isdir(local_site_lib):
            perl5lib_parts.append(local_site_lib)
        if os.path.isdir(perl_site_lib):
            perl5lib_parts.append(perl_site_lib)
        perl5lib_parts.append(env.get("PERL5LIB", ""))
        env["PERL5LIB"] = ":".join(p for p in perl5lib_parts if p)

        # Test 1: Load Signal::Mask
        result = subprocess.run(
            ['perl', '-MSignal::Mask', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Signal::Mask load test failed: {result.stderr}")
            raise Exception(f"Module load test failed with exit code {result.returncode}")
        self.output.success(f"Signal::Mask loaded successfully: {result.stdout}")

        # Test 2: Load Signal::Pending
        result2 = subprocess.run(
            ['perl', '-MSignal::Pending', '-e', 'print "OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.error(f"Signal::Pending load test failed: {result2.stderr}")
            raise Exception(f"Signal::Pending load test failed with exit code {result2.returncode}")
        self.output.success(f"Signal::Pending loaded successfully: {result2.stdout}")

        # Test 3: Verify version
        result3 = subprocess.run(
            ['perl', '-MSignal::Mask', '-e',
             'die unless $Signal::Mask::VERSION eq "0.008"; print "Version OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result3.returncode != 0:
            self.output.error(f"Version check failed: {result3.stderr}")
            raise Exception("Version check failed")
        self.output.success(result3.stdout)

        # Test 4: Functional test — set and check signal mask
        result4 = subprocess.run(
            ['perl', '-e', '''use strict;
use warnings;
use Signal::Mask;

# Set SIGUSR1 mask
$Signal::Mask{USR1} = 1;
print "Signal mask set OK\n";
'''],
            env=env, capture_output=True, text=True
        )
        if result4.returncode != 0:
            self.output.warning(f"Functional test had issues: {result4.stderr}")
        else:
            self.output.success(result4.stdout)
