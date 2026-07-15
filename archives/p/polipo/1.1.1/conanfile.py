from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class PolipoConan(ConanFile):
    name = "polipo"
    version = "1.1.1"
    description = "Polipo is a small, fast caching HTTP proxy"
    license = "MIT"
    homepage = "https://github.com/jech/polipo"
    url = "https://github.com/jech/polipo"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run(f"make -C {self.source_folder} polipo -j1")

    def package(self):
        copy(self, "polipo", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "polipo.man", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "config.sample", self.source_folder, os.path.join(self.package_folder, "share", "polipo"), keep_path=False)
        copy(self, "forbidden.sample", self.source_folder, os.path.join(self.package_folder, "share", "polipo"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
