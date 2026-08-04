#!/usr/bin/env python3
"""Conan recipe for autojump 22.5.3 — a Python/bash command-line tool.

autojump is a pure Python/bash script project (no C compilation).
It uses install.py for installation instead of configure/make.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class AutojumpConan(ConanFile):
    name = "autojump"
    version = "22.5.3"
    description = "A faster way to navigate your filesystem"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/wting/autojump"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Fix hardcoded /usr/local path in autojump.sh to use the package prefix
        autojump_sh = os.path.join(self.source_folder, "bin", "autojump.sh")
        prefix = self.package_folder
        replace_in_file(self, autojump_sh,
                        "/usr/local/share/autojump",
                        os.path.join(prefix, "share", "autojump"))

        # Run install.py to install files to package folder
        install_prefix = "usr/local"  # relative path (os.path.join behavior)
        self.run(f'python3 install.py -d "{self.package_folder}" -p {install_prefix} --force',
                 cwd=self.source_folder)

        # Move etc/profile.d and functions under the prefix
        etc_src = os.path.join(self.package_folder, "etc", "profile.d")
        etc_dst = os.path.join(self.package_folder, "usr", "local", "etc", "profile.d")
        if os.path.isdir(etc_src):
            os.makedirs(os.path.dirname(etc_dst), exist_ok=True)
            shutil.move(etc_src, etc_dst)
            os.rmdir(os.path.join(self.package_folder, "etc"))

        func_src = os.path.join(self.package_folder, "functions")
        func_dst = os.path.join(self.package_folder, "usr", "local", "share", "zsh", "site-functions")
        if os.path.isdir(func_src):
            os.makedirs(os.path.dirname(func_dst), exist_ok=True)
            shutil.move(func_src, func_dst)

    def package(self):
        # Files already installed to package_folder by build()
        pass

    def package_info(self):
        bin_dir = os.path.join("usr", "local", "bin")
        share_dir = os.path.join("usr", "local", "share", "autojump")
        self.cpp_info.bindirs = [bin_dir]
        self.cpp_info.resdirs = [share_dir]
