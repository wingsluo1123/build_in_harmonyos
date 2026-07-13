#!/usr/bin/env python3
"""Conan recipe for homebrew 5.1.12 — script-based package."""
from conan import ConanFile
from conan.tools.files import get, chdir, copy, save, replace_in_file, apply_conandata_patches, export_conandata_patches
import os


class HomebrewConan(ConanFile):
    name = "homebrew"
    version = "5.1.12"
    description = "Homebrew - The missing package manager for macOS (or Linux)"
    license = "MIT"
    homepage = "https://brew.sh"
    url = "https://github.com/Homebrew/brew/archive/refs/tags/5.1.12.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bash and ruby are system-provided on OHOS
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebangs for OHOS where bash is at /data/service/hnp/bin/bash
        self.output.info("Fixing shebangs for OHOS (E165)...")
        for root, dirs, files in os.walk(self.source_folder):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                        first_line = fh.readline()
                    if first_line.startswith('#!/bin/bash') or first_line.startswith('#!/bin/sh'):
                        if first_line.startswith('#!/bin/bash'):
                            replace_in_file(self, fpath, '#!/bin/bash', '#!/data/service/hnp/bin/bash')
                        elif first_line.startswith('#!/bin/sh'):
                            replace_in_file(self, fpath, '#!/bin/sh', '#!/system/bin/sh')
                except Exception:
                    pass

    def package(self):
        # Copy all files
        self.output.info("Packaging homebrew scripts...")
        copy(self, "*", src=self.source_folder, dst=os.path.join(self.package_folder, "Homebrew"))

        # Create bin/ with the main entry point
        bin_dir = os.path.join(self.package_folder, "bin")
        save(self, os.path.join(bin_dir, "brew"),
             "#!/usr/bin/env bash\n"
             'cd "$(dirname "$0")/../Homebrew" && exec bin/brew "$@"\n')
        os.chmod(os.path.join(bin_dir, "brew"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # System dependencies: bash >= 5.0, ruby >= 3.0 (pre-installed on OHOS)
