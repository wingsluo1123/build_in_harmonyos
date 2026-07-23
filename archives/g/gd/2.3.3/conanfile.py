#!/usr/bin/env python3
"""Conan recipe — libgd 2.3.3 (GD Graphics Library).

Autotools-based image processing library supporting PNG, JPEG, GIF, WebP, etc.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout


class GdConan(ConanFile):
    name = "gd"
    version = "2.3.3"
    description = "GD graphics library — supports PNG, JPEG, GIF, WebP, etc."
    license = "MIT-like"
    homepage = "https://libgd.github.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("freetype/2.14.3")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libwebp/1.6.0")
        self.requires("fontconfig/2.18.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Force cross-compile mode: build != host → configure skips run-test
        # (conftest links to Conan .so files not in default LD path)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # Generate CFLAGS/LDFLAGS from dependencies
        deps = AutotoolsDeps(self)
        deps.generate()

        # Generate .pc files for dependencies (gd's configure uses PKG_CHECK_MODULES)
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gd"]
        self.cpp_info.set_property("cmake_file_name", "GD")
        self.cpp_info.set_property("cmake_target_name", "gd::gd")
        # gnuplot's configure looks for "gdlib" via pkg-config
        self.cpp_info.set_property("pkg_config_name", "gdlib")
