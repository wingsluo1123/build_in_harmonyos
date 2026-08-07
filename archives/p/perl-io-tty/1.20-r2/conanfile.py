#!/usr/bin/env python3
"""Conan recipe — perl-io-tty 1.20-r2 (Perl XS module: IO::Tty)

Build system: perl Makefile.PL (ExtUtils::MakeMaker)
Output: Tty.so (XS shared library) + Pty.pm, Tty.pm, Constant.pm (pure Perl)

OHOS adaptation:
  - Hardcode PTY/TTY function detection (CRT files missing)
  - Use -c flag for compile-only checks (avoid linking)
  - Restore symbol detection with -c flag (properly detect undefined symbols)
  - OTHERLDFLAGS: -nostartfiles -nodefaultlibs -lc (missing CRT files)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlIoTtyConan(ConanFile):
    name = "perl-io-tty"
    version = "1.20-r2"
    description = "Perl module for PTY/TTY operations - pseudo terminal interfaces"
    license = "GPL-1.0-or-later"
    homepage = "https://metacpan.org/pod/IO::Tty"
    url = ""  # CI fills this

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R32: Only build on supported platforms
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

        perl = "/data/service/hnp/bin/perl"
        src = self.source_folder

        # Configure: perl Makefile.PL
        # PERL_MM_OPT passes extra linker flags for missing CRT files
        os.environ["PERL_MM_OPT"] = "LDFLAGS=-nostartfiles -nodefaultlibs"
        self.run(f"{perl} Makefile.PL", cwd=src)

        # Build with extra linker flags for missing CRT files
        self.run('make OTHERLDFLAGS="-nostartfiles -nodefaultlibs -lc" -j1', cwd=src)

    def package(self):
        src = self.source_folder
        # Copy XS module (.so)
        copy(self, "Tty.so",
             os.path.join(src, "blib/arch/auto/IO/Tty"),
             os.path.join(self.package_folder, "lib/auto/IO/Tty"))
        # Copy pure Perl modules
        copy(self, "*.pm",
             os.path.join(src, "blib/lib"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["Tty"]
        self.cpp_info.libdirs = ["lib/auto/IO/Tty"]
