#!/usr/bin/env python3
"""Conan recipe — ffmpeg2theora 0.30 (SCons + pkg-config build system).

ffmpeg2theora is a command-line tool that converts media files to Ogg Theora/Ogg Vorbis.
Build system: SCons (Python-based), discovers dependencies via pkg-config.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class Ffmpeg2TheoraConan(ConanFile):
    name = "ffmpeg2theora"
    version = "0.30"
    description = "ffmpeg2theora — converts various media formats to Ogg Theora/Ogg Vorbis"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.xiph.org/xiph/ffmpeg2theora"
    url = "https://gitlab.xiph.org/xiph/ffmpeg2theora"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ffmpeg/4.4.8")
        self.requires("libtheora/1.1.1")
        self.requires("libvorbis/1.3.7")
        self.requires("libogg/1.3.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate .pc files for all conan dependencies
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

        # Set up build environment (R33: compiler paths from conan conf, not shell vars)
        env = Environment()
        env.define("CC", self._cc())
        env.define("CXX", self._cxx())
        env.define("SHELL", "/system/bin/sh")
        env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # SCons reads CC/CXX from environment (set by generate() above)
        # and discovers all libs via pkg-config (PkgConfigDeps .pc files)
        self.run("scons prefix=${PACKAGE_FOLDER}", env="conanbuild")

    def package(self):
        # Install the binary
        copy(self, "ffmpeg2theora", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "ffmpeg2theora.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _cc(self):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return exes.get("c") or "clang"

    def _cxx(self):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return exes.get("cpp") or "clang++"
