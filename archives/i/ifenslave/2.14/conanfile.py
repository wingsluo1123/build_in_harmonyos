#!/usr/bin/env python3
"""Conan recipe — ifenslave 2.14 (ifupdown bonding hooks, shell scripts)."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IfenslaveConan(ConanFile):
    name = "ifenslave"
    version = "2.14"
    description = "Configure network interfaces for parallel routing (bonding)"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/debian/ifenslave"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("network", "bonding", "ifupdown", "shell")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def config_options(self):
        # OHOS profile carries os.version (e.g. 6.0); pure shell hooks are
        # version-independent, drop the subsetting so package_id stays stable.
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def package_id(self):
        # Pure shell hooks: no compilation, one package for every
        # compiler/build_type/arch combination (overdrive 2.4.1 precedent).
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        debian_dir = os.path.join(self.source_folder, "debian")
        expected = [
            "ifenslave.if-pre-up",
            "ifenslave.if-up",
            "ifenslave.if-post-down",
        ]
        for name in expected:
            path = os.path.join(debian_dir, name)
            if not os.path.isfile(path):
                raise ConanException("upstream ifenslave hook missing: %s" % path)
        self.output.info("Validated 3 upstream ifupdown bonding hooks; no compilation required")

    def package(self):
        debian_dir = os.path.join(self.source_folder, "debian")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name in ["ifenslave.if-pre-up", "ifenslave.if-up", "ifenslave.if-post-down"]:
            copy(self, name, src=debian_dir, dst=bin_dir)
            installed = os.path.join(bin_dir, name)
            try:
                mode = os.stat(installed).st_mode
                os.chmod(installed, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError as exc:
                self.output.warning("chmod +x ignored for %s: %s" % (installed, exc))
        doc_dir = os.path.join(self.package_folder, "share", "doc", "ifenslave")
        os.makedirs(doc_dir, exist_ok=True)
        for name in ["README.Debian", "README.source", "NEWS", "copyright", "98-net-bonding.link"]:
            copy(self, name, src=debian_dir, dst=doc_dir)
        examples_src = os.path.join(debian_dir, "examples")
        examples_dst = os.path.join(doc_dir, "examples")
        os.makedirs(examples_dst, exist_ok=True)
        for name in ["ethernet+hotplug_wifi", "ethernet+wifi", "two_ethernet", "two_hotplug_ethernet"]:
            copy(self, name, src=examples_src, dst=examples_dst)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
