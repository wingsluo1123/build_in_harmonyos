#!/usr/bin/env python3
"""Conan test_package — Pod::Wrap (pure Perl module).

Verifies that the package contains the Wrap.pm file and that the module
can be loaded and used to wrap POD text.
"""
import os
import glob
import tempfile
import subprocess

from conan import ConanFile


class PodWrapTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _build_perl5lib(self, pkg_perl_lib):
        """Construct PERL5LIB including system Pod::Parser path."""
        home = os.path.expanduser("~")
        try:
            result = subprocess.run(
                ["perl", "-e", "print $]"],
                capture_output=True, text=True, timeout=10
            )
            perl_ver_full = result.stdout.strip()
            major = int(float(perl_ver_full))
            minor = int((float(perl_ver_full) * 1000) % 1000)
            perl_ver = f"{major}.{minor // 100}.0"
        except Exception:
            perl_ver = "5.42.0"

        parts = [pkg_perl_lib]
        site_perl = os.path.join(home, "usr", "local", "lib", "site_perl", perl_ver)
        std_perl = os.path.join(home, "usr", "local", "lib", perl_ver)
        if os.path.isdir(site_perl):
            parts.append(site_perl)
        if os.path.isdir(std_perl):
            parts.append(std_perl)

        existing = os.environ.get("PERL5LIB", "")
        if existing:
            parts.append(existing)
        return ":".join(parts)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-pod-wrap"]
        pkg_folder = dep.package_folder
        wrap_files = glob.glob(
            os.path.join(pkg_folder, "**", "Pod", "Wrap.pm"),
            recursive=True,
        )
        if not wrap_files:
            raise Exception("Pod/Wrap.pm not found in package")
        # Pod/Wrap.pm → Pod/ → lib/perl5 (2 dirname calls to get PERL5LIB root)
        perl_lib_dir = os.path.dirname(
            os.path.dirname(wrap_files[0])
        )

        # 1. Verify package artifact integrity via test_package.py
        test_script = os.path.join(os.path.dirname(__file__), "test_package.py")
        self.run('python3 "{}" "{}"'.format(test_script, wrap_files[0]))

        # 2. Functional test: load module and use it to wrap POD text
        func_test = os.path.join(tempfile.gettempdir(), "test_pod_wrap.pl")
        with open(func_test, "w") as f:
            f.write("use strict;\n")
            f.write("use warnings;\n")
            f.write("use Pod::Wrap;\n")
            f.write("use File::Temp qw(tempfile);\n")
            f.write("\n")
            # Create input POD with regular text and verbatim text
            f.write("my ($in_fh, $in_file) = tempfile();\n")
            f.write('print $in_fh "=pod\\n\\n";\n')
            f.write('print $in_fh "This is a regular paragraph that should be wrapped.\\n\\n";\n')
            f.write('print $in_fh "    verbatim text should not be wrapped\\n\\n";\n')
            f.write('print $in_fh "=cut\\n";\n')
            f.write("close $in_fh;\n")
            f.write("\n")
            f.write("my ($out_fh, $out_file) = tempfile();\n")
            f.write("Pod::Wrap->new->parse_from_file($in_file, $out_file);\n")
            f.write("close $out_fh;\n")
            f.write("\n")
            f.write("open my $read_fh, '<', $out_file or die \"Cannot open output: $!\";\n")
            f.write("my $output = do { local $/; <$read_fh> };\n")
            f.write("close $read_fh;\n")
            f.write("\n")
            f.write('die "FAIL: output is empty" unless length($output);\n')
            f.write('die "FAIL: regular text not in output" unless $output =~ /regular paragraph/;\n')
            f.write('die "FAIL: verbatim text not preserved" unless $output =~ /verbatim text should not be wrapped/;\n')
            f.write('print "ALL ASSERTIONS PASSED\\n";\n')

        # Set PERL5LIB to include both package lib and system Pod::Parser path
        perl5lib = self._build_perl5lib(perl_lib_dir)
        self.run('PERL5LIB="{}" perl {}'.format(perl5lib, func_test))
