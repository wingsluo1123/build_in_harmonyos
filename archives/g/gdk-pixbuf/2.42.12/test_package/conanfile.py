#!/usr/bin/env python3
"""Conan test_package for gdk-pixbuf 2.42.12."""
import os
from conan import ConanFile
from conan.tools.cmake import cmake_layout


class GdkpixbufTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("glib/2.84.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        gen = self.generators_folder
        inc_flags = []
        lib_flags = []
        for ref, dep in self.dependencies.items():
            if dep.package_folder:
                for incdir in ["include", "include/glib-2.0", "lib/glib-2.0/include", "include/gdk-pixbuf-2.0", "include/libpng16"]:
                    d = os.path.join(dep.package_folder, incdir)
                    if os.path.isdir(d):
                        inc_flags.append("-I" + d)
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    lib_flags.append("-L" + libdir)
        with open(os.path.join(gen, "test_flags.txt"), "w") as f:
            f.write("INC=" + " ".join(inc_flags) + "\n")
            f.write("LIB=" + " ".join(lib_flags) + "\n")

    def build(self):
        gen = self.generators_folder
        inc = ""
        lib = ""
        with open(os.path.join(gen, "test_flags.txt")) as f:
            for line in f:
                if line.startswith("INC="):
                    inc = line.split("=", 1)[1].strip()
                elif line.startswith("LIB="):
                    lib = line.split("=", 1)[1].strip()
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c", "clang")
        src = os.path.join(self.source_folder, "test.c")
        libs = "-lgdk_pixbuf-2.0 -lgobject-2.0 -lgio-2.0 -lglib-2.0 -lgmodule-2.0 -lffi -lpcre2-8 -ljpeg -lpng -lz -lm -lpthread -lrt -ldl -L/lib -l:ld-musl-aarch64.so.1"
        self.run(cc + " " + inc + " " + src + " " + lib + " " + libs + " -o test_gdk-pixbuf", env="conanrun")

    def test(self):
        so_path = None
        for ref, dep in self.dependencies.items():
            if str(ref).startswith("gdk-pixbuf") and dep.package_folder:
                for name in ["libgdk_pixbuf-2.0.so", "libgdk_pixbuf-2.0.so.0"]:
                    p = os.path.join(dep.package_folder, "lib", name)
                    if os.path.isfile(p):
                        so_path = p
                        break
        if not so_path:
            raise Exception("gdk-pixbuf .so not found in package")
        self.run("readelf -s " + so_path + " | grep gdk_pixbuf_new", env="conanrun")
