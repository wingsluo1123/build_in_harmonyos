#!/usr/bin/env python3
"""Conan recipe for vips 8.17.3 — Meson build system.

vips is a high-performance image processing library.
System dependencies (glib, pcre2, libffi, libjpeg, libwebp, lcms2, expat, zlib)
are pre-installed via cmd-pkgs on OHOS.
"""
import os
import shutil
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
    url = "https://github.com/libvips/libvips"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"

    options = {"shared": [True, False]}
    default_options = {"shared": True}

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
                    self.output.warning("Download failed: {}".format(url))
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
            # Use $ORIGIN-relative RPATH for portability
            "build.rpath": "$ORIGIN/../lib",
        })
        tc.generate()

        # Patch meson native file: add ar binary, fix pkg_config_path,
        # and add -Wl,-rpath for clean install RUNPATH
        native_ini = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_ini):
            # Find llvm-ar: check PATH first, then derive from compiler dir
            ar_path = shutil.which("llvm-ar")
            if not ar_path:
                cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "")
                if cc and os.path.isfile(cc):
                    candidate = os.path.join(os.path.dirname(cc), "llvm-ar")
                    if os.path.isfile(candidate):
                        ar_path = candidate
                if not ar_path:
                    ar_path = "llvm-ar"
            # Find system pkgconfig: check user home, then standard paths
            home_pc = os.path.join(os.path.expanduser("~"), "usr", "local", "lib", "pkgconfig")
            sys_pc = home_pc if os.path.isdir(home_pc) else "/usr/local/lib/pkgconfig"
            rpath_flag = "-Wl,-rpath,$ORIGIN/../lib"
            # Extra link flags for static transitive deps not in pkg-config
            home_lib = os.path.join(os.path.expanduser("~"), "usr", "local", "lib")
            extra_flags = []
            if os.path.isdir(home_lib):
                extra_flags.append("-L{}".format(home_lib))
            for lib in ("libintl", "libsharpyuv"):
                static_lib = os.path.join(home_lib, lib + ".a")
                if os.path.isfile(static_lib):
                    extra_flags.append(static_lib)
                elif any(os.path.isfile(os.path.join(home_lib, lib + ext))
                         for ext in (".a", ".so")):
                    extra_flags.append("-l{}".format(lib[3:]))
            all_flags = [rpath_flag] + extra_flags
            flags_str = ", ".join("'{}'".format(f) for f in all_flags)
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
                # Add rpath and extra link flags to C link args
                elif line.strip().startswith("c_link_args ="):
                    stripped = line.rstrip()
                    if stripped.endswith("[]"):
                        out.append(stripped[:-1] + flags_str + "]\n")
                    else:
                        out.append(stripped.rstrip("]") + ", " + flags_str + "]\n")
                # Add rpath and extra link flags to C++ link args
                elif line.strip().startswith("cpp_link_args ="):
                    stripped = line.rstrip()
                    if stripped.endswith("[]"):
                        out.append(stripped[:-1] + flags_str + "]\n")
                    else:
                        out.append(stripped.rstrip("]") + ", " + flags_str + "]\n")
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

        # Fix absolute paths in DT_NEEDED entries (E050 workaround).
        # pkg-config .pc files embed absolute libdir paths, causing meson to
        # emit DT_NEEDED with absolute paths like /storage/.../libexpat.so.
        # Replace them with bare library names for portability.
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for fname in os.listdir(lib_dir):
                if not fname.startswith("libvips") or not ".so" in fname:
                    continue
                lib_path = os.path.join(lib_dir, fname)
                if os.path.islink(lib_path):
                    continue
                # Read current NEEDED entries and fix absolute paths
                try:
                    result = self.run(
                        'patchelf --print-needed "{}"'.format(lib_path),
                        capture=True,
                    )
                    for needed in result.stdout.strip().splitlines():
                        needed = needed.strip()
                        if needed.startswith("/"):
                            bare = os.path.basename(needed)
                            self.output.info(
                                "Fixing NEEDED: {} -> {}".format(needed, bare)
                            )
                            self.run(
                                'patchelf --replace-needed "{}" "{}" "{}"'.format(
                                    needed, bare, lib_path
                                )
                            )
                except Exception as e:
                    raise Exception(
                        "patchelf failed on {}: {}. "
                        "This will leave absolute DT_NEEDED paths, "
                        "making the library non-portable.".format(fname, e)
                    )

    def package_info(self):
        self.cpp_info.libs = ["vips"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "vips")

    @staticmethod
    def _verify_sha256(filepath, expected):
        if not expected:
            raise Exception("sha256 not set in conandata.yml")
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest() == expected
