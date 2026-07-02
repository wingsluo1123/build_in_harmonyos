#!/usr/bin/env python3
"""Conan recipe for perl-net-xmpp 1.05-r0 (pure Perl module).

Net::XMPP - XMPP Support Library
Build system: Perl Module::Build (via Makefile.PL compat wrapper).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlNetXmppConan(ConanFile):
    name = "perl-net-xmpp"
    version = "1.05-r0"
    description = "XMPP Support Library"
    license = "LGPL-2.1-or-later"
    homepage = "https://metacpan.org/dist/Net-XMPP"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime dependencies (Perl modules available in system Perl)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl module: perl Makefile.PL + make
        # Makefile.PL is a Module::Build::Compat wrapper around Build.PL
        self.run("perl Makefile.PL", env="conanbuild")
        self.run("make", env="conanbuild")

    def package(self):
        # Install to package directory using make install with DESTDIR
        self.run(f'make install DESTDIR="{self.package_folder}"', env="conanbuild")

        # Module::Build installs to system Perl site_perl path under DESTDIR,
        # which creates a deeply nested path. Copy .pm files to lib/ at the
        # package root so Conan's G4 artifact integrity check can find them.
        src_base = os.path.join(self.package_folder, "data", "service", "hnp")
        perl_lib = None
        if os.path.isdir(src_base):
            # Walk to find the site_perl lib directory containing Net/XMPP.pm
            for root, dirs, files in os.walk(src_base):
                if "XMPP.pm" in files and root.endswith(os.path.join("Net")):
                    perl_lib = os.path.dirname(root)  # parent of Net/
                    break

        if perl_lib and os.path.isdir(perl_lib):
            # Copy Net/ directory (contains XMPP.pm and XMPP/ subdir) to lib/
            dest_lib = os.path.join(self.package_folder, "lib")
            net_src = os.path.join(perl_lib, "Net")
            net_dst = os.path.join(dest_lib, "Net")
            if os.path.isdir(net_src):
                os.makedirs(net_dst, exist_ok=True)
                for item in os.listdir(net_src):
                    s = os.path.join(net_src, item)
                    d = os.path.join(net_dst, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

    def package_info(self):
        # Perl module - expose as a Perl library path
        perl_lib = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(perl_lib):
            perl_lib = os.path.join(self.package_folder, "usr", "local", "lib", "perl5")
        self.cpp_info.libdirs = [perl_lib] if os.path.isdir(perl_lib) else []
        self.cpp_info.libs = []  # Pure Perl module, no compiled libs
