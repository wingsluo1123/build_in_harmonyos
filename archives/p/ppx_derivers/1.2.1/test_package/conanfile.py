#!/usr/bin/env python3
"""Conan test_package — ppx_derivers 1.2.1

R34: really consumes the tested package:
  1. test.sh asserts the packaged artifacts exist;
  2. bytecode-compiles test_pd.ml against the packaged Ppx_derivers
     interfaces (compile-only);
  3. native-compiles + runs test_pd.ml: extends the exported extensible
     `deriver` type, registers/looks up entries, checks duplicate
     registration raises and unknown lookup returns None
     ("ALL TESTS PASSED");
  4. native-compiles + runs test_ohos_e2e.ml: HarmonyOS-specific end-to-end
     case — real file I/O: registry contents serialized to a file, read
     back and re-checked ("ALL OHOS E2E PASSED").
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class PpxDeriversTestConan(ConanFile):
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
        lib_dir = os.path.join(pkg.package_folder, "lib", "ocaml", "ppx_derivers")

        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        self.run(
            'sh "{0}" "{1}" "{2}" "{3}"'.format(test_sh, lib_dir, ocaml_lib, ocaml_bin),
            env="conanbuild",
        )
        self.output.info("ppx_derivers test_package: ALL PASS")
