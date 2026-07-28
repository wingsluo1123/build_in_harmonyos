#!/usr/bin/env python3
"""Conan test_package for perl-object-insideout — Perl smoke test.

Verifies that the Object::InsideOut module package is correctly built:
  1. Package structure: .pm files at lib/perl5/Object/InsideOut.pm
  2. Version verification: parse VERSION from .pm file
  3. Module load attempt: tries to load Object::InsideOut, gracefully handles
     missing runtime dependency Exception::Class (not packaged as Conan)
"""
import os

from conan import ConanFile


class PerlObjectInsideOutTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["perl-object-insideout"]
        dep_pkg = dep.package_folder
        oio_pm = os.path.join(dep_pkg, "lib", "perl5", "Object", "InsideOut.pm")

        # Verify package structure: .pm files must be at lib/perl5/
        if not os.path.isfile(oio_pm):
            raise Exception(
                f"Object::InsideOut.pm not found at expected path: {oio_pm}"
            )

        # Build PERL5LIB from dependency package folders
        perl5lib_paths = []
        for d in self.dependencies.values():
            pkg_lib = os.path.join(d.package_folder, "lib", "perl5")
            if os.path.isdir(pkg_lib):
                perl5lib_paths.append(pkg_lib)
        perl5lib = ":".join(perl5lib_paths)

        # Write a test script that verifies module files and attempts to load
        test_pl = os.path.join(self.build_folder, "test_oio.pl")
        with open(test_pl, "w") as f:
            f.write(
                "use strict;\n"
                "use warnings;\n"
                f"my $pm_file = '{oio_pm}';\n"
                'die "Module file not found: $pm_file" unless -f $pm_file;\n'
                'open my $fh, "<", $pm_file or die "Cannot open: $!";\n'
                'my $content = do { local $/; <$fh> };\n'
                "close $fh;\n"
                r'my ($ver) = $content =~ /\$VERSION\s*=\s*[\x27"]([\d.]+)[\x27"]/;'
                '\ndie "VERSION not found" unless $ver;\n'
                'die "VERSION mismatch: $ver" unless $ver eq "4.05";\n'
                "\n"
                "eval { require Object::InsideOut; };\n"
                r'if ($@ && $@ =~ /Exception[\/:]Class/) {'
                '\n    exit 0;\n'
                "}\n"
                'elsif ($@) {\n'
                '    die "Unexpected error: $@";\n'
                "}\n"
                'die "Version mismatch" unless $Object::InsideOut::VERSION eq "4.05";\n'
            )

        cmd = f'PERL5LIB="{perl5lib}" perl {test_pl}'
        self.run(cmd)
