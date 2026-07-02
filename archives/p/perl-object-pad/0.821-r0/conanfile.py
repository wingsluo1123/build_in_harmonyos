#!/usr/bin/env python3
"""Conan recipe — perl-object-pad 0.821-r0 (Perl XS module, Module::Build)

Object::Pad - simple syntax for lexical field-based objects
Build system: perl Build.PL + ./Build (Module::Build with XS)
Produces: Pad.so (ELF64 AArch64 shared library) + .pm modules
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PerlobjectpadConan(ConanFile):
    name = "perl-object-pad"
    version = "0.821-r0"
    description = "simple syntax for lexical field-based objects"
    license = "Artistic-1.0-Perl"
    homepage = "https://metacpan.org/dist/Object-Pad"
    url = ""  # CI fills this

    # R32: Support both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # XS dependencies (managed by Conan or pre-installed)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Set up HarmonyOS-specific environment for XS module compilation
        import os
        cpath = "/storage/Users/currentUser/usr/local/include"
        libpath = "/storage/Users/currentUser/usr/local/lib"
        os.environ["CPATH"] = cpath
        os.environ["LIBRARY_PATH"] = libpath
        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        os.environ["TMPDIR"] = "/storage/Users/currentUser/tmp"
        # Perl Module::Build: configure with install_base pointing to build dir
        prefix = os.path.join(self.build_folder, "perl_prefix")
        self.run(f"perl Build.PL --install_base={prefix}", env="conanbuild")
        self.run("./Build", env="conanbuild")

    def package(self):
        import os
        # Install to a staging directory
        stage = os.path.join(self.build_folder, "stage")
        self.run(f"./Build install --install_base={stage}", env="conanbuild")

        # Copy .so to lib/ (standard Conan layout for G4 check)
        copy(self, "Pad.so",
             src=os.path.join(stage, "lib", "perl5", "aarch64-linux", "auto", "Object", "Pad"),
             dst=os.path.join(self.package_folder, "lib"))
        # Copy header to include/
        copy(self, "object_pad.h",
             src=os.path.join(stage, "lib", "perl5", "aarch64-linux", "auto", "share", "module", "Object-Pad", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # Copy .pm files to lib/perl5/ (preserve Perl directory structure)
        copy(self, "*.pm",
             src=os.path.join(stage, "lib", "perl5", "aarch64-linux"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))
        # Copy .pod files
        copy(self, "*.pod",
             src=os.path.join(stage, "lib", "perl5", "aarch64-linux"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

    def package_info(self):
        # XS module .so file
        self.cpp_info.libs = ["Pad"]
        self.cpp_info.libdirs = ["lib"]
