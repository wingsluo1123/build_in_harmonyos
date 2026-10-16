#!/usr/bin/env python3
"""Conan test_package — ocaml-re 1.13.2

R34: really consumes the tested package:
  1. test.sh asserts the packaged artifacts exist (core + 4 sub-libraries);
  2. bytecode-compiles test_re.ml against the packaged re.cma (compile-only);
  3. native-compiles (re.cmxa) + runs test_re.ml: exercises Perl/Glob/Posix
     compilation, group extraction, split, replace_string and the Str
     compatibility layer from the package, asserting every value;
  4. native-compiles + runs test_ohos_e2e.ml: HarmonyOS file-I/O end-to-end
     case — writes a real file, regex-parses each line, aggregates, writes
     and re-reads a result file.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class OcamlReTestConan(ConanFile):
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
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml", "re")

        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "{0}" "{1}" "{2}" "{3}"'.format(test_sh, lib_dir, ocaml_lib, ocaml_bin),
            env="conanbuild",
        )
        self.output.info("ocaml-re test_package: ALL PASS")
