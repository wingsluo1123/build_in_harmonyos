#!/usr/bin/env python3
"""Conan recipe — maim 5.8.0 (CMake, X11 screenshot utility)."""

import os
import platform
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class MaimConan(ConanFile):
    name = "maim"
    version = "5.8.0"
    description = "make image — screenshot utility that captures an X11 desktop region"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/naelstrof/maim"
    url = "https://github.com/naelstrof/maim"
    # Upstream install() ships a single executable (bin/maim) plus its man page;
    # commands.json (software level) declares the CLI entry point.
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 client stack. Pinned to the libx11/libxext 6.4.0 "SONAME" track
        # used by the published libxfixes/libxcomposite/libxrandr recipes.
        # slop/7.7 pins libxext/6.4.0.1 while the other X11 recipes pin
        # libxext/6.4.0; =force converges the graph on the 6.4.0 track (the
        # 6.4.0/6.4.0.1 difference is a patch-level revision, so downstream
        # package_ids and the published slop binary stay valid).
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxrender/0.9.12", transitive_headers=True, transitive_libs=True)
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires(
            "libxcomposite/0.4.6",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxrandr/1.5.5.1", transitive_headers=True, transitive_libs=True)
        # Image encoders used by src/image.cpp.
        self.requires("libpng/1.6.58.3", transitive_headers=True, transitive_libs=True)
        self.requires(
            "libjpeg-turbo/3.2.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libwebp/1.6.0.1", transitive_headers=True, transitive_libs=True)
        # Region selector (src/main.cpp includes <slop.hpp>), math, unicode.
        self.requires("slop/7.7", transitive_headers=True, transitive_libs=True)
        self.requires("glm/1.0.3", transitive_headers=True)
        self.requires("icu/76.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"maim supports Linux and OHOS, not {self.settings.os}"
            )

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        # MAIM_UNICODE drives the CXXOPTS_USE_UNICODE path in src/cxxopts.hpp,
        # which needs the ICU unicode headers/libraries supplied by Conan.
        toolchain.variables["MAIM_UNICODE"] = True
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream v5.8.0 ships no test suite. Running ctest preserves the
        # upstream test entry point and records the empty-suite result.
        self.run(f'ctest --test-dir "{self.build_folder}" --output-on-failure')

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_ohos_binary(os.path.join(self.package_folder, "bin", "maim"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    @staticmethod
    def _sign_ohos_binary(binary):
        """Self-sign the packaged ELF so it is loadable on HarmonyOS."""
        if not os.path.isfile(binary) or platform.system() != "HarmonyOS":
            return
        signer = shutil.which("binary-sign-tool")
        if not signer:
            return
        signed = binary + ".signed"
        result = subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                binary,
                "-outFile",
                signed,
                "-selfSign",
                "1",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0 and os.path.isfile(signed):
            os.replace(signed, binary)
            os.chmod(binary, 0o755)
