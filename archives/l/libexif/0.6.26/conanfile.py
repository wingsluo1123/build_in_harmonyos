#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libexif, libexif, 0.6.26, EXIF 元数据处理库，用于读取、写入和编辑图像文件的 EXIF 信息, LGPL-2.1+, https://libexif.github.io
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibexifConan(ConanFile):
    name = "libexif"
    version = "0.6.26"
    description = "EXIF 元数据处理库，用于读取、写入和编辑图像文件的 EXIF 信息"
    license = "LGPL-2.1+"
    homepage = "https://libexif.github.io"


    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Ensure ${HOME}/tmp exists for configure temp files (E002: /tmp is read-only on OHOS)
        import os
        from pathlib import Path
        home_tmp = Path(os.environ.get("HOME", "/tmp")) / "tmp"
        home_tmp.mkdir(parents=True, exist_ok=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["exif"]
