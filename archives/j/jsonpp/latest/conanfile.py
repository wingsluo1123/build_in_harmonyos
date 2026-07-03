#!/usr/bin/env python3
"""Conan recipe — jsonpp (Go command-line JSON pretty printer).

jsonpp is a fast command-line JSON pretty printer written in Go.
Source: https://github.com/jmhodges/jsonpp
License: MIT
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class JsonppConan(ConanFile):
    name = "jsonpp"
    version = "latest"
    description = "A fast command line JSON pretty printer written in Go"
    license = "MIT"
    homepage = "https://github.com/jmhodges/jsonpp"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.name} only supports Linux and OHOS")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # Go build without modules (pre-go.mod project)
        self.run("GO111MODULE=off go build -o jsonpp .", env="conanbuild")

    def package(self):
        copy(self, "jsonpp", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        # This is a command-line tool, not a library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
