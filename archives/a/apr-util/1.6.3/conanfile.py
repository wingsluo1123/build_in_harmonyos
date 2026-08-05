#!/usr/bin/env python3
"""Conan recipe — Apache Portable Runtime Utility (APR-Util) 1.6.3.

Build system: autotools (configure + make).
License: Apache-2.0
Homepage: https://apr.apache.org/

Dependencies: apr/1.7.6, expat/2.8.2.1
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AprUtilConan(ConanFile):
    name = "apr-util"
    version = "1.6.3"
    description = "Apache Portable Runtime Utility — companion library to APR providing additional utility interfaces"
    license = "Apache-2.0"
    homepage = "https://apr.apache.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("apr/1.7.6")
        self.requires("expat/2.8.2.1")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Point to APR package — configure uses apr-1-config to find APR
        apr = self.dependencies["apr"]
        tc.configure_args.append(f"--with-apr={apr.package_folder}")

        # Point to expat package
        expat = self.dependencies["expat"]
        expat_prefix = expat.package_folder
        tc.configure_args.append(f"--with-expat={expat_prefix}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()

        # Fix //build-1 paths: apr-1-config returns //build-1 due to --prefix=/
        apr_prefix = self.dependencies["apr"].package_folder
        correct_builddir = os.path.join(apr_prefix, "build-1")
        for fname in ["Makefile", os.path.join("build", "rules.mk")]:
            fpath = os.path.join(self.build_folder, fname)
            if os.path.exists(fpath):
                content = load(self, fpath)
                content = content.replace("//build-1", correct_builddir)
                save(self, fpath, content)

        # Also fix //lib, //include, //bin paths from apr-1-config
        for fname in ["Makefile", os.path.join("build", "rules.mk")]:
            fpath = os.path.join(self.build_folder, fname)
            if os.path.exists(fpath):
                content = load(self, fpath)
                content = content.replace("//lib", os.path.join(apr_prefix, "lib"))
                content = content.replace("//include", os.path.join(apr_prefix, "include"))
                content = content.replace("//bin", os.path.join(apr_prefix, "bin"))
                save(self, fpath, content)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/apr-1"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["aprutil-1"]
        self.cpp_info.requires = ["apr::apr-1", "expat::expat"]
        self.cpp_info.set_property("cmake_file_name", "apr-util")
        self.cpp_info.set_property("cmake_target_name", "apr-util::aprutil-1")
        self.cpp_info.set_property("pkg_config_name", "apr-util-1")
