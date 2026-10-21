#!/usr/bin/env python3
"""Conan test_package for freecell-solver 6.16.0.

Consumer-side verification (real API usage, no stubs):

  * test.c links the CMakeDeps-generated ``freecell-solver::freecell-solver``
    target and drives the public solver API on Microsoft deal #24
    (alloc, version, preset handling, game parameters, solve, move replay,
    solved-foundations state string).  Its 13 per-case TEST PASS/FAIL
    lines and TEST SUMMARY exit code are the package's consumer tests.
  * conanfile.py additionally checks the installed-package contract that
    C/C++ consumers rely on: fcs_user.h, libfreecell-solver.pc and the
    -lfreecell-solver link line from the upstream CMake install.

OHOS: the same Platform/HarmonyOS.cmake shim as the main recipe (CMake
4.1 has no HarmonyOS platform module) and a $ORIGIN-free consumer binary;
the runtime loader path comes from VirtualRunEnv (conanrun).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import save


class FreecellSolverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            platform_modules = os.path.join(self.build_folder, "_cmake_modules")
            save(
                self,
                os.path.join(platform_modules, "Platform", "HarmonyOS.cmake"),
                "include(Platform/Linux)\n",
            )
            tc.variables["CMAKE_MODULE_PATH"] = ";".join(
                (platform_modules, self.generators_folder)
            )
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
        # Resolve the library through LD_LIBRARY_PATH (conanrun) instead of
        # baking a conan-cache RPATH into the consumer binary.
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()

    def build(self):
        # E132: the OHOS SDK lld needs the libxml2 shipped in the SDK's
        # llvm/lib directory; prepend it for CMake's TryCompile.
        env = Environment()
        for sdk_llvm_lib in sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )
        ):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self) or self.conf.get(
            "tools.build:skip_test", default=False
        ):
            self.output.info(
                "NOT_RUN FREECELL_SOLVER_CONSUMER_TESTS=0/13 "
                "reason=cross_building_or_skip_test"
            )
            return

        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_freecell_solver"
        )
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
        self._check_installed_contract()

    def _check_installed_contract(self):
        package_folder = self.dependencies["freecell-solver"].package_folder
        header = os.path.join(
            package_folder, "include", "freecell-solver", "fcs_user.h"
        )
        if not os.path.isfile(header):
            raise ConanInvalidConfiguration(
                f"installed public header is missing: {header}"
            )

        pc_file = os.path.join(
            package_folder, "lib", "pkgconfig", "libfreecell-solver.pc"
        )
        if not os.path.isfile(pc_file):
            raise ConanInvalidConfiguration(
                f"installed pkg-config file is missing: {pc_file}"
            )
        with open(pc_file, encoding="utf-8") as stream:
            pc_content = stream.read()
        if "-lfreecell-solver" not in pc_content:
            raise ConanInvalidConfiguration(
                "libfreecell-solver.pc does not link -lfreecell-solver"
            )
        self.output.info("FREECELL_SOLVER_INSTALLED_CONTRACT=3/3")
