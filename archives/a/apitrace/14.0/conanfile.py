#!/usr/bin/env python3
"""Conan recipe for apitrace 14.0 — graphics API tracing framework.

apitrace traces OpenGL, Direct3D and other graphics API calls for debugging
and performance analysis. This recipe builds the CLI tools (apitrace, gltrim)
and the EGL trace wrapper (egltrace.so).

Patches:
  0001-CMakeLists.txt:          Add ENABLE_LTO option (disable LTO to fix brotli hidden symbol link errors)
  0002-thirdparty-brotli.cmake: Add missing brotli source files for brotli 1.2.0+
"""
import os
import shutil
import tarfile
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, download
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

# Submodule definitions with fixed tags for reproducible builds.
# Tags correspond to versions compatible with apitrace 14.0.
_SUBMODULES = {
    "brotli":       {"url": "https://github.com/google/brotli",                "dest": "thirdparty/brotli",       "ref": "v1.2.0"},  # v1.2.0+ has prefix.c, static_init.c, static_dict_lut.c
    "gtest":        {"url": "https://github.com/google/googletest",             "dest": "thirdparty/gtest",       "ref": "v1.14.0"},
    "libbacktrace": {"url": "https://github.com/ianlancetaylor/libbacktrace",   "dest": "thirdparty/libbacktrace", "ref": "master"},  # no version tags available
    "libpng":       {"url": "https://github.com/apitrace/libpng",               "dest": "thirdparty/libpng",       "ref": "master"},  # fork, no version tags
    "snappy":       {"url": "https://github.com/google/snappy",                 "dest": "thirdparty/snappy",       "ref": "1.1.10"},
    "zlib":         {"url": "https://github.com/madler/zlib",                   "dest": "thirdparty/zlib",         "ref": "v1.3.1"},
    "zstd":         {"url": "https://github.com/facebook/zstd",                "dest": "thirdparty/zstd",         "ref": "v1.5.5"},
    "directxmath":  {"url": "https://github.com/microsoft/DirectXMath",          "dest": "thirdparty/directxmath",  "ref": "main"},  # no version tags, uses main branch
}

# Mirror prefixes tried in order if GitHub is unreachable
_MIRRORS = ["https://ghfast.top/", "https://gh-proxy.com/", ""]


class ApitraceConan(ConanFile):
    name = "apitrace"
    version = "14.0"
    description = "API call tracing framework for OpenGL, Direct3D and other graphics APIs"
    license = "MIT"
    homepage = "https://github.com/apitrace/apitrace"
    url = "https://github.com/apitrace/apitrace"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def _download_submodule(self, name, base_url, ref, dest):
        """Download a git submodule at a fixed ref, trying mirror prefixes.

        ref can be a tag name (e.g. 'v1.1.0') or a commit SHA (e.g. '9ae436c').
        """
        tmp_dir = tempfile.gettempdir()
        # Try both tag and commit archive URL formats
        for url_path in [f"archive/refs/tags/{ref}.tar.gz", f"archive/{ref}.tar.gz"]:
            for mirror in _MIRRORS:
                archive_url = f"{base_url}/{url_path}"
                full_url = f"{mirror}{archive_url}" if mirror else archive_url
                tmp_file = os.path.join(tmp_dir, f"apitrace_{name}.tar.gz")
                try:
                    download(self, full_url, tmp_file)
                    self.output.info(f"Downloaded {name}@{ref} from {full_url}")
                    with tarfile.open(tmp_file, "r:gz") as tar:
                        members = tar.getmembers()
                        if members:
                            top = os.path.join(tmp_dir, members[0].name.split("/")[0])
                            tar.extractall(tmp_dir)
                            if os.path.exists(dest):
                                shutil.rmtree(dest)
                            shutil.move(top, dest)
                    os.unlink(tmp_file)
                    return True
                except Exception as e:
                    self.output.info(f"Failed {name}@{ref} from {full_url}: {e}")
                    if os.path.exists(tmp_file):
                        os.unlink(tmp_file)
        return False

    def source(self):
        # Download main source (conan get handles mirror lists injected by ohc-run.py)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download required submodules at fixed refs for reproducible builds
        for name, info in _SUBMODULES.items():
            dest = os.path.join(self.source_folder, info["dest"])
            self.output.info(f"Downloading submodule {name}@{info['ref']} -> {dest}")
            if not self._download_submodule(name, info["url"], info["ref"], dest):
                raise RuntimeError(f"Failed to download submodule {name}@{info['ref']}")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_LTO"] = "OFF"
        tc.variables["ENABLE_GUI"] = "OFF"
        tc.variables["ENABLE_CLI"] = "ON"
        tc.variables["ENABLE_X11"] = "OFF"  # OHOS has no X11
        tc.variables["ENABLE_EGL"] = "ON"   # OHOS has EGL
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/apitrace/wrappers"]
