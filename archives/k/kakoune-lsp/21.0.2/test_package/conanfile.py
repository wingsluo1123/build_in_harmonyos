#!/usr/bin/env python3
"""Conan test_package for kakoune-lsp 21.0.2 — consumer smoke test.

The upstream cargo test suite (16 registered #[test] across markup/
position/text_edit/util) runs in the MAIN recipe's build() — below/
0.11.0 precedent (MANIFEST declares upstream_test_in_build: true);
the build-phase verdict is carried by the L1 gate, so the CI worker
needs no cargo during the test_package phase.

The test_package phase runs the consumer smoke cases against the
packaged (signed) bin/kak-lsp — --version / --help / -h / --kakoune —
via test.sh, emitting HMBS_TEST_PACKAGE_RESULT.
"""
import os

from conan import ConanFile


class KakouneLspTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["kakoune-lsp"]
        bindir = dep.cpp_info.bindirs[0]
        bindir = bindir if os.path.isabs(bindir) else os.path.join(
            dep.package_folder, bindir)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        binpath = os.path.join(bindir, "kak-lsp")
        self.run(f'{bash} test.sh "{binpath}"', env="conanbuild")
