#!/usr/bin/env python3
"""Conan recipe for ParMETIS 4.0.3 — parallel graph partitioning library.

ParMETIS is the parallel extension of METIS, requiring MPI for inter-process
communication. This recipe bundles METIS and GKlib from the upstream source
tree (no external METIS dependency).

R32: settings.os check uses `in ("Linux", "OHOS")`
R33: build() does not depend on undefined shell environment variables
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class ParmetisConan(ConanFile):
    name = "parmetis"
    version = "4.0.3"
    description = "ParMETIS - Parallel Graph Partitioning and Fill-reducing Matrix Ordering"
    license = "University of Minnesota (free for research/education)"
    homepage = "https://karypis.github.io/glaros/software/parmetis/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("open-mpi/5.0.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        openmpi = self.dependencies["open-mpi"]
        mpi_bin = os.path.join(openmpi.package_folder, "bin")
        # Use mpicc from open-mpi as compiler (upstream design:
        # CMakeLists.txt has FindMPI commented out, relies on mpicc
        # wrapper to inject MPI include/lib flags automatically)
        tc.cache_variables["CMAKE_C_COMPILER"] = os.path.join(mpi_bin, "mpicc")
        tc.cache_variables["GKLIB_PATH"] = os.path.join(self.source_folder, "metis", "GKlib")
        tc.cache_variables["METIS_PATH"] = os.path.join(self.source_folder, "metis")
        # CMake 2.8 compatibility with modern CMake
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["SHARED"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["parmetis", "metis"]
        # parmetis.h includes <metis.h> — metis headers are installed alongside
        self.cpp_info.includedirs = ["include"]
        # Programs (ptest, pometis, parmetis, etc.) declared in commands.json
