import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Txt2ManConan(ConanFile):
    name = "txt2man"
    version = "1.7.1"
    description = "Convert flat ASCII text to man page format"
    license = "GPL-2.0"
    homepage = "https://github.com/mvertes/txt2man"
    url = "https://github.com/mvertes/txt2man"

    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # txt2man is a shell script tool; make generates man pages by running scripts
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # Copy executables (shell scripts)
        for bin_name in ("txt2man", "src2man", "bookman"):
            copy(self, bin_name, src, os.path.join(self.package_folder, "bin"))
        # Copy man pages
        copy(self, "*.1", src, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
   self.cpp_info.resdirs = ["share"]
