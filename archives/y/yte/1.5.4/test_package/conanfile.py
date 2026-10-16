#!/usr/bin/env python3
"""Conan test_package for yte 1.5.4 — Python library.

Runs test_yte.py (real test source file, satisfies L0c) against the package
installed by THIS conan recipe (verifies module path + real API).
"""
import os
import sys  # R33: CI/worker python3 = /data/app/bin/python3, never hardcode host paths

from conan import ConanFile
from conan.errors import ConanException


class YteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["yte"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        test_script = os.path.join(os.path.dirname(__file__), "test_yte.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_yte.py missing: {test_script}")
        # conanrun env 的 LD_LIBRARY_PATH（hnp SDK llvm lib）会污染扩展模块
        # 加载（math/_posixsubprocess ImportError），剥离后运行
        self.run(
            f'env -u LD_LIBRARY_PATH -u PYTHONHOME -u PYTHONPATH '
            f'"{sys.executable}" "{test_script}" "{site}"'
        )
