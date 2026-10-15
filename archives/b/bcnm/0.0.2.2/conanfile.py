#!/usr/bin/env python3
"""Conan recipe for bcnm 0.0.2.2 — skarnet.org Better Client Network Manager.

bcnm uses skarnet's own configure + make system (NOT standard autotools).
It depends on skalibs (build-time + run-time). The configure script needs
explicit --with-sysdeps / --with-include / --with-lib pointing to the
skalibs package folder.

This package produces:
  - libbcnm.a         (bcnm_if_* functions: network interface state monitoring)
  - libwpactrl.a      (wpa_supplicant control API)
  - bcnm-waitif       (CLI tool: wait for network interface to reach a state)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class BcnmConan(ConanFile):
    name = "bcnm"
    version = "0.0.2.2"
    description = "skarnet.org bcnm — Better Client Network Manager (libbcnm + libwpactrl + bcnm-waitif)"
    license = "ISC"
    homepage = "https://skarnet.org/software/bcnm/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R26: static build by default (bcnm links statically against skalibs)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("skalibs/2.15.1.0")

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        prefix = self.package_folder

        skalibs = self.dependencies["skalibs"]
        skalibs_prefix = skalibs.package_folder
        skalibs_sysdeps = os.path.join(skalibs_prefix, "lib", "skalibs", "sysdeps")
        skalibs_include = os.path.join(skalibs_prefix, "include")
        skalibs_lib = os.path.join(skalibs_prefix, "lib")

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bcnm does not support os={self.settings.os}"
            )

        configure_cmd = (
            f"cd {src} && ./configure"
            f" --prefix={prefix}"
            f" --disable-shared"
            f" --with-sysdeps={skalibs_sysdeps}"
            f" --with-include={skalibs_include}"
            f" --with-lib={skalibs_lib}"
        )
        self.run(configure_cmd, env="conanbuild")
        self.run(f"cd {src} && make -j1", env="conanbuild")
        # skarnet make install uses rm under the hood which is intercepted by safe-delete
        # on OHOS sandbox. Instead, manually copy build artifacts to package folder.
        import shutil
        # Copy static libraries (built in source dir with .xyzzy suffix)
        for libname in ["libbcnm.a", "libwpactrl.a"]:
            src_lib = os.path.join(src, libname + ".xyzzy")
            dst_lib = os.path.join(self.package_folder, "lib", libname)
            os.makedirs(os.path.dirname(dst_lib), exist_ok=True)
            if os.path.exists(src_lib):
                shutil.copy2(src_lib, dst_lib)
        # Copy bcnm-waitif executable
        waitif_src = os.path.join(src, "bcnm-waitif")
        if os.path.exists(waitif_src):
            dst_bin = os.path.join(self.package_folder, "bin", "bcnm-waitif")
            os.makedirs(os.path.dirname(dst_bin), exist_ok=True)
            shutil.copy2(waitif_src, dst_bin)
        # Copy headers
        include_src = os.path.join(src, "src", "include", "bcnm")
        include_dst = os.path.join(self.package_folder, "include", "bcnm")
        if os.path.isdir(include_src):
            shutil.copytree(include_src, include_dst, dirs_exist_ok=True)

    def package(self):
        pass

    def package_info(self):
        self.cpp_info.libs = ["wpactrl", "bcnm", "skarnet"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
