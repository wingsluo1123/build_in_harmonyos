#!/usr/bin/env python3
"""Conan recipe — trio 1.16 (Autotools, portable printf/sprintf library)

trio 是可移植、可扩展的 printf/sprintf/scanf 替换库 (SourceForge: ctrio)。
构建系统: autotools (configure + make)。源码包已附带预生成的 configure。
产出: libtrio.a (静态) / libtrio.so.2.0.0 (共享) + 头文件 (trio.h, triop.h 等)。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TrioConan(ConanFile):
    name = "trio"
    version = "1.16"
    description = "Portable, extensible printf/sprintf/scanf replacement library"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/ctrio/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        # OHOS 平台只支持静态库，删除 shared 选项
        if self.settings.os == "OHOS":
            self.options.rm_safe("shared")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["trio"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "trio")
        self.cpp_info.set_property("cmake_target_name", "trio::trio")
