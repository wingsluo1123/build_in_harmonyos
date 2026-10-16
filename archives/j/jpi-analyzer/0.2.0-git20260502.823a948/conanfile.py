#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for jpi-analyzer 0.2.0-git20260502.823a948"""

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import os
import sys


class JpiAnalyzerConan(ConanFile):
    name = "jpi-analyzer"
    version = "0.2.0-git20260502.823a948"
    license = "MIT"
    author = "Sophie Bertsch"
    url = "https://github.com/unicornlines/JPI-Parser"
    homepage = "https://github.com/unicornlines/JPI-Parser"
    description = "Parse JPI EDM flight data files and export them to CSV"
    topics = ("cli", "python", "flight-data", "edm")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Runtime dependency (click>=8.1 per upstream pyproject); resolved from
        # the ohpcd registry where click/8.4.2 is already published.
        self.requires("click/8.4.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Build the package using pip (PEP 517 setuptools.build_meta).
        # --no-deps: click comes from the Conan dependency graph, not PyPI.
        # Build isolation fetches setuptools/wheel from the network (same
        # proven path as click/8.4.2 on this device).
        install_target = os.path.join(self.build_folder, "install")
        self.run(
            f'{sys.executable} -m pip install --no-deps --target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        # Copy the installed files from build folder to package folder
        install_target = os.path.join(self.build_folder, "install")
        copy(self, "*", dst=self.package_folder, src=install_target)

    def package_info(self):
        # Python package information
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # Console scripts (jpi-analyzer, jpia) installed by pip into <pkg>/bin
        self.cpp_info.bindirs = ["bin"]

        # Python-specific environment
        # Use the package folder directly (pip --target is flat installation)
        python_path = self.package_folder

        self.output.info(f"Setting PYTHONPATH: {python_path}")
        self.runenv_info.prepend_path("PYTHONPATH", python_path)
