#!/usr/bin/env python3
"""Conan recipe for requests 2.34.2 — Python HTTP library."""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os


class RequestsConan(ConanFile):
    name = "requests"
    version = "2.34.2"
    description = "Python HTTP for Humans"
    license = "Apache-2.0"
    homepage = "https://requests.readthedocs.io/"
    url = ""

    package_type = "python-require"
    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        self.run(f"pip install {self.source_folder} --target={self.package_folder}/lib/python3.12/site-packages --no-deps",
                 cwd=self.source_folder)

    def package(self):
        pass  # build() already installed to package_folder

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []