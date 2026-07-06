#!/usr/bin/env python3
"""Conan recipe for bossa 1.9.1 — Makefile executable package.

BOSSA (Basic Open Source SAM-BA Application) is a flash programmer for
Atmel SAM microcontrollers. This recipe builds the CLI tool bossac only.
bossash (interactive shell) requires readline and is not included.
The GUI version (bossa) requires wxWidgets and is not available on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BossaConan(ConanFile):
    name = "bossa"
    version = "1.9.1"
    description = "Flash programmer for Atmel SAM microcontrollers (CLI tool: bossac)"
    license = "MIT"
    homepage = "https://github.com/shumatech/BOSSA"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Touch pre-generated WordCopyArm.cpp to prevent applet regeneration
        # (arm-none-eabi-as not available on OHOS)
        applet_cpp = os.path.join(self.source_folder, "src", "WordCopyArm.cpp")
        if os.path.exists(applet_cpp):
            os.utime(applet_cpp, None)

        # bossa Makefile detects OS via uname -s | cut -c -7 = "Harmon" on OHOS,
        # which matches no OS rule. Pass OS=Linux to get PosixSerialPort support.
        # Build only bin/bossac (not all, which includes GUI needing wxWidgets).
        # VERSION must be set manually (Makefile uses git describe; source is not git).
        # Create dummy wx-config to silence parse-time $(shell wx-config) calls
        # (only bossa GUI needs wxWidgets; we build bossac only)
        dummy_bin = os.path.join(self.build_folder, "dummy_bin")
        os.makedirs(dummy_bin, exist_ok=True)
        wx_config = os.path.join(dummy_bin, "wx-config")
        with open(wx_config, "w") as f:
            f.write("#!/system/bin/sh\necho ''\n")
        os.chmod(wx_config, 0o755)

        # Add dummy_bin to PATH for this make invocation
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = dummy_bin + os.pathsep + old_path

        # CXXFLAGS=-Wno-error overrides Makefile's -Werror (std::move unqualified call)
        # Run from source_folder because Makefile is at root, not in build subdir.
        self.run("make CXX=clang++ VERSION=1.9.1 OS=Linux CXXFLAGS=-Wno-error -j1 bin/bossac",
                 cwd=self.source_folder)

        # Restore PATH
        os.environ["PATH"] = old_path

    def package(self):
        # Copy executable to bin/
        copy(self, "bossac", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Executable package — no libraries to link
        self.cpp_info.bindirs = ["bin"]
