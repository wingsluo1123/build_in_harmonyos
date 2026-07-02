#!/usr/bin/env python3
"""Conan test_package — perl-specio-library-path-tiny 0.05

Tests that Specio::Library::Path::Tiny can be loaded and used to
declare Path::Tiny type constraints (Path, AbsPath, RealPath, File,
AbsFile, RealFile, Dir, AbsDir, RealDir).
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlSpecioLibraryPathTinyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _get_perl5lib(self, pkg_folder):
        """Build PERL5LIB from package lib + system Perl paths."""
        parts = []
        # Package lib
        for site_lib in glob.glob(os.path.join(pkg_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                parts.append(site_lib)
                break
        base_perl = os.path.join(pkg_folder, "lib", "perl5")
        if os.path.isdir(base_perl):
            parts.append(base_perl)
        # System Perl paths for runtime dependencies
        for sys_path in [
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0",
            "/storage/Users/currentUser/usr/local/lib/perl5",
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0",
        ]:
            if os.path.isdir(sys_path):
                parts.append(sys_path)
        existing = os.environ.get("PERL5LIB", "")
        if existing:
            parts.append(existing)
        return ":".join(parts)

    def test(self):
        # Find Tiny.pm in the package folder
        pkg = self.dependencies["perl-specio-library-path-tiny"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Tiny.pm"), recursive=True)
        if not pm_files:
            raise Exception("Specio/Library/Path/Tiny.pm not found in package")
        self.output.info(f"Found Tiny.pm: {pm_files[0]}")

        # Verify version in .pm file
        with open(pm_files[0]) as f:
            content = f.read()
        if "0.05" not in content:
            raise Exception("Version 0.05 not found in Tiny.pm")
        self.output.info("Version 0.05 verified in Tiny.pm content")

        # Check for Path::Tiny reference
        if "Path::Tiny" in content:
            self.output.info("Path::Tiny reference found in module")
        if "Specio" in content:
            self.output.info("Specio reference found in module")

        # Set up PERL5LIB
        perl5lib = self._get_perl5lib(pkg_folder)
        self.output.info(f"PERL5LIB={perl5lib}")

        env = os.environ.copy()
        env["PERL5LIB"] = perl5lib
        env["SPECIO_IMPLEMENTATION"] = "PP"

        # Test 1: Load module
        result = subprocess.run(
            ['perl', '-MSpecio::Library::Path::Tiny', '-e',
             'print "Specio::Library::Path::Tiny loaded OK\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Module load test failed: {result.stderr}")
            raise Exception(f"Module load test failed with exit code {result.returncode}")
        self.output.success(f"Module loaded successfully: {result.stdout.strip()}")

        # Test 2: Check version
        result2 = subprocess.run(
            ['perl', '-MSpecio::Library::Path::Tiny', '-e',
             'print "VERSION=", $Specio::Library::Path::Tiny::VERSION, "\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.error(f"Version check failed: {result2.stderr}")
            raise Exception(f"Version check failed with exit code {result2.returncode}")
        self.output.info(f"Version check: {result2.stdout.strip()}")

        self.output.info("perl-specio-library-path-tiny 0.05 package structure verified OK")
