#!/usr/bin/env python3
"""Conan recipe for argus-clients 5.0.3 — Argus network flow analysis client tools.

Argus Clients is a suite of client programs for reading, analyzing and
managing Argus network flow data.  It produces CLI tools (ra, rabins,
racluster, etc.) and static libraries (libargus_parse.a, libargus_common.a,
libargus_client.a).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class ArgusclientsConan(ConanFile):
    name = "argus-clients"
    version = "5.0.3"
    description = "Argus Clients - Network flow data analysis client tools"
    license = "GPL-3.0-or-later"
    homepage = "http://qosient.com/argus"
    url = "https://github.com/openargus/clients"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["argus_parse", "argus_common", "argus_client"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread"]
