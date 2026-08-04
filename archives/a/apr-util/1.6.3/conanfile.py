#!/usr/bin/env python3
"""Conan recipe — apr-util 1.6.3 (Apache Portable Runtime Utilities).

Autotools-based library depending on apr and expat.
Patches fix HarmonyOS platform detection (config.guess/config.sub)
and HMDFS umask permission issue (E011).
"""
import os

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
        # Create a wrapper directory with bin/apr-1-config that forces
        # the correct prefix. Conan builds apr with --prefix=/ so
        # apr-1-config returns paths based on /. The wrapper overrides
        # the prefix to the actual conan package folder.
        wrapper_dir = os.path.join(self.build_folder, "apr-wrapper")
        bin_dir = os.path.join(wrapper_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "apr-1-config")
        with open(wrapper, "w") as f:
            f.write("#!/bin/sh\n")
            f.write(
                f'exec "{apr.package_folder}/bin/apr-1-config" '
                f'--prefix="{apr.package_folder}" "$@"\n'
            )
        os.chmod(wrapper, 0o755)
        tc.configure_args.append(f"--with-apr={wrapper_dir}")
        tc.configure_args.append(f"--with-expat={expat.package_folder}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix apr_rules.mk in the APR package: it was generated with
        # --prefix=/ so apr_builddir is //build-1 (wrong). Fix it to
        # point to the actual package build-1 directory.
        apr = self.dependencies["apr"]
        rules_mk = os.path.join(apr.package_folder, "build-1", "apr_rules.mk")
        if os.path.isfile(rules_mk):
            with open(rules_mk, "r") as f:
                content = f.read()
            build_1 = os.path.join(apr.package_folder, "build-1")
            content = content.replace(
                "apr_builddir=//build-1",
                f"apr_builddir={build_1}",
            )
            content = content.replace(
                "apr_builders=//build-1",
                f"apr_builders={build_1}",
            )
            with open(rules_mk, "w") as f:
                f.write(content)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["aprutil-1"]
        self.cpp_info.set_property("cmake_file_name", "apu")
        self.cpp_info.set_property("cmake_target_name", "apu::apu")
        self.cpp_info.set_property("pkg_config_name", "apr-util-1")
