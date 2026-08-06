#!/usr/bin/env python3
"""Conan recipe for opencore-amrnb 0.1.6 — AMR-NB speech codec library.

opencore-amr provides the AMR-NB (Adaptive Multi-Rate Narrowband) speech codec,
derived from the Android OpenCORE project. This recipe builds only the AMR-NB
library (libopencore-amrnb), including both encoder and decoder.

Build system: Autotools (configure + make), uses libtool for library creation.
"""

import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    get, copy, load, save,
    apply_conandata_patches, export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpencoreAmrnbConan(ConanFile):
    name = "opencore-amrnb"
    version = "0.1.6"
    description = "OpenCORE AMR Narrowband speech codec library"
    license = "Apache-2.0"
    homepage = "https://sourceforge.net/projects/opencore-amr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"opencore-amrnb only supports Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R4: static-only build for codec library
        tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # Disable examples (not needed for library package)
        tc.configure_args.append("--disable-examples")
        # Compile as C++ (default uses -x c which conflicts with Conan's
        # CXXFLAGS containing -std=c++17 from the profile's compiler.cppstd).
        tc.configure_args.append("--disable-compile-c")
        # opencore-amr source uses 'register' storage class specifier,
        # which is removed in C++17. Suppress the error.
        tc.extra_cxxflags.append("-Wno-register")
        # R33: compiler/flags come from Conan AutotoolsToolchain, not shell env vars
        if self.settings.os == "OHOS":
            # HarmonyOS: config.guess/config.sub (version 2022-01-09) don't
            # recognize the ohos triplet.  Force a known-good linux-gnu
            # triplet so configure does not abort on triplet validation.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # config.status uses `umask 077 && mktemp -d` to create temp dirs;
        # HMDFS creates these without execute permission, causing awk scripts
        # inside to fail with "Permission denied".  Allow configure to fail,
        # then patch config.status and re-run it.
        try:
            autotools.configure()
        except ConanException:
            cs = os.path.join(self.build_folder, "config.status")
            if not os.path.exists(cs):
                raise
            self.output.info("configure's config.status failed (HMDFS perms), "
                             "patching and re-running")
            self._fix_config_status()
            self.run("bash config.status", cwd=self.build_folder)
        autotools.make(args=["-j1"])

    def _fix_config_status(self):
        """Patch config.status to fix HMDFS temporary directory permissions.

        autoconf's config.status creates temp dirs with `umask 077 && mktemp -d`,
        producing drwx--S--- dirs on HMDFS.  This breaks internal awk scripts.
        Fix: remove `umask 077` and add `chmod 755` after dir creation.
        """
        path = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        original = content
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null',
        )
        if content != original:
            save(self, path, content)
            self.output.info(f"Patched config.status for HMDFS: {path}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # libtool's make install may not copy the .a file to the destdir lib/
        # when only static libraries are built.  Copy manually from .libs/.
        pkg_lib = os.path.join(self.package_folder, "lib")
        build_lib = os.path.join(self.build_folder, "amrnb", ".libs")
        if os.path.isdir(build_lib):
            for name in os.listdir(build_lib):
                if name.endswith(".a"):
                    src = os.path.join(build_lib, name)
                    dst = os.path.join(pkg_lib, name)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        os.makedirs(pkg_lib, exist_ok=True)
                        shutil.copy2(src, dst)
                        self.output.info(f"Packaged static lib: {name}")

        # Remove libtool .la files (not needed in Conan packages)
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

        # Remove pkgconfig files (Conan manages dependencies)
        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(pcdir):
            shutil.rmtree(pcdir, ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = ["opencore-amrnb"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # opencore-amrnb links against libm for math functions
        self.cpp_info.system_libs = ["m"]
        # CMake integration
        self.cpp_info.set_property("cmake_file_name", "opencore-amrnb")
        self.cpp_info.set_property("cmake_target_name", "opencore-amrnb::opencore-amrnb")
        # pkg-config integration
        self.cpp_info.set_property("pkg_config_name", "opencore-amrnb")
