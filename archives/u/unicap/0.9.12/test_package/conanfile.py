import os

from conan import ConanFile
from conan.tools.build import can_run


class UnicapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["unicap"].package_folder
        glib = self.dependencies["glib"].package_folder
        cxx = os.environ.get("CXX", "clang++")
        src = os.path.join(self.source_folder, "test_unicap.cpp")
        self.run(
            f"{cxx} -std=c++17 -o test_unicap {src} "
            f"-I{pkg}/include -I{glib}/include/glib-2.0 -I{glib}/lib/glib-2.0/include "
            f"-L{pkg}/lib -L{glib}/lib -lunicap -lgobject-2.0 -lglib-2.0",
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            libdirs = ":".join(
                os.path.join(self.dependencies[n].package_folder, "lib")
                for n in ("unicap", "glib")
            )
            bin_path = os.path.join(self.build_folder, "test_unicap")
            self.run(f"LD_LIBRARY_PATH='{libdirs}' {bin_path}", env="conanrun")
