#!/usr/bin/env python3
"""Conan test_package — perl-specio-library-path-tiny 0.05

Tests that Specio::Library::Path::Tiny can be loaded and used to
declare Path::Tiny type constraints (Path, AbsPath, RealPath, File,
AbsFile, RealFile, Dir, AbsDir, RealDir).
"""
import os
import glob

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

        env = {
            "PERL5LIB": perl5lib,
            "SPECIO_IMPLEMENTATION": "PP",
        }

        # Test 1: Load module
        self.run(
            'perl -MSpecio::Library::Path::Tiny -e '
            '"print qq{Specio::Library::Path::Tiny loaded OK\n}"',
            env=env,
        )
        self.output.success("Module loaded successfully")

        # Test 2: Check version
        self.run(
            'perl -MSpecio::Library::Path::Tiny -e '
            '"print qq{VERSION=$Specio::Library::Path::Tiny::VERSION\n}"',
            env=env,
        )
        self.output.info("Version check completed")

        # Test 3: Run consumer-perspective Perl test script
        test_script = os.path.join(self.source_folder, "test_specio_library_path_tiny.pl")
        self.run(f'perl "{test_script}"', env=env)

        self.output.info("perl-specio-library-path-tiny 0.05 package structure verified OK")
