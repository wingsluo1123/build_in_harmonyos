#!/usr/bin/env python3
"""Conan recipe for vips 8.17.3 — Meson build system.

vips is a high-performance image processing library.
System dependencies (glib, pcre2, libffi, libjpeg, libwebp, lcms2, expat, zlib)
are pre-installed via cmd-pkgs on OHOS.
"""
import os
import hashlib
import tarfile

from conan import ConanFile, ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches
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
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use curl instead of conan's get() to bypass Python ssl module issues
        # on CI workers where the ssl module is not available (R39).
        src = self.conan_data["sources"]
        url = src["url"]
        expected_sha256 = src.get("sha256", "")
        filename = url.split("/")[-1]
        download_path = os.path.join(self.source_folder, filename)

        need_download = True
        if os.path.exists(download_path):
            if self._verify_sha256(download_path, expected_sha256):
                self.output.info("Source already cached, skipping download")
                need_download = False
            else:
                os.remove(download_path)

        if need_download:
            urls = [
                url,
                url.replace("https://github.com", "https://gitcode.com"),
            ]
            downloaded = False
            for try_url in urls:
                self.output.info(f"Downloading via curl: {try_url}")
                try:
                    self.run(f'curl -fSL -o "{download_path}" "{try_url}"')
                    if os.path.exists(download_path) and self._verify_sha256(download_path, expected_sha256):
                        self.output.info("Download OK")
                        downloaded = True
                        break
                except Exception:
                    self.output.warn(f"Download failed: {try_url}")
                    if os.path.exists(download_path):
                        os.remove(download_path)
            if not downloaded:
                raise ConanException("Failed to download source from all URLs")

        self.output.info(f"Extracting {filename} ...")
        with tarfile.open(download_path, "r:*") as tar:
            tar.extractall(self.source_folder)

        extract_dir = filename.replace(".tar.xz", "").replace(".tar.gz", "").replace(".tar.bz2", "")
        extracted_path = os.path.join(self.source_folder, extract_dir)
        if os.path.isdir(extracted_path):
            for item in os.listdir(extracted_path):
                os.rename(
                    os.path.join(extracted_path, item),
                    os.path.join(self.source_folder, item),
                )
            os.rmdir(extracted_path)

    @staticmethod
    def _verify_sha256(filepath, expected):
        if not expected:
            return True
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest() == expected

    def generate(self):
        tc = MesonToolchain(self)
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
                if line.strip().startswith("cpp ="):
                    out.append(line)
                    out.append("ar = '{}'\n".format(ar_path))
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
