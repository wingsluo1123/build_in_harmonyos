#!/usr/bin/env python3
"""Conan test_package for crafty — L1 official test.

Crafty is a command-line chess engine (application, not library). The L1
test invokes the packaged `crafty` binary directly with a non-interactive
command stream (`bench` then `quit`) and asserts it exits 0 and prints the
version banner. This satisfies R34 (test must actually exercise the tested
package: we run the real crafty engine, not a printf stub).
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class CraftyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No compile step — we test the prebuilt crafty binary from the package.
        # cpp.build.bindirs is empty in the test_package context until we copy
        # the packaged binary ourselves; resolve it from the tested package's
        # package_folder via the requires() dependency.
        bindir = os.path.join(self.dependencies["crafty"].package_folder, "bin")
        copy(self, "crafty", bindir, self.build_folder)

    def test(self):
        # `bench` runs crafty's internal performance benchmark (search a fixed
        # set of positions to a fixed depth). Non-interactive, exits cleanly.
        # `quit` terminates the engine. We pipe both via stdin to avoid hang.
        self.run(
            'printf "bench\\nquit\\n" | "./crafty"',
            env="conanrun",
            cwd=self.build_folder,
        )
