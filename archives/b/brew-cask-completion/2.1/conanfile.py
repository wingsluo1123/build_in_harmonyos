#!/usr/bin/env python3
"""Conan recipe for brew-cask-completion 2.1 — shell completion scripts.

This package contains shell completion scripts for Homebrew Cask.
No compilation is needed — just install the script files.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BrewcaskcompletionConan(ConanFile):
    name = "brew-cask-completion"
    version = "2.1"
    description = "Shell completion scripts for Homebrew Cask"
    license = "MIT"
    homepage = "https://github.com/xyb/homebrew-cask-completion"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # No build step - pure script package

    def package(self):
        # Install completion scripts
        copy(self, "*.bash", self.source_folder, os.path.join(self.package_folder, "share", "bash-completion", "completions"))
        copy(self, "*.fish", self.source_folder, os.path.join(self.package_folder, "share", "fish", "completions"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "share", "licenses", "brew-cask-completion"))

    def package_info(self):
        self.cpp_info.libs = []
