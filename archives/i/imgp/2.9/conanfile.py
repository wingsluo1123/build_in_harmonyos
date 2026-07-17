#!/usr/bin/env python3
"""Conan recipe for imgp — Python CLI image resizer/rotator.

imgp is a pure Python CLI tool that uses Pillow for image processing.
It is installed via pip from the PyPI source tarball.
System Python (pre-installed via cmd-pkgs) is used at build and run time.
"""
import os, sys

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class ImgpConan(ConanFile):
    name = "imgp"
    version = "2.9"
    description = "High-performance CLI batch image resizer & rotator"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jarun/imgp"
    url = "https://github.com/jarun/imgp"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Use system Python (pre-installed via cmd-pkgs)
        python = "python3"

        # Change to the source directory since pip needs to find setup.py
        src_dir = self.source_folder

        # Install setuptools (needed by setup.py) and pillow (pre-built wheel for OHOS)
        self.run(f"{python} -m pip install setuptools pillow", env="conanrun")
        # Install imgp from source directory (pillow already installed)
        # Use pip install . which handles build dependencies properly
        self.run(f"cd {src_dir} && {python} -m pip install .", env="conanrun")

    def package(self):
        # Find the installed files from the system Python
        python = "python3"
        python_bin = os.path.join(os.sep, "usr", "local", "bin")

        # Try to find the Python bin directory
        import subprocess
        try:
            result = subprocess.run([python, "-c", "import sys; print(sys.executable)"],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                python_bin = os.path.dirname(result.stdout.strip())
        except Exception:
            pass

        # Copy imgp executable
        copy(self, "imgp*", python_bin, os.path.join(self.package_folder, "bin"))

        # Try to find installed imgp files
        py_ver = "python3.12"
        for site_dir in [
            f"/usr/local/lib/{py_ver}/site-packages",
            f"/usr/lib/{py_ver}/site-packages",
            os.path.expanduser(f"~/usr/local/lib/{py_ver}/site-packages"),
        ]:
            if os.path.isdir(site_dir):
                dest = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
                # Copy imgp module
                copy(self, "imgp.py*", site_dir, dest)
                copy(self, "imgp-*.egg-info*", site_dir, dest)
                # Copy PIL (pillow) - runtime dependency
                pil_dir = os.path.join(site_dir, "PIL")
                if os.path.isdir(pil_dir):
                    copy(self, "*", pil_dir, os.path.join(dest, "PIL"))
                # Copy PIL dist-info
                for f in os.listdir(site_dir):
                    if f.startswith("PIL") and f.endswith("dist-info"):
                        copy(self, f, site_dir, dest)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []