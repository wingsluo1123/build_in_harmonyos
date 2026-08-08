#!/usr/bin/env python3
"""Conan recipe for rtorrent 0.16.2 — BitTorrent client (rakshasa).

rtorrent is a ncurses-based BitTorrent client. It depends on
libtorrent-rakshasa, ncurses, openssl, zlib, and curl.

Build system: autotools, but configure/config.status has shell
compatibility issues on HarmonyOS (print command and mktemp).
This recipe uses a custom build method that compiles sources directly.
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches


class RtorrentConan(ConanFile):
    name = "rtorrent"
    version = "0.16.2"
    description = "Ncurses based BitTorrent client (rakshasa)"
    license = "GPL-2.0"
    homepage = "https://github.com/rakshasa/rtorrent"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libtorrent-rakshasa/0.16.2")
        self.requires("ncurses/6.6")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")
        self.requires("curl/8.15.0")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder

        # Collect dependency flags
        cflags = []
        lflags = []
        libs = []

        for dep_name, dep in self.dependencies.items():
            for inc in dep.cpp_info.includedirs:
                cflags.append(f"-I{inc}")
            for libdir in dep.cpp_info.libdirs:
                lflags.append(f"-L{libdir}")
            for lib in dep.cpp_info.libs:
                libs.append(f"-l{lib}")
            for lib in dep.cpp_info.system_libs:
                libs.append(f"-l{lib}")

        cxx = "clang++"
        cxxflags = cflags + [
            "-std=c++17", "-fPIC", "-O2", "-pthread",
            "-DDEBUG", "-Wall", "-fvisibility=hidden",
            "-DHAVE_CONFIG_H",
            "-I.", "-Isrc",
        ]

        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)

        src_files = sorted(
            glob.glob(os.path.join(src, "src", "**", "*.cc"), recursive=True)
        )

        obj_files = []
        for sf in src_files:
            rel = os.path.relpath(sf, src)
            obj_name = rel.replace(os.sep, "_").replace(".cc", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            cmd = f"{cxx} {' '.join(cxxflags)} -c {sf} -o {obj_path}"
            self.run(cmd)
            obj_files.append(obj_path)

        bin_path = os.path.join(self.build_folder, "rtorrent")
        link_flags = lflags + libs + ["-lz", "-lpthread", "-ldl"]
        link_cmd = f"{cxx} -std=c++17 -O2 -pthread {' '.join(obj_files)} {' '.join(link_flags)} -o {bin_path}"
        self.run(link_cmd)

    def package(self):
        copy(self, "rtorrent", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
