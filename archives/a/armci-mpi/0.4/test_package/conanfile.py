#!/usr/bin/env python3
"""Conan test_package for armci-mpi 0.4.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

The test calls ARMCI API functions (ARMCI_Init, ARMCI_Malloc, ARMCI_Put,
ARMCI_Get, ARMCI_Barrier, ARMCI_Free, ARMCI_Finalize) to verify the
package is usable. It requires running with mpiexec -n 2.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ArmcimpiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicitly require mpich for MPI headers and runtime
        self.requires("mpich/5.0.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Find mpiexec from mpich dependency
        mpiexec = shutil.which("mpiexec")
        if not mpiexec:
            mpich = self.dependencies.get("mpich")
            if mpich:
                candidate = os.path.join(mpich.package_folder, "bin", "mpiexec")
                if os.path.isfile(candidate):
                    mpiexec = candidate

        if mpiexec:
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_armci_mpi")
            self.run(f'"{mpiexec}" -n 2 "{test_bin}"', env="conanrun")
        else:
            cmake = CMake(self)
            cmake.test()
