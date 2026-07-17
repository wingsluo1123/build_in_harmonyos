#!/usr/bin/env python3
"""Conan recipe — libedit 20240808 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibeditConan(ConanFile):
    name = "libedit"
    version = "20240808"
    description = "BSD line editing library (editline)"
    license = "BSD-3-Clause"
    homepage = "https://thrysoee.dk/editline/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

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
        # HarmonyOS: use system libtinfo for termcap
        # Create symlink libtinfo.so -> libtinfo.so.6 in build lib dir
        if self.settings.os in ("Linux", "OHOS"):
            lib_dir = os.path.join(self.build_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            tinfo_link = os.path.join(lib_dir, "libtinfo.so")
            if not os.path.exists(tinfo_link):
                os.symlink("/usr/lib/libtinfo.so.6", tinfo_link)
            tc.extra_ldflags.append("-L" + lib_dir)
            tc.extra_cflags.append("-I" + self.source_folder)
            # HarmonyOS: wchar_t stores ISO 10646 but __STDC_ISO_10646__ not defined
            tc.extra_cflags.append("-D__STDC_ISO_10646__=201206L")
        tc.extra_ldflags.append("-L" + lib_dir)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["edit"]
        # HarmonyOS: link system libtinfo
        self.cpp_info.system_libs = ["tinfo"]
