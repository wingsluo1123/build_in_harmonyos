#!/usr/bin/env python3
"""Conan recipe — xz 5.6.2.1 (Autotools static liblzma build)."""

import stat
from pathlib import Path

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XzConan(ConanFile):
    name = "xz"
    version = "5.6.2.1"
    package_type = "library"
    description = "XZ Utils with a statically linked liblzma for OpenHarmony"
    license = "0BSD"
    homepage = "https://tukaani.org/xz/"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        wrapper_dir = Path(self.build_folder) / ".ohos-tools"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        mktemp_wrapper = wrapper_dir / "mktemp"
        mktemp_wrapper.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        mktemp_wrapper.chmod(mktemp_wrapper.stat().st_mode | stat.S_IEXEC)

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend([
            "--disable-scripts",
            "--enable-static",
            "--disable-shared",
        ])
        toolchain.generate()

        build_env = Environment()
        build_env.prepend_path("PATH", str(wrapper_dir))
        build_env.vars(self).save_script("conanbuild")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lzma"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "xz")
        self.cpp_info.set_property("cmake_target_name", "xz::xz")
