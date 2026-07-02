#!/usr/bin/env python3
"""Conan recipe for perl-signal-mask 0.008-r3 (Signal::Mask).

Pure Perl module — provides easy access to signal masks.
Build system: ExtUtils::MakeMaker (Makefile.PL).
Requires: IPC::Signal (installed at system Perl path).
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlSignalMaskConan(ConanFile):
    name = "perl-signal-mask"
    version = "0.008-r3"
    description = "Signal::Mask - Signal masks made easy (Pure Perl module)"
    license = "perl_5"
    homepage = "https://metacpan.org/dist/Signal-Mask"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def requirements(self):
        # IPC::Signal is a runtime dependency; if available as Conan pkg use @ohpcd/stable
        # self.requires("perl-ipc-signal/1.00@ohpcd/stable")
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Pure Perl module, no C/XS code — no toolchain needed
        pass

    def _get_perl5lib(self):
        """Build PERL5LIB from system Perl paths (for IPC::Signal dependency)."""
        parts = []

        # Add system Perl site_perl paths for runtime deps (IPC::Signal)
        for sys_path in [
            "/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0",
            "/storage/Users/currentUser/usr/local/lib/perl5",
            "/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0",
        ]:
            if os.path.isdir(sys_path):
                parts.append(sys_path)

        existing = os.environ.get("PERL5LIB", "")
        if existing:
            parts.append(existing)

        return ":".join(parts)

    def build(self):
        apply_conandata_patches(self)

        perl5lib = self._get_perl5lib()
        env_vars = [f"PERL5LIB={perl5lib}"]

        # R32: Platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        self.run("perl Makefile.PL INSTALLDIRS=site", cwd=self.source_folder, env=env_vars)
        self.run("make -j1", cwd=self.source_folder, env=env_vars)

    def package(self):
        perl5lib = self._get_perl5lib()
        env_vars = [f"PERL5LIB={perl5lib}"]

        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder, env=env_vars)

        # Copy Perl .pm files to lib/perl5 at package root
        for pm_file in glob.glob(os.path.join(staging, "**", "*.pm"), recursive=True):
            rel = os.path.relpath(pm_file, staging)
            parts = rel.split(os.sep)
            if 'site_perl' in parts:
                idx = parts.index('site_perl')
                target_rel = os.path.join('lib', 'perl5', *parts[idx:])
            else:
                target_rel = os.path.join('lib', 'perl5', rel)
            target = os.path.join(self.package_folder, target_rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            copy(self, os.path.basename(pm_file), src=os.path.dirname(pm_file), dst=os.path.dirname(target))

    def package_info(self):
        # Pure Perl module — libraries are .pm files in lib/perl5
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        # Set PERL5LIB for consumers — use glob to find the actual site_perl path
        for site_lib in glob.glob(os.path.join(self.package_folder, "lib", "perl5", "site_perl", "*")):
            if os.path.isdir(site_lib):
                self.runenv_info.append_path("PERL5LIB", site_lib)
                break
