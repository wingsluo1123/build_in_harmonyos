#!/usr/bin/env python3
"""test_package for vitunes 2.3 - end-to-end consumer test of the CLI.

The package ships the `vitunes` executable plus its man page. `test()` runs the
L0c test source test_vitunes.py, which drives the real CLI: e-command help,
database creation, a recursive directory scan (including a symbolic link cycle),
taglib meta-data extraction and a database dump.
"""
import os
import sys

from conan import ConanFile


class VitunesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ncurses runenv (TERMINFO) comes with the dependency's runenv_info;
        # declare it directly so it is aggregated into the conanrun env.
        self.requires("ncurses/6.6")

    def test(self):
        dep = self.dependencies["vitunes"]
        exe = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0], "vitunes")
        script = os.path.join(self.source_folder, "test_vitunes.py")
        # L0d: really execute the test source through self.run
        self.run(f'"{sys.executable}" "{script}" "{exe}"')
