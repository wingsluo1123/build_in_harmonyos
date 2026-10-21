#!/usr/bin/env python3
"""Conan test_package — indi-starbook (L1 official upstream test).

indi-starbook ships an INDI driver *executable*, not a linkable library.
Per R34 we still exercise a real public API: the upstream official unit
test (test_starbook.cpp, GTest) exercises the public protocol-types layer
starbook_types.cpp — CommandResponse parsing ("OK"/"ERROR"/whitespace
variants) and DateTime formatting ("2018+10+05+12+30+04"). Both sources
are vendored in this directory (starbook_types.cpp carries the 0004 ltrim
fix; CI L0c requires test sources inside test_package/) and compiled
against the real libnova/GTest dependency packages (CMakeDeps). (Layer 1
deliberately does not touch libindi/curl: the tested sources only need
libnova's ln_* astrometry.)

Then we assert the produced driver binary is present (R34/L1e: the test
must fail without package artifacts) and probe it best-effort with --help.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class IndiStarbookTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Conan 2.29 test-graph Skip optimization: static TRANSITIVE libnova.a
        # is marked Skip in the test branch -> package_folder None and no
        # CMakeDeps config -> find_package(libnova REQUIRED) would fail the
        # same way indi-gpsd's test_package failed its round 1. Declare it
        # directly (preventive; gpsd round-1 probe-verified mechanism).
        self.requires("libnova/0.16")

    def build_requirements(self):
        # Upstream official unit test is GTest-based (test_starbook.cpp).
        self.test_requires("gtest/1.17.0.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Layer 1 (R34): upstream official unit test, compiled against real
        # libnova + GTest packages.
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_starbook"),
                     env="conanrun")

        # Layer 2: the packaged driver binary must exist — this is what makes
        # the test depend on the package artifacts (executable-only package;
        # Layer 1 compiles test_package's own vendored sources, so the L1e
        # bin/ sabotage is caught by this assertion, not by Layer 1).
        # Execution is best-effort: some environments deny exec on binaries
        # linked to shared libindi (EPERM/126), and --help exit codes vary.
        pkg = self.dependencies["indi-starbook"].package_folder
        exe = os.path.join(pkg, "bin", "indi_starbook_telescope")
        if not os.path.isfile(exe):
            raise ConanException(f"packaged driver binary missing: {exe}")
        if can_run(self):
            ret = self.run(f'"{exe}" --help', ignore_errors=True)
            if ret != 0:
                self.output.warning(
                    f"driver --help exited {ret}; tolerated (exec-restricted "
                    "environment or driver-specific exit code), "
                    "artifact presence already asserted"
                )
