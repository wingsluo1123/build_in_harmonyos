#!/usr/bin/env python3
"""Conan recipe for NTL 11.6.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NtlConan(ConanFile):
    name = "ntl"
    version = "11.6.0"
    description = "High-performance portable C++ number theory library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libntl.org"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("NTL supports Linux and OHOS")

    def requirements(self):
        self.requires("gmp/6.3.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        do_config = os.path.join(self.source_folder, "src", "DoConfig")
        replace_in_file(
            self,
            do_config,
            "if(system(\"$MakeSub{'MAKE_PROG'} GenConfigInfo >> CompilerOutput.log 2>&1\")) { \n",
            "if(system(\"$MakeSub{'MAKE_PROG'} GenConfigInfo >> CompilerOutput.log 2>&1\")) {\n",
        )
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        gmp = self.dependencies["gmp"].package_folder
        executables = self.conf.get("tools.build:compiler_executables", default={})
        ar = executables.get("ar", "llvm-ar")
        ranlib = executables.get("ranlib", "llvm-ranlib")
        configure_args = [
            f'PREFIX="{self.package_folder}"',
            f'GMP_PREFIX="{gmp}"',
            "SHARED=off",
            "NATIVE=off",
            "TUNE=generic",
            "NTL_GF2X_LIB=off",
            "NTL_THREADS=on",
            "NTL_SAFE_VECTORS=on",
            "NTL_STD_CXX11=on",
            "ENABLE_RPATH=off",
            'CXX="$CXX"',
            'CXXFLAGS="$CXXFLAGS"',
            'CPPFLAGS="$CPPFLAGS"',
            'LDFLAGS="$LDFLAGS"',
            f'AR="{ar}"',
            f'RANLIB="{ranlib}"',
        ]
        source_dir = os.path.join(self.source_folder, "src")
        self.run(
            "CONAN_CROSS_BUILDING=1 ./configure " + " ".join(configure_args),
            cwd=source_dir,
            env="conanbuild",
        )
        self.run("make -j1", cwd=source_dir, env="conanbuild")

    def package(self):
        source_dir = os.path.join(self.source_folder, "src")
        self.run("make install", cwd=source_dir, env="conanbuild")
        copy(
            self,
            "copying.txt",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ntl"]
        self.cpp_info.set_property("cmake_file_name", "ntl")
        self.cpp_info.set_property("cmake_target_name", "ntl::ntl")
        self.cpp_info.set_property("pkg_config_name", "ntl")
        self.cpp_info.system_libs = ["m", "pthread"]
