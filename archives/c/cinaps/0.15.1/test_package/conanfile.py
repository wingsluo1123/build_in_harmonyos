#!/usr/bin/env python3
"""Conan test_package — cinaps 0.15.1

R34: really consumes the tested package:
  1. test.sh asserts the packaged artifacts exist (bin/cinaps + libraries);
  2. --help runs and prints the option list;
  3. staged mode generates the evaluation driver from the upstream
     test_staged.ml content (verbatim), the driver is compiled against the
     packaged cinaps.runtime library and RUN — the in-sync file exits 0;
  4. negative control: the same pipeline on a file whose expectation block
     was corrupted exits non-zero and produces <file>.corrected containing
     the regenerated value — proving the tool really evaluates the embedded
     OCaml code and compares against the expectation.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class CinapsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.2")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def generate(self):
        pass

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.2"]
        bin_dir = os.path.join(pkg.package_folder, "bin")
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml", "cinaps")
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")

        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "{0}" "{1}" "{2}" "{3}" "{4}"'.format(
                test_sh, bin_dir, lib_dir, ocaml_lib, ocaml_bin),
            env="conanbuild",
        )
        self.output.info("cinaps test_package: ALL PASS")
