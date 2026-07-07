#!/usr/bin/env python3
"""Conan recipe — libqalculate 5.11.0 (Autotools).

A multi-purpose desktop calculator library.
Provides arbitrary precision arithmetic, symbolic calculation,
unit conversion, and plotting support.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibqalculateConan(ConanFile):
    name = "libqalculate"
    version = "5.11.0"
    description = "A multi-purpose desktop calculator library with arbitrary precision"
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # System dependencies (pre-installed via cmd-pkgs, not Conan)
    # gmp 6.3.0, mpfr 4.2.1, readline 8.2, libxml2 2.15.3

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Try downloading from the URL in conandata.yml; if that fails
        # (e.g., network-restricted environment), fall back to a local copy.
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            local = os.path.expanduser("~/libqalculate-5.11.0.tar.gz")
            if os.path.exists(local):
                get(self, "file://" + local,
                    sha256=self.conan_data["sources"]["sha256"],
                    strip_root=True)
            else:
                raise

    def generate(self):
        # Environment variables for OHOS compatibility and system dependency lookup.
        # CONFIG_SHELL and SHELL are also set by the conan profile [buildenv],
        # but we set them here as well for robustness.
        sys_prefix = os.path.expanduser("~/usr/local")
        env = Environment()
        env.define("CONFIG_SHELL", "/usr/bin/sh")
        env.define("SHELL", "/usr/bin/sh")
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("PKG_CONFIG_PATH", f"{sys_prefix}/lib/pkgconfig")
        env.define("LDFLAGS", f"-L{sys_prefix}/lib")
        env.define("CPPFLAGS", f"-I{sys_prefix}/include")
        env.define("LD_LIBRARY_PATH", f"{sys_prefix}/lib")
        env.vars(self).save_script("sysdeps_env")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-libcurl")
        tc.configure_args.append("--without-icu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["qalculate"]
        self.cpp_info.system_libs = ["gmp", "mpfr", "readline", "xml2"]
