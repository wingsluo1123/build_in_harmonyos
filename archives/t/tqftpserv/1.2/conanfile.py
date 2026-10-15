#!/usr/bin/env python3
"""Conan recipe — tqftpserv 1.2 (Meson).

tqftpserv is a Trivial File Transfer Protocol server over AF_QIPCRTR
(Qualcomm IPC Router). It builds a single executable that depends on
libqrtr (for QRTR socket support) and libzstd (for compressed firmware
support).

OHOS notes:
- systemd not available; systemd-unit-prefix set to empty.
- ar/ranlib must be derived from compiler_executables because OHOS
  toolchain is not on PATH.
- meson.build has a bug where systemd_system_unit_dir is only defined
  when systemd is found; patch 0001-ohos-systemd-init makes it always
  defined (applied via apply_conandata_patches).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class TqftpservConan(ConanFile):
    name = "tqftpserv"
    version = "1.2"
    description = "Trivial File Transfer Protocol server over AF_QIPCRTR"
    license = "BSD-3-Clause"
    homepage = "https://github.com/linux-msm/tqftpserv"
    url = "https://github.com/linux-msm/tqftpserv"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = ["PkgConfigDeps"]

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tqftpserv supports Linux and OHOS only, got %s" % self.settings.os
            )

    def requirements(self):
        self.requires("qrtr/1.2")
        self.requires("zstd/1.5.7")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["systemd-unit-prefix"] = ""
        tc.generate()

        executables = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            cc = str(executables.get("c") or "")
            bindir = os.path.dirname(cc)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if ar and os.path.isfile(native_file):
            with open(native_file) as handle:
                content = handle.read()
            if "\nar =" not in content and "[binaries]" in content:
                insert = "[binaries]\nar = '%s'\n" % ar
                if ranlib:
                    insert += "ranlib = '%s'\n" % ranlib
                content = content.replace("[binaries]\n", insert, 1)
                with open(native_file, "w") as handle:
                    handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        # CI workers are resource-constrained: the default -j20 ninja spawn
        # storm exhausted posix_spawn (EAGAIN) twice in CI (builds #93302,
        # #93316). tqftpserv has only 2 C sources; -j1 is free and robust.
        self.conf.define("tools.build:jobs", 1)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
