#!/usr/bin/env python3
"""Conan recipe for oath-toolkit 2.6.13-r0 — OATH Toolkit (OTP library and tools).

Components:
  - liboath:  OTP library (HOTP/TOTP)
  - libpskc:  PSKC library (depends on libxml2)
  - pam_oath: PAM module (depends on linux-pam and liboath)
  - oathtool: CLI tool for OTP generation
  - pskctool: CLI tool for PSKC management
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import AutotoolsDeps
from conan.tools.gnu import PkgConfigDeps


class OathToolkitConan(ConanFile):
    name = "oath-toolkit"
    version = "2.6.13-r0"
    description = "OATH Toolkit — one-time password (OTP) library and tools (HOTP/TOTP, PSKC, PAM)"
    license = "MIT"
    homepage = "https://oath-toolkit.codeberg.page/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3.1")
        self.requires("linux-pam/1.7.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # PAM and PSKC are enabled by default; make it explicit
        tc.configure_args.append("--enable-pam")
        tc.configure_args.append("--enable-pskc")

        # HarmonyOS: CONFIG_SHELL must be bash (not /bin/sh)
        env = tc.environment()
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("SHELL", "/data/service/hnp/bin/bash")

        # HarmonyOS: lld linker depends on system libxml2.so.16 (at SDK path).
        # AutotoolsDeps adds -lxml2 to LIBS, so test programs also need libxml2 at runtime.
        # Put SDK path first so lld finds its own libxml2; conan path for other libs.
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        env.prepend_path("LD_LIBRARY_PATH", sdk_lib)

        tc.generate(env=env)

        # PkgConfigDeps generates .pc files for dependencies (needed for configure's pkg-config checks)
        pkg = PkgConfigDeps(self)
        pkg.generate()

        # AutotoolsDeps generates CPPFLAGS, LDFLAGS, LIBS
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["oath", "pskc"]
        self.cpp_info.includedirs = ["include", "include/liboath", "include/libpskc"]
