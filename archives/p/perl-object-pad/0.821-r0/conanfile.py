#!/usr/bin/env python3
"""Conan recipe — perl-object-pad 0.821-r0 (Perl XS module, Module::Build)

Object::Pad - simple syntax for lexical field-based objects
Build system: perl Build.PL + ./Build (Module::Build with XS)
Produces: Pad.so (ELF64 AArch64 shared library) + .pm modules

Build dependencies (pre-installed at $HOME/usr/local/lib/perl5/):
  - Module::Build (build system)
  - XS::Parse::Keyword::Builder (compiler flag provider)
  - XS::Parse::Sublike::Builder (compiler flag provider)
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
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

    def _resolve_perl_libs(self):
        """Find pre-installed Perl build dependencies dynamically (R33).

        Module::Build, XS::Parse::Keyword::Builder, and
        XS::Parse::Sublike::Builder are pre-installed at
        $HOME/usr/local/lib/perl5/ but are not in Perl's default @INC.
        Returns a list of existing directory paths.
        """
        home = os.environ.get("HOME", "")
        if not home:
            self.output.info("PERL5LIB: HOME not set, skipping")
            return []

        # Find perl binary: subprocess may not have same PATH as self.run()
        perl_path = shutil.which("perl")
        if not perl_path:
            for candidate in [
                "/data/service/hnp/bin/perl",
                "/usr/bin/perl",
                "/usr/local/bin/perl",
            ]:
                if os.path.isfile(candidate):
                    perl_path = candidate
                    break
        if not perl_path:
            return []

        try:
            archname = subprocess.check_output(
                [perl_path, "-MConfig", "-e", "print $Config{archname}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            perl_ver = subprocess.check_output(
                [perl_path, "-MConfig", "-e", "print $Config{version}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception as e:
            self.output.info(f"PERL5LIB: Failed to query perl config: {e}")
            return []

        perl5_base = os.path.join(home, "usr", "local", "lib", "perl5")
        candidate_libs = [
            perl5_base,  # Module::Build and pure Perl modules
            os.path.join(perl5_base, archname) if archname else "",  # XS Builder modules
            os.path.join(perl5_base, "site_perl", perl_ver) if perl_ver else "",  # File::ShareDir
        ]
        found = [p for p in candidate_libs if p and os.path.isdir(p)]
        return found

    def generate(self):
        """Generate env scripts for the conanbuild scope.

        Uses Conan's Environment class so that variables are properly
        sourced by self.run(cmd, env='conanbuild').
        """
        env = Environment()

        # PERL5LIB: find Module::Build and XS::Parse::*::Builder
        perl_libs = self._resolve_perl_libs()
        if perl_libs:
            env.define("PERL5LIB", os.pathsep.join(perl_libs))
            self.output.info(f"PERL5LIB set to: {os.pathsep.join(perl_libs)}")

        # R33: Derive sysroot paths from Conan config, no hardcoded user paths
        cc_info = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(cc_info, str):
            cc_info = json.loads(cc_info)
        cc = cc_info.get("c", "clang") if cc_info else "clang"

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
        cc_bin_dir = os.path.dirname(cc_real)
        sdk_native = os.path.dirname(os.path.dirname(cc_bin_dir))
        sysroot = os.path.join(sdk_native, "sysroot")
        if os.path.isdir(sysroot):
            env.define("CPATH", os.path.join(sysroot, "usr", "include"))
            env.define("LIBRARY_PATH", os.path.join(
                sysroot, "usr", "lib", "aarch64-linux-ohos"))

        env.define("PERL_CANARY_STABILITY_NOPROMPT", "1")
        env.define("TMPDIR", os.environ.get("TMPDIR", "/tmp"))

        envvars = env.vars(self, scope="build")
        envvars.save_script("perl_object_pad_env")

    def build(self):
        apply_conandata_patches(self)

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
