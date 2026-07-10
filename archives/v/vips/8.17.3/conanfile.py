#!/usr/bin/env python3
"""Conan recipe for vips 8.17.3 — Meson build system.

vips is a high-performance image processing library.
System dependencies (glib, pcre2, libffi, libjpeg, libwebp, lcms2, expat, zlib)
are pre-installed via cmd-pkgs on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class VipsConan(ConanFile):
    name = "vips"
    version = "8.17.3"
    description = "High-performance image processing library"
    license = "LGPL-2.1+"
    homepage = "https://libvips.github.io/libvips/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # System dependencies via cmd-pkgs (not in conan remotes):
        # glib-2.0, pcre2, libffi, libjpeg-turbo, libwebp, lcms2
        # Conan-available: expat/2.8.2, zlib/1.3.1
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable features not available on OHOS
        tc.project_options.update({
            "fontconfig": "disabled",
            "pangocairo": "disabled",
            "png": "disabled",
            "spng": "disabled",
            "tiff": "disabled",
            "openexr": "disabled",
            "openjpeg": "disabled",
            "heif": "disabled",
            "pdfium": "disabled",
            "poppler": "disabled",
            "rsvg": "disabled",
            "jpeg-xl": "disabled",
            "magick": "disabled",
            "introspection": "disabled",
            "vapi": "false",
        })
        tc.generate()

        # Patch meson native file: add ar binary and fix pkg_config_path
        native_ini = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_ini):
            sdk_bin = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"
            ar_path = os.path.join(sdk_bin, "llvm-ar")
            sys_pc = "/storage/Users/currentUser/usr/local/lib/pkgconfig"
            with open(native_ini, "r") as f:
                lines = f.readlines()
            out = []
            for line in lines:
                # Add ar after cpp line in [binaries] section
                if line.strip().startswith("cpp ="):
                    out.append(line)
                    out.append("ar = '{}'\n".format(ar_path))
                # Fix pkg_config_path to include system dependencies
                elif "pkg_config_path = '" in line:
                    out.append(line.replace(
                        "pkg_config_path = '",
                        "pkg_config_path = '{}:".format(sys_pc),
                    ))
                else:
                    out.append(line)
            with open(native_ini, "w") as f:
                f.writelines(out)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["vips"]
        self.cpp_info.set_property("pkg_config_name", "vips")
