#!/usr/bin/env python3
"""test_package — HarmonyOS consumer tests for raptor2 2.0.16 (Conan L1).

Two consumer cases run against the installed package:

  R12-01  library API end-to-end: test_raptor2 parses a real Turtle document and
          a real RDF/XML document with the installed libraptor2, serializes both
          to N-Triples and asserts the two syntaxes yield the same expected
          triple set.
  R12-02  installed rapper CLI end-to-end: the packaged `rapper` binary converts
          the same RDF/XML document to N-Triples and its real business output
          (the emitted statements) is asserted.

Both cases consume only the artifacts of this recipe (no system raptor2).
"""
import os
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Raptor2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _data_dir(self):
        for candidate in (os.path.join(self.recipe_folder, "data"),
                          os.path.join(self.source_folder, "data")):
            if os.path.isdir(candidate):
                return candidate
        raise ConanException("test data directory not found next to test_package")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skipping consumer execution")
            return

        data_dir = self._data_dir()

        # ── R12-01: library API end-to-end (Turtle + RDF/XML -> N-Triples) ──
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_raptor2")
        self.run('"{}" "{}"'.format(test_binary, data_dir), env="conanrun")

        # ── R12-02: installed rapper CLI end-to-end ──────────────────────────
        rapper = os.path.join(self.dependencies["raptor2"].cpp_info.bindir, "rapper")
        if not os.path.isfile(rapper):
            raise ConanException("the package did not install the rapper CLI: {}".format(rapper))

        buffer = StringIO()
        self.run('"{}" -q -i rdfxml -o ntriples "{}"'.format(
            rapper, os.path.join(data_dir, "sample.rdf")), stdout=buffer, env="conanrun")
        ntriples = buffer.getvalue()

        expected = [
            "<http://example.org/alice> <http://example.org/knows> <http://example.org/bob> .",
            '<http://example.org/alice> <http://example.org/name> "Alice" .',
            '<http://example.org/bob> <http://example.org/name> "Bob" .',
        ]
        missing = [line for line in expected if line not in ntriples]
        if missing:
            raise ConanException(
                "rapper output is missing expected statements: {}\n--- rapper output ---\n{}".format(
                    missing, ntriples))
        self.output.info("rapper CLI produced all 3 expected statements")
