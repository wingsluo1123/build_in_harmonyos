#!/usr/bin/env python3
"""Test package for libquvi-scripts 0.9.20131130.

Verifies that the Lua scripts are installed correctly by checking
the presence of key script files and the version metadata using
shell commands against the installed package.
"""
import os

from conan import ConanFile


class LibquviScriptsTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["libquvi-scripts"]
        pkg_folder = dep.package_folder

        # Locate the share/libquvi-scripts directory
        share_dir = os.path.join(pkg_folder, "res", "share",
                                 "libquvi-scripts")
        if not os.path.isdir(share_dir):
            share_dir = os.path.join(pkg_folder, "share",
                                     "libquvi-scripts")

        assert os.path.isdir(share_dir), \
            f"libquvi-scripts share dir not found: {share_dir}"

        # Verify version file content using self.run (CI L0d requires self.run)
        version_file = os.path.join(share_dir, "0.9", "version")
        self.run(f'cat "{version_file}"', env="conanrun")
        self.run(f'grep "v0.9.20131130" "{version_file}"', env="conanrun")

        # Verify key Lua scripts exist and are readable
        common_dir = os.path.join(share_dir, "0.9", "common", "quvi")
        for script in ["const.lua", "html.lua", "util.lua"]:
            script_path = os.path.join(common_dir, script)
            self.run(f'test -f "{script_path}"', env="conanrun")
            self.run(f'head -1 "{script_path}"', env="conanrun")

        # Verify media scripts directory has content
        media_dir = os.path.join(share_dir, "0.9", "media")
        self.run(f'test -d "{media_dir}" && ls "{media_dir}" | wc -l',
                 env="conanrun")

        # Verify pkg-config file if present
        pc_path = os.path.join(pkg_folder, "res", "lib", "pkgconfig",
                               "libquvi-scripts-0.9.pc")
        if not os.path.isfile(pc_path):
            pc_path = os.path.join(pkg_folder, "lib", "pkgconfig",
                                   "libquvi-scripts-0.9.pc")
        if os.path.isfile(pc_path):
            self.run(f'grep "0.9.20131130" "{pc_path}"', env="conanrun")
