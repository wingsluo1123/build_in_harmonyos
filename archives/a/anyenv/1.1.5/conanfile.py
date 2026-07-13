#!/usr/bin/env python3
"""Conan recipe for anyenv 1.1.5.

anyenv is a pure Bash command dispatcher for rbenv-style environment
managers. There is no compile step; packaging copies the entrypoint and
libexec command scripts into bin/ so Conan's VirtualRunEnv can expose a
self-contained command set.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AnyenvConan(ConanFile):
    name = "anyenv"
    version = "1.1.5"
    description = "All-in-one wrapper for rbenv-style environment managers"
    license = "MIT"
    homepage = "https://github.com/anyenv/anyenv"
    url = ""

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "anyenv", src=os.path.join(self.source_folder, "libexec"), dst=bin_dir, keep_path=False)
        copy(self, "anyenv-*", src=os.path.join(self.source_folder, "libexec"), dst=bin_dir, keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "completions"), dst=os.path.join(self.package_folder, "share", "anyenv", "completions"), keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "envs"), dst=os.path.join(self.package_folder, "share", "anyenv", "envs"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "res"), keep_path=False)

        for fname in os.listdir(bin_dir):
            fpath = os.path.join(bin_dir, fname)
            if os.path.isfile(fpath):
                os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
