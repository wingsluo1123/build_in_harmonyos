#!/usr/bin/env python3
"""Conan recipe for perl-parallel-pipes (Parallel::Pipes) — pure Perl module.

Parallel::Pipes provides parallel processing using pipe(2) for communication
and synchronization. This is a pure Perl module using Module::Build::Tiny
as its build system.

Build steps: perl Build.PL → ./Build → ./Build install
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlparallelpipesConan(ConanFile):
    name = "perl-parallel-pipes"
    version = "0.201"
    description = "Parallel processing using pipe(2) for communication and synchronization"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://github.com/skaji/Parallel-Pipes"
    url = ""  # CI fills this

    # Pure Perl module — no compiler/build_type needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Pure Perl module — no C/C++ layout needed
        # Using pass instead of basic_layout to avoid 'build' directory
        # conflicting with Module::Build::Tiny's 'Build' script on
        # case-insensitive filesystems
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any (none for this module)
        apply_conandata_patches(self)
        # Module::Build::Tiny workflow
        self.run("perl Build.PL")
        self.run("./Build")

    def package(self):
        # Install to a temporary staging dir, then reorganize into lib/
        staging = os.path.join(self.package_folder, "_staging")
        self.run(f"./Build install --destdir {staging}")
        # Find the installed .pm files and copy them to lib/ at package root
        # so that G4 (product integrity check) can find standard lib/ directory
        pm_files = glob.glob(os.path.join(staging, "**", "Parallel", "Pipes.pm"), recursive=True)
        if not pm_files:
            shutil.rmtree(staging, ignore_errors=True)
            raise Exception("Parallel/Pipes.pm not found in staging — package is empty, upstream install layout may have changed")
        if pm_files:
            # Determine the Perl lib root (parent of Parallel/)
            perl_lib_root = os.path.dirname(os.path.dirname(pm_files[0]))
            pkg_lib = os.path.join(self.package_folder, "lib")
            # Copy all files from perl_lib_root to pkg_lib preserving structure
            for root, dirs, files in os.walk(perl_lib_root):
                rel = os.path.relpath(root, perl_lib_root)
                dst = os.path.join(pkg_lib, rel) if rel != "." else pkg_lib
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    shutil.copy2(os.path.join(root, f), os.path.join(dst, f))
        # Remove the temporary staging directory
        shutil.rmtree(staging, ignore_errors=True)

    def package_info(self):
        # Pure Perl module — no C/C++ libraries to link
        # R26 note: static linking not applicable (no native binaries)
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers can find the Perl module
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            self.runenv_info.define_path("PERL5LIB", lib_dir)
