#!/usr/bin/env python3
"""Conan recipe — Apache Portable Runtime Utility (APR-Util) 1.6.3.

Build system: autotools (configure + make).
License: Apache-2.0
Homepage: https://apr.apache.org/

Dependencies: apr/1.7.6, expat/2.7.1
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
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
        self.requires("expat/2.7.1")

    def layout(self):
        basic_layout(self)

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

        # Fix libtool: when --prefix=/ (Conan DESTDIR convention), libtool
        # generates hardcoded library search paths. Fix the generated libtool
        # script to use the correct Conan package paths.
        self._fix_libtool_paths()

        autotools.make(args=["-j1"])

    def _fix_libtool_paths(self):
        """Fix libtool script for HarmonyOS/Conan --prefix=/ convention.

        The generated libtool script has sys_lib_search_path_spec that may
        not include Conan dependency library paths. Prepend our dependency
        paths to ensure the linker can find all required libraries.
        """
        libtool_path = os.path.join(self.source_folder, "libtool")
        if not os.path.exists(libtool_path):
            return

        with open(libtool_path, "r") as f:
            content = f.read()

        # Build the library search path from all dependencies
        lib_paths = []
        for dep_name in ["apr", "expat"]:
            dep = self.dependencies.get(dep_name)
            if dep:
                for libdir in dep.cpp_info.aggregated_components().libdirs:
                    abs_dir = os.path.join(dep.package_folder, str(libdir))
                    if os.path.isdir(abs_dir):
                        lib_paths.append(abs_dir)

        if lib_paths:
            search_path = ":".join(lib_paths)
            # Find the original sys_lib_search_path_spec value and prepend our paths
            old_pattern = 'sys_lib_search_path_spec="'
            if old_pattern in content:
                idx = content.index(old_pattern) + len(old_pattern)
                # Find the closing quote
                end_idx = content.index('"', idx)
                original_value = content[idx:end_idx]
                new_value = f"{search_path}:{original_value}"
                content = content[:idx] + new_value + content[end_idx:]
                with open(libtool_path, "w") as f:
                    f.write(content)
                self.output.info("Fixed libtool library search paths")

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
