#!/usr/bin/env python3
"""Conan test_package — Parallel::Pipes (pure Perl module)."""
import os
import glob
import tempfile

from conan import ConanFile


class PerlparallelpipesTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the installed module path from the dependency
        dep = self.dependencies["perl-parallel-pipes"]
        pkg_folder = dep.package_folder
        pipes_files = glob.glob(os.path.join(pkg_folder, "**", "Parallel", "Pipes.pm"), recursive=True)
        if not pipes_files:
            raise Exception("Parallel/Pipes.pm not found in package")
        perl_lib_dir = os.path.dirname(os.path.dirname(pipes_files[0]))
        # Write a simple test script to avoid shell quoting issues
        test_script = os.path.join(tempfile.gettempdir(), "test_parallel_pipes.pl")
        with open(test_script, "w") as f:
            f.write("use Parallel::Pipes;\n")
            f.write("use Parallel::Pipes::App;\n")
            f.write("my $pipes = Parallel::Pipes->new(3);\n")
            f.write("print \"OK\\n\";\n")
        self.run('PERL5LIB="{}" perl {}'.format(perl_lib_dir, test_script))
