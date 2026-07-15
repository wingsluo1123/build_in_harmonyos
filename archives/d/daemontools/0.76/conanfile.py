#!/usr/bin/env python3
"""Conan recipe for daemontools 0.76 — DJB service management tools.

daemontools is a collection of tools by D.J. Bernstein for managing UNIX
services (supervise, svscan, svc, multilog, tai64n, etc.).

Build system: DJB custom Makefile (no configure, no autotools).
Compiler configured via conf-cc/conf-ld files (patches set to clang).
Install prefix configured via 'home' file (created in build()).
No 'make install' target — binaries copied manually.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DaemontoolsConan(ConanFile):
    name = "daemontools"
    version = "0.76"
    description = "Collection of tools for managing UNIX services"
    license = "LicenseRef-Homebrew-public-domain"
    homepage = "https://cr.yp.to/daemontools.html"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # DJB tarball has nested structure: admin/daemontools-0.76/src/
        get(self, **self.conan_data["sources"], strip_root=False)

        # Promote src/ contents to source folder root
        src_dir = os.path.join(self.source_folder, "admin", "daemontools-0.76", "src")
        for item in os.listdir(src_dir):
            shutil.move(os.path.join(src_dir, item), os.path.join(self.source_folder, item))
        shutil.rmtree(os.path.join(self.source_folder, "admin"), ignore_errors=True)

    def build(self):
        apply_conandata_patches(self)

        # DJB build system: create 'home' file with install prefix
        # (choose/svscanboot scripts embed this path at build time)
        with open(os.path.join(self.source_folder, "home"), "w") as f:
            f.write(self.package_folder)

        # DJB uses conf-cc/conf-ld (patches set to clang), no configure script
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # DJB produces executables, copy all built binaries to bin/
        bins = [
            "envdir", "envuidgid", "fghack", "multilog", "pgrphack",
            "readproctitle", "setlock", "setuidgid", "softlimit",
            "supervise", "svc", "svok", "svscan", "svscanboot",
            "svstat", "tai64n", "tai64nlocal",
        ]
        for bin_name in bins:
            copy(self, bin_name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # ELF signing for HarmonyOS (E082)
        import subprocess
        bin_dir = os.path.join(self.package_folder, "bin")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        for bin_name in bins:
            bin_path = os.path.join(bin_dir, bin_name)
            if os.path.exists(bin_path):
                tmp_signed = bin_path + ".signed"
                # Remove existing .codesign section if present (non-fatal if absent)
                subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                               capture_output=True)
                # Sign the binary for HarmonyOS execution
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path,
                     "-outFile", tmp_signed, "-selfSign", "1"],
                    capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(tmp_signed):
                    os.replace(tmp_signed, bin_path)
                    os.chmod(bin_path, 0o755)
                else:
                    self.output.warning(f"ELF signing failed for {bin_name}: {result.stderr}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
