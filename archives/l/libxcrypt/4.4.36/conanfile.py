#!/usr/bin/env python3
"""Conan recipe for libxcrypt 4.4.36 using Autotools."""

import os
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibxcryptConan(ConanFile):
    name = "libxcrypt"
    version = "4.4.36"
    package_type = "library"
    description = "Extended crypt library with support for modern password hashing schemes"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/besser82/libxcrypt"
    url = "https://github.com/besser82/libxcrypt"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxcrypt supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
            toolchain.configure_args.append("--disable-static")
        else:
            toolchain.configure_args.append("--disable-shared")
            toolchain.configure_args.append("--enable-static")
        toolchain.generate()

    @staticmethod
    def _verify_writable_directory(path, label):
        os.makedirs(path, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", prefix=".conan-write-test-", dir=path, delete=True
            ) as probe:
                probe.write("conan writable path probe\n")
                probe.flush()
        except OSError as exc:
            raise ConanInvalidConfiguration(
                f"{label} is not writable: {path}: {exc}"
            ) from exc

    def build(self):
        self._verify_writable_directory(self.source_folder, "source folder")
        self._verify_writable_directory(self.build_folder, "build folder")

        # HMDFS may reject Autoconf's restrictive relative temp directory.
        # Keep all configure scratch files in Conan's writable build tree.
        tmpdir = os.path.join(self.build_folder, "_tmp")
        self._verify_writable_directory(tmpdir, "configure temp folder")
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        apply_conandata_patches(self)
        autotools = Autotools(self)
        previous_umask = os.umask(0o022)
        try:
            autotools.configure()
        finally:
            os.umask(previous_umask)
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["crypt"]
        self.cpp_info.set_property("cmake_file_name", "libxcrypt")
        self.cpp_info.set_property("cmake_target_name", "libxcrypt::libxcrypt")
        self.cpp_info.set_property("pkg_config_name", "libcrypt")
