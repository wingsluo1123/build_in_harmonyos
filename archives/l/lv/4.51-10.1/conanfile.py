#!/usr/bin/env python3
"""Conan recipe — lv 4.51-10.1 (Autotools).

lv is a powerful multi-lingual file viewer/grep tool.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LvConan(ConanFile):
    name = "lv"
    version = "4.51-10.1"
    description = "Powerful multi-lingual file viewer/grep tool"
    license = "GPL-2.0-or-later"
    homepage = "http://www.ff.iij4u.or.jp/~nrt/lv/"
    url = ""  # CI fills this

    package_type = "application"

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
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Configure script is in src/ subdirectory
        src_dir = os.path.join(self.source_folder, "src")
        autotools.configure(build_script_folder=src_dir)
        autotools.make()

    def package(self):
        # Use manual install because make install fails on HMDFS (hardlink)
        # After autotools.build(), binary is in the build-release subfolder
        build_dir = os.path.join(self.build_folder, "build-release") if hasattr(self, 'build_folder') else self.source_folder
        # Try multiple locations for the lv binary
        lv_bin = None
        for candidate in [os.path.join(build_dir, "lv"), os.path.join(self.source_folder, "src", "lv"),
                          os.path.join(self.source_folder, "lv"), os.path.join(self.build_folder, "lv")]:
            if os.path.exists(candidate):
                lv_bin = candidate
                break
        if not lv_bin:
            # Search in build folder
            import glob
            found = glob.glob(os.path.join(self.build_folder, "**", "lv"), recursive=True)
            if found:
                lv_bin = found[0]
        
        root_dir = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib", "lv")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        if lv_bin:
            self.run(f"cp {lv_bin} {bin_dir}/")
        self.run(f"cd {bin_dir} && ln -sf lv lgrep")
        if os.path.exists(os.path.join(root_dir, "lv.hlp")):
            self.run(f"cp {root_dir}/lv.hlp {lib_dir}/")

    def package_info(self):
        self.cpp_info.libs = []
        self.conf_info.define("user.ohpcd:binary", "lv")
