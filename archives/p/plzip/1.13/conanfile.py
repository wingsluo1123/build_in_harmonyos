#!/usr/bin/env python3
"""Conan recipe for plzip - Parallel LZMA compressor using lzlib.

plzip uses a custom configure script (not standard autotools).
The configure script hardcodes CXX=g++ and falls back to c++,
so CXX must be passed as a configure argument, not via environment.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PlzipConan(ConanFile):
    name = "plzip"
    version = "1.13"
    description = "Parallel LZMA compressor using lzlib"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/lzip/plzip.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lzlib/1.15")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # plzip's custom configure hardcodes CXX=g++; pass CXX as configure arg
        compiler_execs = self.conf.get("tools.build:compiler_executables", default={})
        cxx = compiler_execs.get("cpp")
        if cxx:
            tc.configure_args.append(f"CXX={cxx}")
        # Pass lzlib include and lib paths as configure args
        # (custom configure ignores environment CPPFLAGS/LDFLAGS)
        lz = self.dependencies.get("lzlib")
        if lz:
            inc_dirs = lz.cpp_info.includedirs
            lib_dirs = lz.cpp_info.libdirs
            if inc_dirs:
                cppflags = " ".join(["-I" + d for d in inc_dirs])
                tc.configure_args.append("CPPFLAGS=" + cppflags)
            if lib_dirs:
                ldflags = " ".join(["-L" + d for d in lib_dirs])
                tc.configure_args.append("LDFLAGS=" + ldflags)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
