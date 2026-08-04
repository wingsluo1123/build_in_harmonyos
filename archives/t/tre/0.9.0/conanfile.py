#!/usr/bin/env python3
"""Conan recipe for TRE v0.9.0 — OHOS (OpenHarmony) aarch64 adaptation."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TREConan(ConanFile):
    name = "tre"
    version = "0.9.0"
    description = "C library for POSIX regex matching with approximate (fuzzy) matching"
    license = "BSD-3-Clause"
    homepage = "https://github.com/laurikari/tre"
    url = "https://github.com/laurikari/tre"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Explicit build/host triplet — AutotoolsToolchain does not generate
        # --host for os=OHOS; config.guess also fails on OHOS (uname mismatch).
        # TODO: migrate to dynamic triplet when Conan OHOS support matures.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--enable-approx")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E097: Fix HMDFS setgid — autoconf umask 077 strips group perms.
        # Modifying generated 'configure' violates R6 in principle, but this
        # is a runtime fix for autoconf behavior — no source patch available.
        source_dir = self.source_folder
        self.run(
            "sed -i 's/umask 077/umask 022/g' configure"
            " && sed -i 's|mktemp -d \"./confXXXXXX\"|mktemp -d \"$TMPDIR/confXXXXXX\"|g' configure",
            cwd=source_dir
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tre"]
        self.cpp_info.bindirs = ["bin"]
