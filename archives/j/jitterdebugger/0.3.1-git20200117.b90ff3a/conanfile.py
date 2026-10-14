#!/usr/bin/env python3
"""Conan recipe - jitterdebugger 0.3.1-git20200117.b90ff3a."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JitterdebuggerConan(ConanFile):
    name = "jitterdebugger"
    version = "0.3.1-git20200117.b90ff3a"
    description = "Wake-up latency measurement and sample post-processing tools"
    license = "MIT"
    homepage = "https://github.com/igaw/jitterdebugger"
    url = "https://github.com/igaw/jitterdebugger"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)
    def export_sources(self):
        export_conandata_patches(self)
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"
        self.run(f"make -j1 CC={cc}", cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in ("jitterdebugger", "jittersamples", "jitterplot"):
            copy(self, name, src=self.source_folder, dst=bin_dir)
        for name in ("jitterdebugger", "jittersamples", "jitterplot"):
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
