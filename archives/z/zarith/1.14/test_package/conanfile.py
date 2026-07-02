#!/usr/bin/env python3
"""Conan test_package -- ZArith 1.14

Verifies that zarith library is installed and can perform big integer arithmetic.
Test: 42 + 1 = 43 (big integer addition).
"""
import os

from conan import ConanFile


class ZarithTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Verify zarith is findable via ocamlfind
        self.run('ocamlfind query zarith -format "%v"', env="conanrun")
        # Verify big integer arithmetic: 42 + 1 = 43
        self.run(
            'ocamlfind ocaml -package zarith -linkpkg -e '
            '"let () = let n = Z.add (Z.of_int 42) (Z.of_int 1) in assert (Z.to_int n = 43)"',
            env="conanrun"
        )
