#!/usr/bin/env python3
"""Conan test_package — w-calc 2.5 CLI consumer verification.

w-calc is a standalone command-line calculator (not a library). test.c is
compiled with the profile compiler and executed against the installed
bin/wcalc binary, performing 8 deterministic assertions (existence, version,
arithmetic, precision, hexadecimal, variable persistence, stdin evaluation,
syntax diagnostic). test.c itself prints the HMBS_TEST_PACKAGE_RESULT marker
with discovered/passedCount taken from its real assertion outcomes.

test() also re-emits HMBS_UPSTREAM_TEST_RESULT from the marker persisted by
build() into the package (res/upstream_test_result.json). test_package runs on
every preflight even when conan skips a cached build() ("Already installed"),
so the upstream evidence is always present. A missing packaged marker is an
explicit failure, never a silent pass.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class WcalcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def configure(self):
        # Same fork-pressure fix as the main recipe: the generated env scripts'
        # deactivation preamble forks `printenv` once per variable, and that
        # burst trips the worker's process-table limit.  test_package declares
        # `generators = "VirtualRunEnv"` explicitly, and explicit generators run
        # *before* generate(), so the conf must be set in configure() to take
        # effect on the run-env scripts.
        self.conf.define("tools.env:deactivation_mode", "function")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: compiler path from Conan conf, never a bare shell variable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c", "clang")
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_wcalc")
        self.run('"%s" -O2 "%s" -o "%s"' % (cc, src, out))

    def test(self):
        dep = self.dependencies["w-calc"]
        bin_path = os.path.join(dep.package_folder, "bin", "wcalc")
        if not os.path.isfile(bin_path):
            raise ConanException("wcalc binary missing: %s" % bin_path)

        test_bin = os.path.join(self.build_folder, "test_wcalc")
        # test.c runs the binary itself and emits HMBS_TEST_PACKAGE_RESULT.
        self.run('"%s" "%s"' % (test_bin, bin_path))

        # Re-emit the upstream marker persisted by build().
        result_path = os.path.join(
            dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) — "
                "upstream make check did not run during build(); refusing to "
                "pass silently" % result_path)
        with open(result_path, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
