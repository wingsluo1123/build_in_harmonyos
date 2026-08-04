#!/usr/bin/env python3
"""Conan recipe — apr 1.7.6 (Apache Portable Runtime).

Autotools-based library. Patches fix HarmonyOS platform detection
(config.guess/config.sub) and HMDFS umask permission issue (E011).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AprConan(ConanFile):
    name = "apr"
    version = "1.7.6"
    description = "Apache Portable Runtime Library"
    license = "Apache-2.0"
    homepage = "https://apr.apache.org/"

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
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["apr-1"]
        self.cpp_info.set_property("cmake_file_name", "APR")
        self.cpp_info.set_property("cmake_target_name", "APR::APR")
        self.cpp_info.set_property("pkg_config_name", "apr-1")
