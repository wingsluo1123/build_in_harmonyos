#!/usr/bin/env python3
"""Conan recipe — perl-object-pad 0.821-r0 (Perl XS module, Module::Build)

Object::Pad - simple syntax for lexical field-based objects
Build system: perl Build.PL + ./Build (Module::Build with XS)
Produces: Pad.so (ELF64 AArch64 shared library) + .pm modules

Build dependencies (auto-installed to local Perl lib if not available):
  - Module::Build (build system, self-bootstrapping)
  - ExtUtils::CChecker (C compiler feature detection, used by XSPK Build.PL)
  - File::ShareDir (shared file location, used by XSPK Builder)
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

    # Perl build dependencies (CPAN official sources, R39)
    # Installed in order to local Perl lib if not pre-installed.
    _PERL_BUILD_DEPS = [
        ("Module-Build-0.4234",
         "https://cpan.metacpan.org/authors/id/L/LE/LEONT/Module-Build-0.4234.tar.gz",
         "66aeac6127418be5e471ead3744648c766bd01482825c5b66652675f2bc86a8f"),
        ("ExtUtils-CChecker-0.12",
         "https://cpan.metacpan.org/authors/id/P/PE/PEVANS/ExtUtils-CChecker-0.12.tar.gz",
         "8b87d145337dec1ee754d30871d0b105c180ad4c92c7dc0c7fadd76cec8c57d3"),
        ("Class-Inspector-1.36",
         "https://cpan.metacpan.org/modules/by-module/Class/Class-Inspector-1.36.tar.gz",
         "cc295d23a472687c24489d58226ead23b9fdc2588e522f0b5f0747741700694e"),
        ("File-ShareDir-1.118",
         "https://cpan.metacpan.org/modules/by-module/File/File-ShareDir-1.118.tar.gz",
         "3bb2a20ba35df958dc0a4f2306fc05d903d8b8c4de3c8beefce17739d281c958"),
        ("XS-Parse-Keyword-0.49",
         "https://cpan.metacpan.org/authors/id/P/PE/PEVANS/XS-Parse-Keyword-0.49.tar.gz",
         "76c5ed142abba1f1df2335849681c83d83cc0842fe854af71081d2c411efb0bb"),
        ("XS-Parse-Sublike-0.41",
         "https://cpan.metacpan.org/authors/id/P/PE/PEVANS/XS-Parse-Sublike-0.41.tar.gz",
         "a10f5e07273b105e5c0b4c6e7e2a6d2d2a68afe9ff4f989c11f38d4bf39cc86d"),
    ]

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

    def _get_local_perl_lib(self):
        """Get local Perl lib paths for deps installed during build().

        These paths are added to PERL5LIB in generate() so that
        dependencies installed in build()'s _ensure_perl_deps() are
        found by perl Build.PL and ./Build.
        """
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
        except Exception:
            archname = "aarch64-linux"

        local_base = os.path.join(self.build_folder, "perl5lib", "lib", "perl5")
        return [local_base, os.path.join(local_base, archname)]

    def _ensure_perl_deps(self):
        """Install Perl build dependencies if not already available.

        On dev machines, Module::Build and XS::Parse::*::Builder are
        pre-installed at $HOME/usr/local/lib/perl5/. On CI workers (clean
        environment), they are missing, causing 'Can't locate Module/Build.pm'
        at perl Build.PL time. This method detects the absence and installs
        all required deps to a local Perl lib directory within the build folder.
        """
        # Compute inc_flags for all perl commands (build() and package())
        # Even when deps are pre-installed, the -I paths simply don't exist
        # and Perl ignores them, so it's safe to always include them.
        local_lib = os.path.join(self.build_folder, "perl5lib")
        perl_path = shutil.which("perl")
        if not perl_path:
            for candidate in ["/data/service/hnp/bin/perl", "/usr/bin/perl"]:
                if os.path.isfile(candidate):
                    perl_path = candidate
                    break
        try:
            archname = subprocess.check_output(
                [perl_path, "-MConfig", "-e", "print $Config{archname}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            archname = "aarch64-linux"
        self._perl_inc_flags = (
            f"-I{local_lib}/lib/perl5 -I{local_lib}/lib/perl5/{archname}"
        )

        # Check if Module::Build is already available
        try:
            result = subprocess.run(
                ["perl", "-MModule::Build", "-e", "exit 0"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                self.output.info("Module::Build already available, skipping dep install")
                return
        except Exception:
            pass

        self.output.info("Module::Build not found, installing Perl build dependencies...")
        deps_dir = os.path.join(self.build_folder, "perl_deps")
        inc_flags = self._perl_inc_flags

        for dirname, url, sha256 in self._PERL_BUILD_DEPS:
            self.output.info(f"Installing {dirname}...")
            dep_dir = os.path.join(deps_dir, dirname)
            os.makedirs(dep_dir, exist_ok=True)
            get(self, url=url, sha256=sha256, destination=dep_dir, strip_root=True)
            if os.path.isfile(os.path.join(dep_dir, "Build.PL")):
                self.run(
                    f'cd "{dep_dir}" && perl {inc_flags} '
                    f'Build.PL --install_base="{local_lib}"',
                    env="conanbuild"
                )
                self.run(
                    f'cd "{dep_dir}" && perl {inc_flags} ./Build',
                    env="conanbuild"
                )
                self.run(
                    f'cd "{dep_dir}" && perl {inc_flags} '
                    f'./Build install --install_base="{local_lib}"',
                    env="conanbuild"
                )
            else:
                self.run(
                    f'cd "{dep_dir}" && perl {inc_flags} '
                    f'Makefile.PL INSTALL_BASE="{local_lib}"',
                    env="conanbuild"
                )
                self.run(f'cd "{dep_dir}" && make', env="conanbuild")
                self.run(f'cd "{dep_dir}" && make install', env="conanbuild")

        self.output.info("Perl build dependencies installed to local lib")

    def generate(self):
        """Generate env scripts for the conanbuild scope.

        Uses Conan's Environment class so that variables are properly
        sourced by self.run(cmd, env='conanbuild').
        """
        env = Environment()

        # PERL5LIB: find Module::Build and XS::Parse::*::Builder
        # Include both pre-installed paths and local lib (populated in build())
        perl_libs = self._resolve_perl_libs()
        local_libs = self._get_local_perl_lib()
        all_libs = perl_libs + local_libs
        if all_libs:
            env.define("PERL5LIB", os.pathsep.join(all_libs))
            self.output.info(f"PERL5LIB set to: {os.pathsep.join(all_libs)}")

        # R33: Derive compiler and sysroot paths from Conan config, no hardcoded paths
        cc_info = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(cc_info, str):
            cc_info = json.loads(cc_info)
        cc = cc_info.get("c", "clang") if cc_info else "clang"
        cxx = cc_info.get("cpp", "clang++") if cc_info else "clang++"

        # Resolve bare compiler names via PATH (R33: no hardcoded paths)
        if os.sep not in cc and "/" not in cc:
            cc_resolved = shutil.which(cc)
            if not cc_resolved:
                raise ConanInvalidConfiguration(
                    f"Compiler '{cc}' not found in PATH. "
                    "Configure tools.build:compiler_executables in your Conan profile."
                )
        else:
            cc_resolved = cc

        if os.sep not in cxx and "/" not in cxx:
            cxx_resolved = shutil.which(cxx) or cxx
        else:
            cxx_resolved = cxx

        # Set CC/CXX/LD in conanbuild env so Perl's ExtUtils::CBuilder
        # uses clang as linker driver instead of ld.lld. Perl's lddlflags
        # contains -fstack-protector-strong which ld.lld doesn't understand,
        # but clang (as driver) handles it correctly.
        env.define("CC", cc_resolved)
        env.define("CXX", cxx_resolved)
        env.define("LD", cc_resolved)

        # Resolve compiler symlink and derive sysroot:
        # clang at {sdk}/llvm/bin/clang -> sysroot at {sdk}/sysroot
        cc_real = os.path.realpath(cc_resolved)
        cc_bin_dir = os.path.dirname(cc_real)
        sdk_native = os.path.dirname(os.path.dirname(cc_bin_dir))
        sysroot = os.path.join(sdk_native, "sysroot")
        if os.path.isdir(sysroot):
            inc_paths = [
                os.path.join(sysroot, "usr", "include"),
                os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos"),
            ]
            env.define("CPATH", os.pathsep.join(
                p for p in inc_paths if os.path.isdir(p)))
            lib_paths = [
                os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos"),
                os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos"),
            ]
            env.define("LIBRARY_PATH", os.pathsep.join(
                p for p in lib_paths if os.path.isdir(p)))

        env.define("PERL_CANARY_STABILITY_NOPROMPT", "1")
        env.define("TMPDIR", os.environ.get("TMPDIR", "/tmp"))

        envvars = env.vars(self, scope="build")
        envvars.save_script("perl_object_pad_env")

    def build(self):
        apply_conandata_patches(self)

        # Install Perl build dependencies if not available (CI workers)
        self._ensure_perl_deps()
        inc = self._perl_inc_flags

        # Perl Module::Build: configure with install_base pointing to build dir
        prefix = os.path.join(self.build_folder, "perl_prefix")
        self.run(f"perl {inc} Build.PL --install_base={prefix}", env="conanbuild")
        self.run(f"perl {inc} ./Build", env="conanbuild")

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

        # Copy XS::Parse::Keyword and XS::Parse::Sublike runtime modules
        # These are runtime dependencies of Object::Pad. They are installed
        # to perl5lib during build() by _ensure_perl_deps(). Without packaging
        # them, the Perl API test in test_package cannot load Object::Pad.
        perl5lib_arch = os.path.join(
            self.build_folder, "perl5lib", "lib", "perl5", "aarch64-linux")
        if os.path.isdir(perl5lib_arch):
            # Copy XS .pm modules (XS/Parse/Keyword.pm, Sublike.pm, etc.)
            xs_src = os.path.join(perl5lib_arch, "XS")
            if os.path.isdir(xs_src):
                copy(self, "*.pm", src=xs_src,
                     dst=os.path.join(self.package_folder, "lib", "perl5",
                                      "aarch64-linux", "XS"))
            # Copy XS .so files (auto/XS/Parse/Keyword/Keyword.so, etc.)
            auto_xs_src = os.path.join(perl5lib_arch, "auto", "XS")
            if os.path.isdir(auto_xs_src):
                copy(self, "*.so", src=auto_xs_src,
                     dst=os.path.join(self.package_folder, "lib", "perl5",
                                      "aarch64-linux", "auto", "XS"))
            # Copy Sublike module
            sublike_src = os.path.join(perl5lib_arch, "Sublike")
            if os.path.isdir(sublike_src):
                copy(self, "*.pm", src=sublike_src,
                     dst=os.path.join(self.package_folder, "lib", "perl5",
                                      "aarch64-linux", "Sublike"))
            # Copy shared include headers for XS modules
            share_src = os.path.join(perl5lib_arch, "auto", "share", "module")
            if os.path.isdir(share_src):
                copy(self, "*.h", src=share_src,
                     dst=os.path.join(self.package_folder, "lib", "perl5",
                                      "aarch64-linux", "auto", "share", "module"))

    def package_info(self):
        # Pad.so is a Perl XS module loaded by Perl runtime via DynaLoader,
        # not linked by C/C++ consumers. No cpp_info.libs declaration needed
        # since the .so uses Perl naming (Pad.so, not libPad.so).
        self.cpp_info.libdirs = ["lib"]
