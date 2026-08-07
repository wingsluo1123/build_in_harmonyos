#!/usr/bin/env python3
"""Conan recipe — pound 4.22 (Autotools).

Pound is a lightweight HTTP/HTTPS reverse-proxy and load balancer.
It builds as a command-line tool (sbin/pound, bin/poundctl).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PoundConan(ConanFile):
    name = "pound"
    version = "4.22"
    description = "Lightweight HTTP/HTTPS reverse-proxy and load balancer"
    license = "GPL-3.0"
    homepage = "https://www.apsis.ch/pound"
    url = "https://github.com/graygnuorg/pound"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/1.1.1w")
        self.requires("pcre2/10.40")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable dynamic backends (adns not available on OHOS)
        tc.configure_args.append("--disable-dynamic-backends")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Bootstrap: generate configure from configure.ac (source from git tag, no pre-generated configure)
        # Use bash directly since /bin/sh may not exist on HarmonyOS
        self.run("bash ./bootstrap", cwd=self.source_folder)
        # Fix HMDFS mktemp permission issue: config.status uses mktemp -d "./confXXXXXX"
        # which fails on HarmonyOS HMDFS filesystem due to umask 077.
        # Replace mktemp with mkdir and umask 077 with umask 022.
        from conan.tools.files import replace_in_file
        conf_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, conf_path,
                        'umask 077 && mktemp -d "./confXXXXXX"',
                        'umask 022 && mkdir -p "${TMPDIR:-/storage/Users/currentUser/tmp}/conf$$" && echo "${TMPDIR:-/storage/Users/currentUser/tmp}/conf$$"')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
