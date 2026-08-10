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
        mpi_root = openmpi.package_folder
        tc.cache_variables["GKLIB_PATH"] = os.path.join(self.source_folder, "metis", "GKlib")
        tc.cache_variables["METIS_PATH"] = os.path.join(self.source_folder, "metis")
        # CMake 2.8 compatibility with modern CMake
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["SHARED"] = self.options.shared
        # MPI: don't use mpicc wrapper — it needs OPAL_PREFIX which open-mpi
        # only sets in runenv_info (not buildenv_info). Instead, use the
        # default clang compiler and pass MPI paths via cache variables that
        # the upstream CMakeLists.txt already respects:
        #   include_directories(${MPI_INCLUDE_PATH})     — root CMakeLists.txt
        #   target_link_libraries(... ${MPI_LIBRARIES})  — libparmetis/CMakeLists.txt
        tc.cache_variables["MPI_INCLUDE_PATH"] = os.path.join(mpi_root, "include")
        tc.cache_variables["MPI_LIBRARIES"] = "mpi"
        tc.cache_variables["MPI_LINK_FLAGS"] = f'-L{os.path.join(mpi_root, "lib")}'
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
