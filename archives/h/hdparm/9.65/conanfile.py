#!/usr/bin/env python3
"""Conan recipe for hdparm 9.65 — Linux disk utility (command-line tool)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches)
from conan.tools.layout import basic_layout


class HdparmConan(ConanFile):
    name = "hdparm"
    version = "9.65"
    description = "hdparm — utility for displaying and/or setting hard disk parameters"
    license = "BSD"
    homepage = "https://sourceforge.net/projects/hdparm/"
    url = "https://sourceforge.net/projects/hdparm/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Export the patches declared in conandata.yml so they are available
        # in the cache source folder and in the build folder.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        tarball = os.path.join(self.source_folder, "hdparm-9.65.tar.gz")
        self.output.info(f"Downloading {url}")
        download(self, url, tarball, sha256=sha256)

    def build(self):
        src_dir = os.path.join(self.source_folder, "hdparm-9.65")
        if not os.path.isdir(src_dir):
            self.output.info("Extracting tarball...")
            tarball = os.path.join(self.source_folder, "hdparm-9.65.tar.gz")
            self.run(
                "python3 -c \"import tarfile,sys; tarfile.open(sys.argv[1],'r:gz')"
                ".extractall(sys.argv[2])\" "
                f'"{tarball}" "{self.source_folder}"'
            )
            src_dir = os.path.join(self.source_folder, "hdparm-9.65")

        apply_conandata_patches(self)

        make_path = shutil.which("make") or "/usr/bin/make"
        cc_path = shutil.which("clang") or "/usr/bin/clang"
        self.output.info(f"make={make_path}, clang={cc_path}")
        self.run(f"{make_path} -j2 CC={cc_path} LDFLAGS=-s", cwd=src_dir)

    def package(self):
        src_dir = os.path.join(self.source_folder, "hdparm-9.65")
        if not os.path.exists(src_dir):
            src_dir = self.source_folder
        pkg = self.package_folder
        copy(self, "hdparm", src=src_dir, dst=os.path.join(pkg, "bin"))
        copy(self, "hdparm.8", src=src_dir, dst=os.path.join(pkg, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
