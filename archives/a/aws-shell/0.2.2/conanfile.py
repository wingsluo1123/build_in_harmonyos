#!/usr/bin/env python3
"""Conan recipe for aws-shell — Python interactive shell for AWS CLI.

aws-shell is a Python package built with setuptools. It provides an
interactive productivity booster for the AWS CLI with auto-completion,
fuzzy searching, and inline documentation.

Build system: Python setuptools (setup.py)
Product type: CLI application (aws-shell, aws-shell-mkindex)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class AwsShellConan(ConanFile):
    name = "aws-shell"
    version = "0.2.2"
    description = "AWS Shell - The interactive productivity booster for the AWS CLI"
    license = "Apache License 2.0"
    homepage = "https://github.com/awslabs/aws-shell"

    package_type = "application"

    # Python package — accept os setting for platform compatibility but
    # don't use compiler/build_type/arch since this is pure Python.
    settings = "os"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # aws-shell's Python runtime dependencies. These are pip packages
        # that the consumer must have installed (or install via pip).
        # Listed here for documentation; conan does not manage pip deps.
        pass

    def layout(self):
        # Simple layout — source in build folder, package in package folder
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Build the wheel and install into staging directory
        staging = os.path.join(self.build_folder, "staging")
        os.makedirs(staging, exist_ok=True)

        # Use pip to install --no-deps into staging (R1: minimal build)
        # Without --no-build-isolation so pip can use setuptools from build env
        self.run(
            f"pip3 install --no-deps --target={staging} .",
            env="conan_build",
        )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if not os.path.isdir(staging):
            staging = os.path.join(self.build_folder, "..", "staging")

        # Copy installed Python files to package
        # Python packages go to lib/python3/site-packages/
        # Executables go to bin/
        dest_lib = os.path.join(self.package_folder, "lib", "python3", "site-packages")
        dest_bin = os.path.join(self.package_folder, "bin")

        os.makedirs(dest_lib, exist_ok=True)
        os.makedirs(dest_bin, exist_ok=True)

        # Copy Python packages and metadata
        for item in os.listdir(staging):
            src = os.path.join(staging, item)
            if item == "bin":
                # Copy executables
                for bin_item in os.listdir(src):
                    copy(self, bin_item, src, dest_bin)
            elif item.endswith(".dist-info"):
                # Copy dist-info metadata
                dest_info = os.path.join(dest_lib, item)
                os.makedirs(dest_info, exist_ok=True)
                for root, _, files in os.walk(src):
                    for f in files:
                        src_file = os.path.join(root, f)
                        rel = os.path.relpath(src_file, src)
                        dest_file = os.path.join(dest_info, rel)
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)
            else:
                # Copy Python packages
                dest_pkg = os.path.join(dest_lib, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dest_pkg, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dest_pkg)

    def package_info(self):
        # Set up bin path
        self.cpp_info.bindirs = ["bin"]
        # Set up Python path for the package
        self.cpp_info.libdirs = ["lib/python3/site-packages"]

        # Ensure PYTHONPATH includes the site-packages directory
        python_path = os.path.join(self.package_folder, "lib", "python3", "site-packages")
        self.runenv_info.append_path("PYTHONPATH", python_path)
        self.buildenv_info.append_path("PYTHONPATH", python_path)
