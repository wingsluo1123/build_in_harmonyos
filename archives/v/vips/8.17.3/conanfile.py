#!/usr/bin/env python3
"""Conan recipe for vips 8.17.3 — Meson build system.

vips is a high-performance image processing library.
System dependencies (glib, pcre2, libffi, libjpeg, libwebp, lcms2, expat, zlib)
are pre-installed via cmd-pkgs on OHOS.
"""
import os
import hashlib
import tarfile

from conan import ConanFile
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
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use curl instead of conan's get() to bypass Python ssl module issues
        # on CI workers. Handle both dict and list formats (CI may rewrite
        # conandata.yml to add mirror fallback URLs).
        sources = self.conan_data["sources"]

        # Normalize to list of (url, sha256) pairs
        url_sha_pairs = []
        if isinstance(sources, list):
            for entry in sources:
                url = entry.get("url", "")
                sha = entry.get("sha256", "")
                if isinstance(url, list):
                    for u in url:
                        url_sha_pairs.append((u, sha))
                else:
                    url_sha_pairs.append((url, sha))
        elif isinstance(sources, dict):
            url = sources.get("url", "")
            sha = sources.get("sha256", "")
            if isinstance(url, list):
                for u in url:
                    url_sha_pairs.append((u, sha))
            else:
                url_sha_pairs.append((url, sha))

        if not url_sha_pairs:
            raise Exception("No source URLs found in conandata")

        # Use first URL's sha256 as the expected hash
        expected_sha256 = url_sha_pairs[0][1]
        filename = url_sha_pairs[0][0].split("/")[-1]
        download_path = os.path.join(self.source_folder, filename)

        # Check if already downloaded and valid
        need_download = True
        if os.path.exists(download_path):
            if self._verify_sha256(download_path, expected_sha256):
                self.output.info("Source already cached, skipping download")
                need_download = False
            else:
                os.remove(download_path)

        if need_download:
            downloaded = False
            for url, sha in url_sha_pairs:
                self.output.info("Downloading via curl: {}".format(url))
                try:
                    self.run('curl -fSL -o "{}" "{}"'.format(download_path, url))
                    if os.path.exists(download_path) and self._verify_sha256(download_path, sha):
                        self.output.info("Download OK")
                        downloaded = True
                        break
                except Exception:
                    self.output.warn("Download failed: {}".format(url))
                    if os.path.exists(download_path):
                        os.remove(download_path)
            if not downloaded:
                raise Exception("Failed to download source from all URLs")

        # Extract
        self.output.info("Extracting {} ...".format(filename))
        with tarfile.open(download_path, "r:*") as tar:
            tar.extractall(self.source_folder)

        # Move stripped root dir contents to source_folder
        for ext in (".tar.xz", ".tar.gz", ".tar.bz2", ".tar"):
            if filename.endswith(ext):
                extract_dir = filename[:-len(ext)]
                break
        else:
            extract_dir = filename.rsplit(".", 1)[0] if "." in filename else filename

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
        if not expected or expected == "REPLACE_WITH_ACTUAL_SHA256":
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
