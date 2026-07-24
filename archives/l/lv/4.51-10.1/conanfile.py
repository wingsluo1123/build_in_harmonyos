#!/usr/bin/env python3
"""Conan recipe — lv 4.51-10.1 (Autotools).

lv is a powerful multi-lingual file viewer/grep tool.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
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
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS 需要显式链接 termcap (ncurses 的 termcap 适配层)
        tc.configure_args.append("LIBS=-ltermcap")
        tc.extra_ldflags.append("-ltermcap")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        src_dir = os.path.join(self.source_folder, "src")
        autotools.configure(build_script_folder=src_dir)
        autotools.make(vars={"LDFLAGS": "${LDFLAGS} -ltermcap"})

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        root_dir = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib", "lv")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        # Find lv binary in build folder
        lv_path = os.path.join(self.build_folder, "lv")
        if not os.path.exists(lv_path):
            lv_path = os.path.join(src_dir, "lv")
        if not os.path.exists(lv_path):
            raise ConanInvalidConfiguration("lv binary not found in build output")
        copy(self, os.path.basename(lv_path), src=os.path.dirname(lv_path), dst=bin_dir)
        os.symlink(os.path.join(bin_dir, "lv"), os.path.join(bin_dir, "lgrep"))
        hlp_src = os.path.join(root_dir, "lv.hlp")
        if os.path.exists(hlp_src):
            copy(self, "lv.hlp", src=root_dir, dst=lib_dir)

    def package_info(self):
        self.cpp_info.libs = []
        self.conf_info.define("user.ohpcd:binary", "lv")
