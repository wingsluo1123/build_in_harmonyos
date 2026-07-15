import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Bzip2Conan(ConanFile):
    name = "bzip2"
    version = "1.0.8"
    description = "高压缩比数据压缩工具和库，广泛用于 Linux 生态"
    license = "BSD-4-Clause"
    homepage = "https://sourceware.org/bzip2/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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

        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "llvm-ar")
        ranlib = os.environ.get("RANLIB", "llvm-ranlib")

        self.run(f"make CC={cc} AR={ar} RANLIB={ranlib} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "bzlib.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libbz2.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "bzip2", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["bz2"]
