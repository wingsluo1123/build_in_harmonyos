#!/usr/bin/env python3
"""Conan recipe — sidplay-libs 2.1.1 (Autotools).

sidplay-libs bundle: libsidplay2 + libsidutils + resid-builder + hardsid-builder.
These are the runtime libraries required by the sidplay 2.0.9 CLI player.

Official source: SourceForge sidplay2 project (downloads.sourceforge.net).
NOTE: The upstream sidplay2 GitHub mirror (sf-is-evil/sidplay2) only hosts the
sidplay/ CLI subdir; the libs are only distributed as sidplay-libs tarball on
SourceForge, so that official URL is used here.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SidplaylibsConan(ConanFile):
    name = "sidplay-libs"
    version = "2.1.1"
    description = "sidplay-libs 2.1.1 - C64 SID playback libraries (libsidplay2, libsidutils, libresid builders)"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/sidplay2/"
    url = "https://sourceforge.net/projects/sidplay2/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # 顶层 configure 是自定义递归脚本，硬编码相对路径 (cd $pwd/libsidplay)，
        # 仅支持 in-source 构建；将 build 目录设为源码目录
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: static libs avoid polluting system /lib /lib64
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Old (2004-era) C++ sources emit C++11 narrowing warnings treated as errors
        tc.extra_cxxflags.append("-Wno-c++11-narrowing")
        tc.extra_cxxflags.append("-Wno-narrowing")
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
        self.cpp_info.libs = ["sidplay2", "sidutils"]  # link order: sidutils -> sidplay2
        # builder libs are static and not directly linked by consumers by default
        self.cpp_info.builddirs = ["lib/sidplay/builders"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = []