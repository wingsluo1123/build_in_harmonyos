#!/usr/bin/env python3
"""Conan recipe for you-get 0.4.1743 — command-line video downloader.

you-get is a pure Python tool (no C/C++ extensions in the package
itself). It provides a command-line interface for downloading
video/audio from YouTube, Bilibili and 100+ other web sites.

Build:  none (pure Python — src/you_get copied straight to
        site-packages; no wheel build)
Install: copy src/you_get to <prefix>/lib/python3.X/site-packages,
         create bin/you-get wrapper
Type:   application (console_scripts: you-get = you_get.__main__:main)

Deps:   upstream declares install_requires=['dukpy'], but dukpy is
        imported only by src/you_get/extractors/youtube.py inside a
        try/except ImportError (log + exit(0)); the CLI entry
        (`you-get --version` / non-YouTube downloads) does NOT need
        it. There is no dukpy recipe in the artifact repository and
        CI has no external pip network, so dukpy is deliberately NOT
        a Conan dependency (see notes.md).

R26: Not applicable (pure Python, no .so / no system-name collision).
R32: settings.os must check in ("Linux", "OHOS").
R38: Command-line tool — commands.json declared at software level.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class YouGetConan(ConanFile):
    name = "you-get"
    version = "0.4.1743"
    description = "A command-line downloader for video/audio from YouTube, Bilibili and 100+ other web sites"
    license = "MIT"
    homepage = "https://github.com/soimort/you-get"
    url = "https://github.com/soimort/you-get"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure-Python package: nothing to compile and no wheel build.
        # Deliberately NOT running `pip wheel . --no-deps` here: pip's
        # build isolation spawns nested subprocesses to install its build
        # backend, which fails with [Errno 11] (EAGAIN / Resource
        # temporarily unavailable) on the resource-constrained OHOS CI
        # worker. The wheel content is exactly the committed src/you_get
        # tree (setup.py uses find_packages('src'), and src/you_get/
        # version.py is versioned upstream), so package() copies it
        # directly — no subprocesses, no setuptools dependency.
        pass

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)

        # Install the pure-Python package by copying src/you_get directly
        # (equivalent to extracting the wheel minus the .dist-info
        # metadata, which neither the launcher nor the tests require).
        shutil.copytree(
            os.path.join(self.source_folder, "src", "you_get"),
            os.path.join(site_pkg, "you_get"),
        )

        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "you-get")
        wrapper_content = (
            "#!/bin/sh\n"
            "# you-get wrapper — by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'if [ -d "$SITE_PKG/you_get" ]; then\n'
            '    PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            '        exec python3 -m you_get "$@"\n'
            'else\n'
            '    exec python3 -m you_get "$@"\n'
            'fi\n'
        )
        with open(wrapper, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper, 0o755)

        from conan.tools.files import copy
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PYTHONPATH", site_pkg)
        self.runenv_info.prepend_path("PATH", bin_dir)
