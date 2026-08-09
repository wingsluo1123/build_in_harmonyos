#!/usr/bin/env python3
"""Conan recipe for xapers 0.9.0 — Python package (setuptools).

xapers is a personal journal article management system written in Python.
It provides a CLI tool `xapers` (console_scripts entry point) and the
`xapers` Python package.

Build system: setuptools (setup.py)
No C/C++ compilation required — pure Python (py3-none-any).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class XapersConan(ConanFile):
    name = "xapers"
    version = "0.9.0"
    description = "Personal journal article management system"
    license = "GPL-3.0+"
    homepage = "https://finestructure.net/xapers"
    url = ""

    # xapers is a CLI tool (console_scripts entry point), not a library
    package_type = "application"

    # Pure Python package — no compiler settings needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Python dependencies: pybtex/pycurl/urwid are installed via pip in
        # build(). xapian Python bindings are NOT available on the pip mirror
        # (they are built from xapian-bindings source against xapian-core,
        # which is published to the ohpcd registry) — they are provided by
        # the build environment, see notes.md.
        self.requires("xapian-core/1.4.26")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (e.g. version.py fix), required by G1 check
        apply_conandata_patches(self)

        # Use sys.executable to get the full python path
        # (conan build env may not have pip in PATH)
        python_exe = sys.executable

        # Step 1: Install Python runtime dependencies needed by xapers.
        # xapian is intentionally NOT here — the xapian Python bindings are
        # not on the pip mirror; they must be present in the build
        # environment (built from xapian-bindings 1.4.26 source, see notes.md).
        self.run(
            f'{python_exe} -m pip install --break-system-packages '
            '"pybtex" "pycurl" "urwid"',
            env="conanrun",
        )

        # Step 2: Verify the xapian Python bindings are importable
        # (environment-provided; fail fast with a clear message otherwise)
        self.run(
            f'{python_exe} -c "import xapian"',
            env="conanrun",
        )

        # Step 3: Build and install the package to the package folder
        src_dir = self.source_folder
        self.run(
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--prefix="{self.package_folder}" "{src_dir}"',
            env="conanrun",
        )

    def package(self):
        # Files already installed to package_folder in build() via --prefix
        pass

    def package_info(self):
        # Set up environment for consumers
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        # Add bin to PATH
        self.cpp_info.bindirs = ["bin"]
        # Add Python lib path
        self.cpp_info.libdirs = [site_packages]

        # Set environment variables for consumers
        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PATH", bin_path)
        self.runenv_info.define("PYTHONPATH", lib_path)
