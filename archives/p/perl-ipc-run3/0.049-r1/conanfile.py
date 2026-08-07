#!/usr/bin/env python3
"""Conan recipe — Perl EUMM (ExtUtils::MakeMaker) module.
perl-ipc-run3 0.049-r1 — IPC::Run3: run subprocesses with I/O redirection.
Pure Perl module, no C/C++ compilation.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlIpcRun3Conan(ConanFile):
    name = "perl-ipc-run3"
    version = "0.049-r1"
    description = "IPC::Run3 - run a subprocess with I/O redirection (pure Perl)"
    license = "open_source"
    homepage = "https://metacpan.org/pod/IPC::Run3"
    url = ""

    # Pure Perl module — only os and arch matter
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.run("perl Makefile.PL INSTALLDIRS=site", env="conanrun")
        self.run("make -j1", env="conanrun")

    def package(self):
        self.run('make install DESTDIR="{}"'.format(self.package_folder), env="conanrun")
        # Copy .pm files to lib/ for Conan artifact detection (G4)
        # With INSTALLDIRS=site, Perl installs to data/service/hnp/perl.org/... path
        pm_files = glob.glob(os.path.join(self.package_folder, "**", "*.pm"), recursive=True)
        for pm in pm_files:
            rel = os.path.relpath(pm, self.package_folder)
            # Find site_perl in the path and rebase to lib/
            parts = rel.split(os.sep)
            if "site_perl" in parts:
                idx = parts.index("site_perl")
                target_rel = os.path.join("lib", *parts[idx:])
            else:
                target_rel = os.path.join("lib", rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm), src=os.path.dirname(pm), dst=os.path.dirname(target))

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        perl_site_lib = os.path.join(self.package_folder, "lib", "site_perl", "5.42.0")
        self.runenv_info.append_path("PERL5LIB", perl_site_lib)
