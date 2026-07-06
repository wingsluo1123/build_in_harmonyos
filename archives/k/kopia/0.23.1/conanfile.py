#!/usr/bin/env python3
"""Conan recipe — kopia (Go binary, backup tool).

kopia is a pure Go binary. Build uses `go build` directly.
No configure, no autotools. package() only ships bin/kopia.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, save
from conan.tools.layout import basic_layout


class KopiaConan(ConanFile):
    name = "kopia"
    version = "0.23.1"
    description = "Fast and secure open-source backup tool"
    license = "Apache-2.0"
    homepage = "https://github.com/kopia/kopia"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Go project — no C/C++ library dependencies managed by Conan
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # kopia is a pure Go binary. Build with nohtmlui tag to skip
        # the HTML UI embedding (which requires npm).
        ldflags = (
            "-s -w"
            " -X github.com/kopia/kopia/repo.BuildVersion=0.23.1"
            " -X github.com/kopia/kopia/repo.BuildInfo=conan"
            " -X github.com/kopia/kopia/repo.BuildGitHubRepo=kopia/kopia"
        )
        self.run(
            f"go build -trimpath -ldflags \"{ldflags}\""
            f" -tags nohtmlui -o kopia github.com/kopia/kopia"
        )

    def package(self):
        # kopia binary was built in the build folder
        copy(self, "kopia", self.build_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # kopia is a CLI binary tool, not a library — no cpp_info.libs
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Make kopia binary available in PATH for consumers (test_package needs this)
        bin_path = os.path.join(self.package_folder, "bin")
        self.runenv_info.define("PATH", bin_path)


