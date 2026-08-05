#!/usr/bin/env python3
"""Conan recipe — black 26.5.1 (pure Python wheel).

Build:  pip wheel . --no-deps --no-build-isolation (with SETUPTOOLS_SCM_PRETEND_VERSION)
Install: extract wheel to <prefix>/lib/python3.X/site-packages, create bin/black wrapper
Type:   application (entry point: black = black:patched_main)
Deps:   click, mypy-extensions, packaging, pathspec, platformdirs, pytokens (pip installed)

R26 N/A (not system-name library); R38 applies (CLI tool, needs commands.json).
"""
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BlackConan(ConanFile):
    name = "black"
    version = "26.5.1"
    description = "Black is the uncompromising Python code formatter that reformats code into a consistent style"
    license = "MIT"
    homepage = "https://black.readthedocs.io/"
    url = "https://github.com/psf/black/archive/refs/tags/26.5.1.tar.gz"

    # Pure Python application, no C/C++ compilation
    package_type = "application"
    settings = "os", "arch"  # no compiler/build_type needed

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # GitHub tarball lacks src/_black_version.py (hatch-vcs generates it
        # from git metadata during sdist creation). Create it manually.
        version_file = os.path.join(self.source_folder, "src", "_black_version.py")
        if not os.path.exists(version_file):
            with open(version_file, "w") as f:
                f.write('version = "26.5.1"\n')

        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration(
                "python3 is required to build black; "
                "ensure python3 is on PATH")

        # Install build dependencies (hatchling build backend)
        self.run(
            f'"{python3}" -m pip install '
            f'hatchling hatch-vcs hatch-fancy-pypi-readme',
            env="conanbuild",
        )

        # pip wheel build (--no-deps: runtime deps provided by host Python env)
        wheel_dir = os.path.join(self.build_folder, "wheel")
        os.makedirs(wheel_dir, exist_ok=True)

        # SETUPTOOLS_SCM_PRETEND_VERSION: hatch-vcs needs version without git metadata
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION"] = "26.5.1"

        self.run(
            f'"{python3}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--no-build-isolation --wheel-dir="{wheel_dir}"',
            env="conanbuild",
        )

    def package(self):
        # Extract wheel to <prefix>/lib/python3.X/site-packages
        # Dynamic Python minor version: avoid hardcoding python3.12
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)

        wheel_dir = os.path.join(self.build_folder, "wheel")
        for whl in os.listdir(wheel_dir):
            if whl.endswith(".whl"):
                with zipfile.ZipFile(os.path.join(wheel_dir, whl)) as z:
                    z.extractall(site_pkg)
                break
        else:
            raise ConanInvalidConfiguration(
                f"No .whl file found in {wheel_dir}; "
                "pip wheel may have failed silently")

        # Create bin/black wrapper — sets PYTHONPATH to sibling site-packages
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "black")
        wrapper_content = (
            "#!/bin/sh\n"
            "# black wrapper — by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'if [ -d "$SITE_PKG/black" ]; then\n'
            '    PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            '        exec python3 -m black "$@"\n'
            'else\n'
            '    exec python3 -m black "$@"\n'
            'fi\n'
        )
        with open(wrapper, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper, 0o755)

    def package_info(self):
        # CLI tool: declare bindirs so conan knows executable location
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
