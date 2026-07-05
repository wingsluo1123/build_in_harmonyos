#!/usr/bin/env python3
"""Conan recipe — bib-tool 2.68 (autotools executable tool)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BibtoolConan(ConanFile):
    name = "bib-tool"
    version = "2.68"
    description = "bib-tool 2.68 — BibTeX file manipulation tool"
    license = "MIT"
    homepage = ""
    url = ""

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
        tc.generate()

    def _fix_script(self, path):
        """Fix shebang and umask for OHOS."""
        if not os.path.isfile(path):
            return
        with open(path, "r") as f:
            content = f.read()
        content = content.replace("#!/bin/bash", "#!/data/service/hnp/bin/bash")
        content = content.replace("#!/bin/sh", "#!/system/bin/sh")
        content = content.replace("#! /bin/bash", "#!/data/service/hnp/bin/bash")
        content = content.replace("#! /bin/sh", "#!/system/bin/sh")
        content = content.replace("umask 077", "umask 022")
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)

    def build(self):
        # Fix configure shebang and umask
        self._fix_script(os.path.join(self.source_folder, "configure"))

        # Run configure with --no-create to generate config.status without executing it
        self.run("./configure --no-create --prefix=", cwd=self.source_folder, env="conanbuild")

        # Fix config.status umask (HMDFS setgid issue)
        self._fix_script(os.path.join(self.source_folder, "config.status"))

        # Run config.status to generate Makefiles
        self.run("./config.status", cwd=self.source_folder, env="conanbuild")

        # Build
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # bib-tool's Makefile doesn't support DESTDIR; copy binary manually
        copy(self, "bibtool", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
