#!/usr/bin/env python3
"""Conan recipe for spicedb 1.56.0."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class SpicedbConan(ConanFile):
    name = "spicedb"
    version = "1.56.0"
    description = "Open-source permissions database inspired by Google Zanzibar"
    license = "Apache-2.0"
    homepage = "https://github.com/authzed/spicedb"
    url = "https://github.com/authzed/spicedb"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                "The upstream pre-built SpiceDB package used for OHOS PC is linux/arm64 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        download(self, sources["url"], sources["filename"], sha256=sources["sha256"])
        self.run(f'tar xzf "{sources["filename"]}"')

    def build(self):
        self.output.info(
            "Using upstream pre-built SpiceDB linux/arm64 release package; "
            "the OHOS CI worker currently does not provide a Go toolchain."
        )

    def package(self):
        binary = self.conan_data["build"]["binary"]
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        tarball = os.path.join(self.source_folder, self.conan_data["sources"]["filename"])
        self.run(f'tar xzf "{tarball}" -C "{bin_dir}" "{binary}"')
        os.chmod(os.path.join(bin_dir, binary),
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "spicedb"),
             keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "completions"),
             dst=os.path.join(self.package_folder, "share", "spicedb", "completions"),
             keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "manpages"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
