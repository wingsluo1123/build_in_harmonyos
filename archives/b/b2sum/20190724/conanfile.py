import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class B2SumConan(ConanFile):
    name = "b2sum"
    version = "20190724"
    description = "BLAKE2 hash function reference implementation - b2sum command-line tool"
    license = "MIT"
    homepage = "https://github.com/BLAKE2/BLAKE2"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Build b2sum binary from b2sum/ subdirectory in source folder
        # CC=clang: makefile defaults to CC?=gcc, but only clang is available on OHOS (E001)
        # NO_OPENMP=1: disable OpenMP (-fopenmp not available in OHOS clang)
        b2sum_dir = os.path.join(self.source_folder, "b2sum")
        self.run(f"make -C {b2sum_dir} CC=clang NO_OPENMP=1 -j1")

    def package(self):
        copy(self, "b2sum", os.path.join(self.source_folder, "b2sum"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
