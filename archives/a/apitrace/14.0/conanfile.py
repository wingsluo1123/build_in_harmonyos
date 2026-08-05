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

# Submodule definitions (official GitHub URLs; mirrors handled by ohc-run.py or CI)
_SUBMODULES = {
    "brotli":       {"url": "https://github.com/google/brotli",                "dest": "thirdparty/brotli"},
    "gtest":        {"url": "https://github.com/google/googletest",             "dest": "thirdparty/gtest"},
    "libbacktrace": {"url": "https://github.com/ianlancetaylor/libbacktrace",   "dest": "thirdparty/libbacktrace"},
    "libpng":       {"url": "https://github.com/apitrace/libpng",               "dest": "thirdparty/libpng"},
    "snappy":       {"url": "https://github.com/google/snappy",                 "dest": "thirdparty/snappy"},
    "zlib":         {"url": "https://github.com/madler/zlib",                   "dest": "thirdparty/zlib"},
    "zstd":         {"url": "https://github.com/facebook/zstd",                "dest": "thirdparty/zstd"},
    "directxmath":  {"url": "https://github.com/microsoft/DirectXMath",          "dest": "thirdparty/directxmath"},
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

    def _download_submodule(self, name, base_url, dest):
        """Download a git submodule, trying mirror prefixes."""
        tmp_dir = tempfile.gettempdir()
        for branch in ("master", "main"):
            for mirror in _MIRRORS:
                archive_url = f"{base_url}/archive/refs/heads/{branch}.tar.gz"
                full_url = f"{mirror}{archive_url}" if mirror else archive_url
                tmp_file = os.path.join(tmp_dir, f"apitrace_{name}.tar.gz")
                try:
                    download(self, full_url, tmp_file)
                    self.output.info(f"Downloaded {name} from {full_url}")
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
                    self.output.info(f"Failed {name} from {full_url}: {e}")
                    if os.path.exists(tmp_file):
                        os.unlink(tmp_file)
        return False

    def source(self):
        # Download main source (conan get handles mirror lists injected by ohc-run.py)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download required submodules
        for name, info in _SUBMODULES.items():
            dest = os.path.join(self.source_folder, info["dest"])
            self.output.info(f"Downloading submodule {name} -> {dest}")
            if not self._download_submodule(name, info["url"], dest):
                raise RuntimeError(f"Failed to download submodule {name}")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_LTO"] = "OFF"
        tc.variables["ENABLE_GUI"] = "OFF"
        tc.variables["ENABLE_CLI"] = "ON"
        tc.variables["ENABLE_X11"] = "OFF"  # OHOS has no X11
        tc.variables["ENABLE_EGL"] = "ON"   # OHOS has EGL
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
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
