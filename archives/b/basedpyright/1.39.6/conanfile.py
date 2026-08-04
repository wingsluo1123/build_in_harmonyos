#!/usr/bin/env python3
"""Conan recipe for basedpyright — a Node.js/npm application.

basedpyright is a fork of pyright (Python type checker) distributed as a
pre-built npm package. No C/C++ compilation is needed; this recipe packages
the JavaScript files and creates bin wrappers that invoke node.

Build system: npm (pre-built package)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class BasedpyrightConan(ConanFile):
    name = "basedpyright"
    version = "1.39.6"
    description = "A fork of pyright with various type checking improvements, pylance features and more"
    license = "MIT"
    homepage = "https://github.com/DetachHead/basedpyright"
    url = ""  # CI fills this

    package_type = "application"
    settings = ("os", "arch")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No build step — the npm package contains pre-built JavaScript

    def package(self):
        # Copy package files to lib/node_modules/basedpyright/
        target = os.path.join(self.package_folder, "lib", "node_modules", "basedpyright")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(self.source_folder, target)

        # Create bin wrappers that invoke node with the correct JS entry point
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        wrapper_template = (
            "#!/bin/sh\n"
            "# Auto-generated bin wrapper for {name}\n"
            'SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\n'
            'exec node "${{SCRIPT_DIR}}/../lib/node_modules/basedpyright/{entry}" "$@"\n'
        )

        entries = {
            "basedpyright": "index.js",
            "basedpyright-langserver": "langserver.index.js",
            "pyright": "index.js",
            "pyright-langserver": "langserver.index.js",
        }

        for name, entry in entries.items():
            wrapper_path = os.path.join(bin_dir, name)
            with open(wrapper_path, "w") as f:
                f.write(wrapper_template.format(name=name, entry=entry))
            os.chmod(wrapper_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
