#!/usr/bin/env python3
"""Conan test_package — ocaml-compiler-libs 0.12.4

R34: really consumes the tested package:
  1. test.sh asserts the packaged artifacts exist;
  2. bytecode-compiles test_ocl.ml against the packaged Ocaml_common
     interfaces (compile-only);
  3. native-compiles + runs test_ocl.ml: builds a Parsetree node with
     Ocaml_common.Ast_helper, pretty-prints it with Pprintast, parses code
     with Parse.implementation and checks Longident/Location — all from the
     packaged repackaged compiler libraries ("ALL TESTS PASSED");
  4. native-compiles + runs test_ohos_e2e.ml: HarmonyOS-specific end-to-end
     case — real file I/O: parse a .ml file from disk, pretty-print it back
     and verify the round-trip ("ALL OHOS E2E PASSED").
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class OclTestConan(ConanFile):
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
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml",
                               "ocaml-compiler-libs")

        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "{0}" "{1}" "{2}" "{3}"'.format(test_sh, lib_dir, ocaml_lib, ocaml_bin),
            env="conanbuild",
        )
        self.output.info("ocaml-compiler-libs test_package: ALL PASS")
