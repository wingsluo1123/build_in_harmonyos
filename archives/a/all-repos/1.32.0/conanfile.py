#!/usr/bin/env python3
"""Conan recipe for all-repos — Clone and run commands across all repos.

all-repos is a pure Python package (CLI + library) by Anthony Sottile (asottile).
No C/C++ compilation needed — build() just copies .py files to the package directory.
The package ships multiple CLI entry points (all-repos-clone, all-repos-grep, etc.)
and a Python library (all_repos module) for batch Git operations across repositories.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class AllReposConan(ConanFile):
    name = "all-repos"
    version = "1.32.0"
    description = "Clone and run commands across all repos (Yelp tool for batch Git operations)"
    license = "MIT"
    homepage = "https://github.com/asottile/all-repos"
    url = ""  # CI fills this

    # Pure Python content package — no compiled binary or library.
    # Using header-library because Conan doesn't have a pure-Python package_type
    # and we can't easily set up entry points for Python CLI tools in Conan.
    package_type = "header-library"

    # No compiler/build_type needed — pure Python
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Python runtime dependencies (cfgv, identify, packaging, pluggy)
        # are NOT Conan dependencies — they are pip-installable Python packages.
        # Document them in notes.md instead.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # Pure Python library — no compilation needed.
        # The .py files are just copied in the package() step.
        pass

    def package(self):
        # Copy all .py files from the all_repos/ source directory to the package.
        # Use glob '*.py' with keep_path=True to recursively preserve the directory
        # structure (all_repos/autofix/, all_repos/push/, all_repos/source/).
        copy(self, "*.py",
             src=os.path.join(self.source_folder, "all_repos"),
             dst=os.path.join(self.package_folder, "lib", "all_repos"),
             keep_path=True)
        # Copy non-Python files if any (e.g., data files) — none in this package.

    def package_info(self):
        self.cpp_info.includedirs = ["lib"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
