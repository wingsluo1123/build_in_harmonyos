#!/usr/bin/env python3
"""Conan recipe for haproxy 3.2.0 — OHOS PC aarch64."""
import os
import subprocess
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

class HaproxyConan(ConanFile):
    name = "haproxy"
    version = "3.2.0"
    description = "Reliable, High Performance TCP/HTTP Load Balancer"
    license = "GPL-2.0-or-later"
    homepage = "https://www.haproxy.org/"
    url = ""
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1.1")
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        openssl = self.dependencies["openssl"]
        zlib = self.dependencies["zlib"]
        pcre2 = self.dependencies["pcre2"]
        openssl_inc = openssl.package_folder + "/include"
        openssl_lib = openssl.package_folder + "/lib"
        zlib_inc = zlib.package_folder + "/include"
        zlib_lib = zlib.package_folder + "/lib"
        pcre2_inc = pcre2.package_folder + "/include"
        pcre2_lib = pcre2.package_folder + "/lib"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"HAProxy supports Linux and OHOS, got {self.settings.os}")
        env = os.environ.copy()
        env["MAKEFLAGS"] = ""
        env["GNUMAKEFLAGS"] = ""
        cmd_list = ["make", "--output-sync=none", "TARGET=linux-musl", f"CC={cc}",
            "USE_OPENSSL=1", "USE_ZLIB=1", "USE_PCRE2=1", "USE_THREAD=1", "USE_PROMEX=1",
            f"SSL_INC={openssl_inc}", f"SSL_LIB={openssl_lib}",
            f"ZLIB_INC={zlib_inc}", f"ZLIB_LIB={zlib_lib}",
            f"PCRE2_INC={pcre2_inc}", f"PCRE2_LIB={pcre2_lib}",
            "CFLAGS=-fPIC -O2"]
        result = subprocess.run(cmd_list, env=env, cwd=self.source_folder)
        if result.returncode != 0:
            raise Exception(f"Build failed with return code {result.returncode}")

    def package(self):
        copy(self, "haproxy", self.source_folder, os.path.join(self.package_folder, "sbin"))
        copy(self, "*.cfg", os.path.join(self.source_folder, "examples"),
             os.path.join(self.package_folder, "share", "haproxy", "examples"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
