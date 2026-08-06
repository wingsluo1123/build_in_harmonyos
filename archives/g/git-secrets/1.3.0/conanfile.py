#!/usr/bin/env python3
"""Conan recipe for git-secrets — AWS Labs secret scanner (shell script).

Shell script project, no compilation needed.
Installs git-secrets script and man page.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class GitSecretsConan(ConanFile):
    name = "git-secrets"
    version = "1.3.0"
    description = "git-secrets prevents you from committing passwords and other sensitive information to git repos"
    license = "MIT"
    homepage = "https://github.com/awslabs/git-secrets"
    url = "https://github.com/awslabs/git-secrets"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        copy(self, "git-secrets", src=self.source_folder, dst=bin_dir)
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        copy(self, "git-secrets.1", src=self.source_folder, dst=man_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
