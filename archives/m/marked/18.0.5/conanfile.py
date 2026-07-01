#!/usr/bin/env python3
"""Conan recipe for marked 18.0.5 — JavaScript markdown parser (npm/esbuild).

marked is a low-level compiler for parsing markdown without caching or blocking
for long periods of time. It is written in TypeScript and bundled with esbuild.

Build system: npm (package.json + esbuild + TypeScript)
No C/C++ compilation required — pure JavaScript library.

Packaging strategy: The built JS/TS output (lib/, bin/, man/) is packaged
as data files. Consumers use NODE_PATH to locate the module.
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MarkedConan(ConanFile):
    name = "marked"
    version = "18.0.5"
    description = "A markdown parser built for speed"
    license = "MIT"
    homepage = "https://github.com/markedjs/marked"
    url = ""

    # R32: settings.os check must use in ("Linux", "OHOS")
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # JavaScript dependencies are installed via npm in build(), not as Conan requires
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (none currently, but required by G1 check)
        apply_conandata_patches(self)

        src_dir = self.source_folder

        # Step 1: Install npm dependencies
        self.run(f'cd "{src_dir}" && npm install', env="conanrun")

        # Step 2: Build the library (esbuild + TypeScript + man page)
        self.run(f'cd "{src_dir}" && npm run build', env="conanrun")

    def package(self):
        src_dir = self.source_folder
        pkg = self.package_folder

        # Install structure: lib/node_modules/marked/
        dest = os.path.join(pkg, "lib", "node_modules", "marked")
        os.makedirs(dest, exist_ok=True)

        # Copy built artifacts
        for item in ["lib", "bin", "man", "package.json"]:
            src = os.path.join(src_dir, item)
            if os.path.exists(src):
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(dest, item), dirs_exist_ok=True)
                else:
                    shutil.copy2(src, os.path.join(dest, item))

    def package_info(self):
        # Node.js module path for consumers
        node_modules_path = os.path.join(self.package_folder, "lib", "node_modules")
        bin_path = os.path.join(self.package_folder, "lib", "node_modules", "marked", "bin")

        # Set up environment for consumers
        self.cpp_info.bindirs = [os.path.join("lib", "node_modules", "marked", "bin")]
        self.cpp_info.libdirs = [os.path.join("lib", "node_modules")]

        # Environment variables for consumers
        self.runenv_info.define("NODE_PATH", node_modules_path)
        self.runenv_info.append("PATH", bin_path)
