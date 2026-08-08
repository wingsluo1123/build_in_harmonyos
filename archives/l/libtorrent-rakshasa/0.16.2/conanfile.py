#!/usr/bin/env python3
"""Conan recipe for libtorrent-rakshasa 0.16.2 — BitTorrent library.

libtorrent (rakshasa) is the BitTorrent library used by rtorrent.
It depends on openssl, zlib, and curl.

Build system: autotools, but configure/config.status has shell
compatibility issues on HarmonyOS. This recipe uses a custom
build method that compiles sources directly.
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches


class LibtorrentRakshasaConan(ConanFile):
    name = "libtorrent-rakshasa"
    version = "0.16.2"
    description = "BitTorrent library (rakshasa)"
    license = "GPL-2.0"
    homepage = "https://github.com/rakshasa/libtorrent"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
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
        for dep_name, dep in self.dependencies.items():
            for inc in dep.cpp_info.includedirs:
                cflags.append(f"-I{inc}")

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
            # Skip udns_library.cc for -Isrc/torrent to avoid poll.h conflict
            if "udns_library" in sf:
                cmd = f"{cxx} {' '.join(cflags + ['-std=c++17', '-fPIC', '-O2', '-pthread', '-DDEBUG', '-Wall', '-fvisibility=hidden', '-DHAVE_CONFIG_H', '-I.', '-Isrc'])} -c {sf} -o {obj_path}"
            else:
                cmd = f"{cxx} {' '.join(cxxflags + ['-Isrc/torrent'])} -c {sf} -o {obj_path}"
            self.run(cmd)
            obj_files.append(obj_path)

        # Create static library
        lib_path = os.path.join(self.build_folder, "libtorrent.a")
        ar = "llvm-ar"
        self.run(f"{ar} rcs {lib_path} {' '.join(obj_files)}")

    def package(self):
        copy(self, "libtorrent.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        src = self.source_folder
        # Install headers
        for header in glob.glob(os.path.join(src, "src", "torrent", "**", "*.h"), recursive=True):
            rel = os.path.relpath(header, os.path.join(src, "src"))
            dst = os.path.join(self.package_folder, "include", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            copy(self, os.path.basename(header), src=os.path.dirname(header),
                 dst=os.path.dirname(dst))
        # Install rak headers
        rak_dir = os.path.join(src, "rak")
        if os.path.isdir(rak_dir):
            for header in glob.glob(os.path.join(rak_dir, "*.h")):
                dst = os.path.join(self.package_folder, "include", "torrent", "rak")
                os.makedirs(dst, exist_ok=True)
                copy(self, os.path.basename(header), src=rak_dir, dst=dst)

    def package_info(self):
        self.cpp_info.libs = ["torrent"]
        self.cpp_info.set_property("pkg_config_name", "libtorrent")
