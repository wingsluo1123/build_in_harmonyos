#!/usr/bin/env python3
"""Conan recipe for bmake — Portable BSD make tool (command-line)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class BmakeConan(ConanFile):
    name = "bmake"
    version = "20260508"
    description = "Portable version of NetBSD make(1)"
    license = "BSD-3-Clause"
    homepage = "https://www.crufty.net/help/sjg/bmake.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        # R33: don't rely on shell env vars; pass CXX explicitly
        tc.configure_args.append("CXX=clang++")
        # --without-makefile: prevent generated makefile (GNU make can't parse BSD makefiles)
        tc.configure_args.append("--without-makefile")
        # --without-meta: disable meta mode (needs filemon(9) not available on OHOS)
        tc.configure_args.append("--without-meta")
        # --without-filemon: disable filemon (not available on OHOS)
        tc.configure_args.append("--without-filemon")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # bmake uses make-bootstrap.sh (not GNU Makefile) to build
        chdir(self, self.source_folder)
        self.run("sh make-bootstrap.sh op=build")

    def package(self):
        # The bmake binary is built into self.build_folder by make-bootstrap.sh
        build_bmake = os.path.join(self.build_folder, "bmake")
        if not os.path.isfile(build_bmake):
            # Fallback: look in source folder
            build_bmake = os.path.join(self.source_folder, "bmake")
        
        # Install bmake binary
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "bmake", src=os.path.dirname(build_bmake), dst=bin_dir)
        
        # Install mk files (for bmake to find sys.mk)
        share_dir = os.path.join(self.package_folder, "share", "mk")
        mk_dir = os.path.join(self.source_folder, "mk")
        if os.path.isdir(mk_dir):
            copy(self, "*", src=mk_dir, dst=share_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Use relative path; Conan resolves it to the package folder
        self.runenv_info.prepend_path("PATH", "bin")