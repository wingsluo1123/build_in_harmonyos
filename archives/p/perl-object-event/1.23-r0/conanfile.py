#!/usr/bin/env python3
"""Conan recipe — Perl module (ExtUtils::MakeMaker / Makefile.PL).

perl-object-event 1.23-r0 — Object::Event: Perl event callback interface

Runtime dependencies (Perl modules, not Conan packages):
  - common::sense  (user-installed, not in system Perl @INC)
  - AnyEvent        (user-installed, not in system Perl @INC)
  - Carp            (Perl core module)
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class PerlobjecteventConan(ConanFile):
    name = "perl-object-event"
    version = "1.23-r0"
    description = "Object::Event - Perl event callback interface"
    license = "perl"
    homepage = "https://metacpan.org/dist/Object-Event"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps: common::sense, AnyEvent are user-installed Perl modules
        # (not Conan packages, not in system Perl @INC in CI)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Use INSTALL_BASE=/ so files install to lib/perl5/ under DESTDIR
        self.run("perl Makefile.PL INSTALL_BASE=/")
        self.run("make -j1")

    def package(self):
        # Install to package folder using DESTDIR
        self.run(f"make install DESTDIR={self.package_folder}")

    def package_info(self):
        # Pure Perl module - no C libraries to link
        self.cpp_info.libs = []
        # Set PERL5LIB so consumers (test_package) can find Object::Event
        self.runenv_info.append_path("PERL5LIB", os.path.join(self.package_folder, "lib", "perl5"))
        # Dynamically add system Perl @INC paths for runtime dependencies
        # (common::sense, AnyEvent are user-installed, not in default @INC in CI)
        try:
            result = subprocess.run(
                ["perl", "-e", "print join(chr(58), grep { $_ ne q{.} && -d } @INC)"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                for inc_path in result.stdout.strip().split(":"):
                    inc_path = inc_path.strip()
                    if inc_path:
                        self.runenv_info.append_path("PERL5LIB", inc_path)
        except Exception:
        except Exception as e:
            self.output.warning(f"Failed to query system Perl @INC: {e}")
