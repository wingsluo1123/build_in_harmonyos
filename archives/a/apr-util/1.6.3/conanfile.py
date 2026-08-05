#!/usr/bin/env python3
"""Conan recipe — apr-util 1.6.3 (Apache Portable Runtime Utilities).

Autotools-based library depending on apr and expat.
Patches fix HarmonyOS platform detection (config.guess/config.sub)
and HMDFS umask permission issue (E011).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AprUtilConan(ConanFile):
    name = "apr-util"
    version = "1.6.3"
    description = "Apache Portable Runtime Utility Library"
    license = "Apache-2.0"
    homepage = "https://apr.apache.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("apr/1.7.6")
        self.requires("expat/2.8.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        apr = self.dependencies["apr"]
        expat = self.dependencies["expat"]
        tc.configure_args.append(f"--with-apr={apr.package_folder}")
        tc.configure_args.append(f"--with-expat={expat.package_folder}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E011: Fix umask 077 -> 000 for HMDFS permission
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 000")
        with open(configure_path, "w") as f:
            f.write(content)

        autotools = Autotools(self)
        autotools.configure()

        # Fix: configure fails to copy apr_rules.mk and references wrong
        # paths because apr-1-config returns '/' as prefix (conan build
        # uses --prefix=/). Copy files and fix paths in Makefile/rules.mk.
        apr = self.dependencies["apr"]
        apr_pkg = apr.package_folder
        apr_build = os.path.join(apr_pkg, "build-1")

        # Copy rules.mk from apr package
        rules_dst = os.path.join(os.getcwd(), "build", "rules.mk")
        os.makedirs(os.path.dirname(rules_dst), exist_ok=True)
        shutil.copy2(os.path.join(apr_build, "apr_rules.mk"), rules_dst)

        # Fix libtool path in rules.mk (//build-1 -> real path)
        with open(rules_dst, "r") as f:
            rules = f.read()
        rules = rules.replace("//build-1", apr_build)
        with open(rules_dst, "w") as f:
            f.write(rules)

        # Also fix Makefile if it references //build-1 or //lib
        makefile = os.path.join(os.getcwd(), "Makefile")
        if os.path.exists(makefile):
            with open(makefile, "r") as f:
                mk = f.read()
            mk = mk.replace("//build-1", apr_build)
            mk = mk.replace("//lib", os.path.join(apr_pkg, "lib"))
            mk = mk.replace("//include", os.path.join(apr_pkg, "include"))
            with open(makefile, "w") as f:
                f.write(mk)

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["aprutil-1"]
        self.cpp_info.set_property("cmake_file_name", "apu")
        self.cpp_info.set_property("cmake_target_name", "apu::apu")
        self.cpp_info.set_property("pkg_config_name", "apr-util-1")
