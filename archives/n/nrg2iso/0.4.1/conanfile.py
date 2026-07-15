import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Nrg2IsoConan(ConanFile):
    name = "nrg2iso"
    version = "0.4.1"
    description = "Command-line tool that converts NERO image files (.nrg) to ISO format (.iso)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/basrach/nrg2iso"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # MacPorts tarball has macOS ._ metadata files in root, breaking strip_root
        get(self, **self.conan_data["sources"])
        # Remove macOS metadata files at root level
        for f in glob.glob(os.path.join(self.source_folder, "._*")):
            os.remove(f)
        # Move contents of nrg2iso-0.4.1/ to source_folder root
        subdir = os.path.join(self.source_folder, "nrg2iso-0.4.1")
        if os.path.isdir(subdir):
            for item in os.listdir(subdir):
                src = os.path.join(subdir, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(subdir)
        # Remove macOS metadata files that were inside the subdirectory
        for f in glob.glob(os.path.join(self.source_folder, "._*")):
            os.remove(f)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan profile conf (dict form)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        copy(self, "nrg2iso", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
