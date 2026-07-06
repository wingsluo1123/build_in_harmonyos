import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BchunkConan(ConanFile):
    name = "bchunk"
    version = "1.2.2"
    description = "BinChunker - converts CD images in .cue/.bin format to .iso and .cdr"
    license = "MIT"
    homepage = "http://he.fi/bchunk/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("make -j1 CC=clang LD=clang", cwd=self.source_folder)

    def package(self):
        copy(self, "bchunk", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
