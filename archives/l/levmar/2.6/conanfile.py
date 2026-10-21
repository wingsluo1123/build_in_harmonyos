#!/usr/bin/env python3
"""Conan recipe for levmar 2.6.

Upstream ships a legacy CMake project (``cmake_minimum_required(VERSION 2.6)``)
that defines neither ``install()`` rules nor any CTest entry.  CMake 4.x refuses
to configure it without an explicit policy floor, and the package step therefore
stages the static library, the ``configure_file`` generated public header and
the licence explicitly instead of relying on ``cmake.install()``.

The upstream CMake file defaults to ``HAVE_LAPACK=1`` with a hard coded
``LAPACKBLAS_DIR=/usr/lib``.  The OHOS sysroot provides neither LAPACK nor BLAS,
so the recipe asks for the self-contained LU based solvers
(``HAVE_LAPACK=0``), which upstream documents as a fully supported mode.
"""

import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
)


class LevmarConan(ConanFile):
    name = "levmar"
    version = "2.6"
    description = "Levenberg-Marquardt non-linear least squares solver"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ics.forth.gr/~lourakis/levmar/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 2.6); CMake 4.x
        # removed the compatibility path below 3.5 and aborts configuration.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # No LAPACK/BLAS in the OHOS sysroot: use the self-contained LU solvers
        # instead of linking against a hard coded host /usr/lib.
        tc.cache_variables["HAVE_LAPACK"] = "0"
        tc.cache_variables["NEED_F2C"] = "0"
        # Needed for the upstream example smoke test run below.
        tc.cache_variables["BUILD_DEMO"] = "ON"
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_upstream_demo()

    def _run_upstream_demo(self):
        """Run the upstream example program and assert that it converges.

        ``lmdemo`` is the only executable upstream ships.  It always returns 0
        and prints the optimiser result, so the convergence contract has to be
        checked on its output (Meyer's problem, the default problem).
        """
        demo = os.path.join(self.build_folder, "lmdemo")
        log_path = os.path.join(self.build_folder, "lmdemo.log")
        self.run('"%s" > "%s" 2>&1' % (demo, log_path), env="conanbuild")
        log = load(self, log_path)
        summary = re.search(
            r"Levenberg-Marquardt returned (\d+) in ([\d.eE+-]+) iter, reason ([\d.eE+-]+)",
            log,
        )
        if not summary:
            raise ConanException("upstream lmdemo produced no result:\n" + log[-800:])
        iterations = int(summary.group(1))
        reason = float(summary.group(3))
        if iterations <= 0 or reason not in (1.0, 2.0, 3.0, 4.0):
            raise ConanException(
                "upstream lmdemo did not converge (iterations=%d reason=%g):\n%s"
                % (iterations, reason, log[-800:])
            )
        solution = re.search(r"Solution: ([^\n]+)", log)
        if not solution:
            raise ConanException("upstream lmdemo printed no solution:\n" + log[-800:])
        p = [float(value) for value in solution.group(1).split()]
        if len(p) < 3 or abs(p[0] - 2.4818) > 0.02 or abs(p[1] - 6.1813) > 0.02:
            raise ConanException(
                "upstream lmdemo converged to an unexpected minimum: %s" % p
            )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # levmar.h is produced by configure_file() into the source folder, so
        # the generated header (not the levmar.h.in template) is what consumers
        # must get.
        copy(
            self,
            "levmar.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "liblevmar.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["levmar"]
        self.cpp_info.set_property("cmake_file_name", "levmar")
        self.cpp_info.set_property("cmake_target_name", "levmar::levmar")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
