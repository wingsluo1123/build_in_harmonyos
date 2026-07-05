#!/usr/bin/env python3
"""Conan recipe — pip/Python projects.

Black is the uncompromising Python code formatter.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BlackConan(ConanFile):
    name = "black"
    version = "26.5.1"
    description = "Black is the uncompromising Python code formatter that reformats code into a consistent style"
    license = "MIT"
    homepage = "https://black.readthedocs.io/"
    url = ""  # CI fills this

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Python3 and pip3 are system tools, not Conan dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Install all black runtime dependencies
        self.run(
            f'pip3 install click pathspec platformdirs mypy_extensions '
            f'packaging pytokens tomli '
            f'--target="{self.build_folder}/site-packages"',
            env="conanrun"
        )
        # Then install black itself (no-deps to avoid reinstalling)
        self.run(
            f'pip3 install "{self.source_folder}" --no-deps '
            f'--target="{self.build_folder}/site-packages" '
            f'--no-build-isolation',
            env="conanrun"
        )

    def package(self):
        # Copy Python packages
        copy(self, "*", os.path.join(self.build_folder, "site-packages"),
             os.path.join(self.package_folder, "lib", "python3.12", "site-packages"))

        # Create black wrapper script since pip --target doesn't create bin/ scripts
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "black")
        site_packages = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        with open(wrapper, 'w') as f:
            f.write("#!/system/bin/sh\n")
            f.write(f'PYTHONPATH="{site_packages}:$PYTHONPATH" ')
            f.write('exec python3 -m black "$@"\n')
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IEXEC)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
