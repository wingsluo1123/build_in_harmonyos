#!/usr/bin/env python3
"""Conan recipe for zix 0.8.1-git — Meson build system.

Zix is a lightweight C library providing common data structures and utilities
(B-tree, ring buffer, semaphores, filesystem operations, etc.) used by the
LV2 audio plugin ecosystem.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ZixConan(ConanFile):
    name = "zix"
    version = "0.8.1-git"
    description = "Lightweight C library of portability wrappers and data structures"
    license = "ISC"
    homepage = "https://drobilla.net/software/zix"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"zix is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # OHOS: meson cannot find llvm-ar via PATH, inject into native file
        native_file = self.generators_folder + "/conan_meson_native.ini"
        with open(native_file) as f:
            content = f.read()
        old_content = content
        content = content.replace(
            "[binaries]\nc =",
            "[binaries]\nar = '/data/service/hnp/bin/ar'\nc ="
        )
        if content == old_content:
            raise RuntimeError(
                "Failed to inject ar into meson native file "
                "(pattern '[binaries]\\nc =' not found)"
            )
        with open(native_file, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["zix-0"]
        self.cpp_info.includedirs = ["include/zix-0"]
        self.cpp_info.set_property("cmake_file_name", "zix")
        self.cpp_info.set_property("pkg_config_name", "zix-0")
