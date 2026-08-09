#!/usr/bin/env python3
"""Conan recipe for aria2 1.37.0 — autotools build.

aria2 is a lightweight multi-protocol command-line download utility
supporting HTTP/HTTPS, FTP, BitTorrent, and Metalink.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class Aria2Conan(ConanFile):
    name = "aria2"
    version = "1.37.0"
    description = "Lightweight multi-protocol command-line download tool (HTTP/HTTPS, FTP, BitTorrent, Metalink)"
    license = "GPL-2.0"
    homepage = "https://aria2.github.io"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("c-ares/1.34.6")
        self.requires("expat/2.8.2.1")
        self.requires("zlib/1.3.1.1.1")
        self.requires("sqlite3/3.49.1")
        self.requires("gmp/6.3.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("libuv/1.52.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set CC/CXX for autotools configure (E001: no cc symlink on OHOS)
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        envvars = env.vars(self)
        envvars.save_script("aria2_env")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-libuv")
        tc.configure_args.append("--without-gnutls")
        tc.configure_args.append("--disable-libaria2")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Workaround: libuv conan package generates libuv-static.pc
        # Create libuv.pc so configure's pkg-config can find it
        for gen_dir in [os.path.join(self.generators_folder),
                        os.path.join(self.build_folder, "build-release", "conan")]:
            if os.path.isdir(gen_dir):
                static_pc = os.path.join(gen_dir, "libuv-static.pc")
                libuv_pc = os.path.join(gen_dir, "libuv.pc")
                if os.path.exists(static_pc) and not os.path.exists(libuv_pc):
                    shutil.copy(static_pc, libuv_pc)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
