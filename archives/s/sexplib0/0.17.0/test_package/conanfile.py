#!/usr/bin/env python3
"""Conan test_package — sexplib0 0.17.0

R34: really consumes the tested package:
  1. test.sh asserts the packaged artifacts exist;
  2. bytecode-compiles test_sexplib0.ml against the packaged sexplib0.cma
     (the registry OCaml toolchain has no findlib, so explicit archive
     linkage is the standard form; compile-only);
  3. native-compiles (sexplib0.cmxa) + runs test_sexplib0.ml: exercises
     Sexp parsing/printing and the Sexp_conv base-type converters from the
     package, asserting every value ("ALL TESTS PASSED");
  4. native-compiles + runs test_ohos_e2e.ml: HarmonyOS-specific end-to-end
     case — file I/O (write/read a real .sexp file), parse, field query,
     re-serialize round-trip ("ALL OHOS E2E PASSED").
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class Sexplib0TestConan(ConanFile):
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
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml", "sexplib0")

        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "{0}" "{1}" "{2}" "{3}"'.format(test_sh, lib_dir, ocaml_lib, ocaml_bin),
            env="conanbuild",
        )
        self.output.info("sexplib0 test_package: ALL PASS")
