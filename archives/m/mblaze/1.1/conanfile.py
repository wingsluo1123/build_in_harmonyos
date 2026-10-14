"""Conan recipe for the mblaze 1.1 Maildir command suite."""

import os
import sys

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class MblazeConan(ConanFile):
    name = "mblaze"
    version = "1.1"
    description = "Maildir command-line message processing suite"
    license = "CC0-1.0 AND MIT"
    homepage = "https://github.com/leahneukirchen/mblaze"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "run_upstream_tests.py"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run(f'make -C "{self.source_folder}" -j2', env="conanbuild")
        runner = os.path.join(self.export_sources_folder, "run_upstream_tests.py")
        if self.settings.os == "OHOS":
            os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"
        self.run(f'"{sys.executable}" "{runner}" "{self.source_folder}"', env="conanbuild")

    def package(self):
        self.run(
            f'make -C "{self.source_folder}" '
            f'DESTDIR="{self.package_folder}" PREFIX= install',
            env="conanbuild",
        )
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        for filename in ("mymemmem.c", "mystrverscmp.c"):
            copy(self, filename, self.source_folder,
                 os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
