#!/usr/bin/env python3
"""Conan recipe — perl-object-pad 0.821-r0 (Perl XS module, Module::Build)

Object::Pad - simple syntax for lexical field-based objects
Build system: perl Build.PL + ./Build (Module::Build with XS)
Produces: Pad.so (ELF64 AArch64 shared library) + .pm modules
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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

    def configure(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"perl-object-pad does not support os={self.settings.os}"
            )

    def requirements(self):
        # XS dependencies (managed by Conan or pre-installed)
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Derive sysroot paths from Conan config, no hardcoded user paths
        # Get compiler path from Conan profile configuration
        cc_info = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(cc_info, str):
            cc_info = json.loads(cc_info)
        cc = cc_info.get("c", "clang") if cc_info else "clang"

        # Resolve compiler path: if bare filename, search PATH
        if os.sep not in cc and "/" not in cc:
            cc_resolved = shutil.which(cc)
            if not cc_resolved:
                raise ConanInvalidConfiguration(
                    f"Compiler '{cc}' not found in PATH. "
                    "Configure tools.build:compiler_executables in your Conan profile."
                )
        else:
            cc_resolved = cc

        # Resolve compiler symlink and derive sysroot:
        # clang at {sdk}/llvm/bin/clang -> sysroot at {sdk}/sysroot
        cc_real = os.path.realpath(cc_resolved)
        cc_bin_dir = os.path.dirname(cc_real)          # .../llvm/bin
        sdk_native = os.path.dirname(os.path.dirname(cc_bin_dir))  # .../native
        sysroot = os.path.join(sdk_native, "sysroot")

        if os.path.isdir(sysroot):
            os.environ["CPATH"] = os.path.join(sysroot, "usr", "include")
            os.environ["LIBRARY_PATH"] = os.path.join(
                sysroot, "usr", "lib", "aarch64-linux-ohos"
            )

        os.environ["PERL_CANARY_STABILITY_NOPROMPT"] = "1"
        # Use system TMPDIR, fallback to /tmp (R33: no hardcoded user paths)
        os.environ.setdefault("TMPDIR", "/tmp")

        # Perl Module::Build: configure with install_base pointing to build dir
        prefix = os.path.join(self.build_folder, "perl_prefix")
        self.run(f"perl Build.PL --install_base={prefix}", env="conanbuild")
        self.run("./Build", env="conanbuild")

    def package(self):
        # Install to a staging directory
        stage = os.path.join(self.build_folder, "stage")
        self.run(f"./Build install --install_base={stage}", env="conanbuild")

        # Copy .so to lib/ (standard Conan layout for G4 check)
        copy(self, "Pad.so",
             src=os.path.join(stage, "lib", "perl5", "aarch64-linux", "auto", "Object", "Pad"),
             dst=os.path.join(self.package_folder, "lib"))
        # Copy .so to Perl auto directory for DynaLoader
        copy(self, "Pad.so",
             src=os.path.join(stage, "lib", "perl5", "aarch64-linux", "auto", "Object", "Pad"),
             dst=os.path.join(self.package_folder, "lib", "perl5", "aarch64-linux", "auto", "Object", "Pad"))
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
        # Pad.so is a Perl XS module loaded by Perl runtime via DynaLoader,
        # not linked by C/C++ consumers. No cpp_info.libs declaration needed
        # since the .so uses Perl naming (Pad.so, not libPad.so).
        self.cpp_info.libdirs = ["lib"]
