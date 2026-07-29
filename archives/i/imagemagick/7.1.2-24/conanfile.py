#!/usr/bin/env python3
"""Conan recipe for ImageMagick 7.1.2-24."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ImagemagickConan(ConanFile):
    name = "imagemagick"
    version = "7.1.2-24"
    description = "Command-line image processing suite"
    license = "ImageMagick"
    homepage = "https://imagemagick.org/"
    url = "https://github.com/ImageMagick/ImageMagick"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-openmp",
                "--disable-docs",
                "--without-modules",
                "--with-utilities",
                "--without-magick-plus-plus",
                "--without-perl",
                "--without-bzlib",
                "--without-zip",
                "--without-zlib",
                "--without-zstd",
                "--without-autotrace",
                "--without-dps",
                "--without-fftw",
                "--without-flif",
                "--without-fpx",
                "--without-djvu",
                "--without-fontconfig",
                "--without-freetype",
                "--without-raqm",
                "--without-gslib",
                "--without-gvc",
                "--without-dmr",
                "--without-heic",
                "--without-jbig",
                "--without-jpeg",
                "--without-jxl",
                "--without-lcms",
                "--without-openjp2",
                "--without-lqr",
                "--without-lzma",
                "--without-openexr",
                "--without-pango",
                "--without-png",
                "--without-raw",
                "--without-rsvg",
                "--without-tiff",
                "--without-uhdr",
                "--without-webp",
                "--without-wmf",
                "--without-xml",
                "--without-x",
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path("MAGICK_HOME", self.package_folder)
        self.runenv_info.define_path(
            "MAGICK_CONFIGURE_PATH",
            os.path.join(self.package_folder, "etc", "ImageMagick-7"),
        )
