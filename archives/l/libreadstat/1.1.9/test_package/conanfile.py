#!/usr/bin/env python3
"""test_package for libreadstat/1.1.9 — consumer-side verification (L1).

Two consumer suites are built against the *packaged* library only (through the
CMakeDeps target `readstat::readstat`):

  * consumer_error_paths — parser lifecycle and error-code mapping for a
    missing file (round-1 suite, kept).
  * consumer_round_trip  — HarmonyOS regression: the public writer API emits a
    real .sav and a real zlib-compressed .zsav through POSIX file descriptors,
    the parser reads them back from disk, every value is compared, and the
    row-limit window is checked.

test() additionally drives the packaged `readstat` CLI over the .sav fixture
that consumer_round_trip produced, so the packaged executable is verified on
the target as well.  CI gates L0d/L1a require real invocations like these, not
a stub whose body only prints and returns success.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ReadstatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _binary(self, name):
        """Locate a consumer executable.

        cmake_layout puts the executable at the root of the CMake build dir,
        while `self.cpp.build.bindirs[0]` resolves to "." for a consumer
        recipe (round-1 evidence: RUN "./test_readstat" → Error 127), so the
        absolute candidates are tried in order.
        """
        candidates = [
            os.path.join(self.build_folder, name),
            os.path.join(self.cpp.build.bindirs[0], name),
            os.path.join(self.source_folder, name),
        ]
        return next((c for c in candidates if os.path.isfile(c)), candidates[0])

    def _packaged_cli(self):
        """Package under test's `readstat` binary.

        The conan package name is `libreadstat` (so `self.dependencies` is keyed
        by that), while the shipped executable keeps its upstream name `readstat`.
        """
        dep = self.dependencies["libreadstat"]
        candidates = [
            os.path.join(dep.cpp_info.bindir, "readstat"),
            os.path.join(dep.package_folder, "bin", "readstat"),
        ]
        return next((c for c in candidates if os.path.isfile(c)), None)

    def test(self):
        if not can_run(self):
            self.output.info("cannot run target binaries in this profile; build-only check")
            return

        fixtures = os.path.join(self.build_folder, "fixtures")
        for name in ("consumer_error_paths", "consumer_round_trip"):
            binary = self._binary(name)
            self.output.info(f"consumer check: {binary}")
            self.run(f'"{binary}" "{fixtures}"', env="conanrun")

        # Packaged CLI over the .sav fixture written by consumer_round_trip:
        # cli_smoke.py runs `readstat <fixture>` and `readstat <fixture> -`
        # and asserts on the emitted metadata / CSV lines.
        cli = self._packaged_cli()
        if cli is None:
            raise ConanException("packaged `readstat` CLI not found in the package under test")
        self.output.info(f"packaged CLI check: {cli}")
        cli_smoke = os.path.join(self.source_folder, "cli_smoke.py")
        fixture = os.path.join(fixtures, "ohos-consumer.sav")
        # Reuse the interpreter that is running this recipe: it is guaranteed
        # to exist on the worker, unlike a `python3` on PATH.
        self.run(f'"{sys.executable}" "{cli_smoke}" "{cli}" "{fixture}"')
