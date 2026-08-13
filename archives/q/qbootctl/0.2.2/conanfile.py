#!/usr/bin/env python3
"""Conan recipe for qbootctl 0.2.2.

qbootctl is a pure-C CLI tool (Meson) that manages Qualcomm A/B boot
slots: it reads/writes GPT boot attributes, queries /proc/cmdline and
uses UFS BSG ioctls. All of those need root + real hardware.

The production binary (bin/qbootctl) keeps upstream semantics exactly:
no mock code, no runtime switch. meson also builds a separate test-only
target bin/qbootctl-test with -DQBOOTCTL_TESTING, whose backend is a
pure in-memory mock (no device access) used exclusively by test_package
(see patches/0001-meson.build.patch + 0002-qbootctl.c.patch).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class QbootctlConan(ConanFile):
    name = "qbootctl"
    version = "0.2.2"
    description = "Qualcomm bootctrl HAL port for Linux — A/B boot slot management CLI"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/linux-msm/qbootctl"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS + Linux are the only supported targets.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qbootctl only supports Linux-like OS, got: {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        MesonToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        # meson.install() installs only install:true targets -> the
        # production bin/qbootctl. qbootctl-test (QBOOTCTL_TESTING) is
        # install:false in meson.build, so it is copied to a test-only
        # location inside the package and never exposed through
        # cpp_info.bindirs; the production package ships only the real
        # qbootctl binary plus LICENSE.
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "qbootctl-test",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "test"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # CLI tool only: no libraries or headers are produced.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
