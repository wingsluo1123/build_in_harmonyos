#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout

class LibConan(ConanFile):
    name = "cleo"
    version = "0.004"
    settings = "os", "compiler", "build_type", "arch"
    def layout(self):
        basic_layout(self)
    def source(self):
        get(self, **self.conan_data["sources"])
    def build(self):
        pass
    def package(self):
        copy(self, "*", self.source_folder, self.package_folder)
    def package_info(self):
        self.cpp_info.libs = []
