#!/usr/bin/env python3
"""Conan test_package — pod2man (podlators) 6.0.2.

Verifies that pod2man script is installed and can convert a POD file to man page format.
"""
import os

from conan import ConanFile


class Pod2manTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["pod2man"].package_folder, "bin", "pod2man")
        # Create a minimal POD file and convert it to man page format
        pod_file = os.path.join(self.build_folder, "test.pod")
        with open(pod_file, "w") as f:
            f.write("=head1 NAME\n\ntest - A test POD file\n\n=head1 DESCRIPTION\n\nThis is a test.\n\n=cut\n")
        out_file = os.path.join(self.build_folder, "test.1")
        self.run(f'perl "{bin_path}" "{pod_file}" "{out_file}"', env="conanrun")
