#!/usr/bin/env python3
"""Conan recipe for nibbleandahalf (NibbleAndAHalf) 0.0-git-c3d5edba42.

Fast base64 encode/decode library. Upstream ships a plain Makefile (no
configure) that builds libnaah64.a / libnaah64.so and respects
CC/CFLAGS/LDFLAGS from the environment, so the recipe drives make directly
with the Conan toolchain env (R33: never read bare shell env vars).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NibbleandahalfConan(ConanFile):
    name = "nibbleandahalf"
    version = "0.0-git-c3d5edba42"
    description = "NibbleAndAHalf - fast base64 encoding and decoding library"
    license = "MIT"
    homepage = "https://github.com/superwills/NibbleAndAHalf"
    url = "https://github.com/superwills/NibbleAndAHalf"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported (Linux/OHOS only)"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Upstream tarball keeps the actual sources under a NibbleAndAHalf/
        # subdirectory (repo root also carries .sln/.xcodeproj IDE files).
        # Flatten so the Makefile sits at the source root.
        nested = os.path.join(self.source_folder, "NibbleAndAHalf")
        if os.path.isdir(nested) and not os.path.isfile(
            os.path.join(self.source_folder, "Makefile")
        ):
            import shutil

            for item in os.listdir(nested):
                shutil.move(os.path.join(nested, item), self.source_folder)
            os.rmdir(nested)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Upstream Makefile target: libnaah64.a / libnaah64.so
        if self.options.shared:
            self.run("make -j1 libnaah64.so", cwd=self.source_folder, env="conanbuild")
        else:
            self.run("make -j1 libnaah64.a", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(
            self,
            "base64.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        if self.options.shared:
            copy(
                self,
                "libnaah64.so",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        else:
            copy(
                self,
                "libnaah64.a",
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["naah64"]