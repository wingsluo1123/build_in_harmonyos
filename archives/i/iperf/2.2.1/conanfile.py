#!/usr/bin/env python3
"""Conan recipe for iperf 2.2.1 — network bandwidth testing tool.

iperf is a tool for measuring maximum TCP and UDP bandwidth performance.
It supports tuning various parameters related to timing, protocols, and
buffering, and reports bandwidth, delay jitter, and datagram loss.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IperfConan(ConanFile):
    name = "iperf"
    version = "2.2.1"
    package_type = "application"
    description = "Network bandwidth performance testing tool (TCP/UDP)"
    license = "BSD-3-Clause"
    homepage = "https://sourceforge.net/projects/iperf2/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: os check must include OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        url = sources["url"]
        sha256 = sources.get("sha256")
        filename = sources.get("filename", "iperf-2.2.1.tar.gz")
        get(self, url=url, sha256=sha256, filename=filename, strip_root=True)

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
        # iperf is a standalone binary tool, no libraries to export
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
