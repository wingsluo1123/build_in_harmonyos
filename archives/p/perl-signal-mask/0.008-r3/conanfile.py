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


def _find_ipc_signal_paths():
    """Dynamically find Perl lib paths containing IPC/Signal.pm.

    Searches system Perl site_perl, $HOME/usr/local/lib, and /usr/local/lib
    using glob — no subprocess or perl binary call required.
    """
    paths = []
    seen = set()

    # 1. System Perl site_perl (HNP-managed Perl installation)
    for p in glob.glob("/data/service/hnp/perl.org/perl_*/lib/site_perl/*/"):
        ap = os.path.abspath(p)
        if ap not in seen and os.path.exists(os.path.join(ap, "IPC", "Signal.pm")):
            paths.append(ap)
            seen.add(ap)

    # 2. $HOME/usr/local/lib paths (user-installed Perl modules)
    home = os.environ.get("HOME", "")
    if home:
        for sub in ["usr/local/lib/perl5", "usr/local/lib/site_perl",
                     "usr/local/lib/perl5/site_perl/*"]:
            for p in glob.glob(os.path.join(home, sub)):
                ap = os.path.abspath(p)
                if os.path.isdir(ap) and ap not in seen:
                    if os.path.exists(os.path.join(ap, "IPC", "Signal.pm")):
                        paths.append(ap)
                        seen.add(ap)

    # 3. /usr/local/lib paths
    for sub in ["perl5", "site_perl", "perl5/site_perl/*"]:
        for p in glob.glob(os.path.join("/usr/local/lib", sub)):
            ap = os.path.abspath(p)
            if os.path.isdir(ap) and ap not in seen:
                if os.path.exists(os.path.join(ap, "IPC", "Signal.pm")):
                    paths.append(ap)
                    seen.add(ap)

    return paths


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
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        self.run("perl Makefile.PL INSTALL_BASE=/", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)

        src_lib = os.path.join(staging, "lib")
        if not os.path.exists(src_lib):
            raise Exception(f"Package staging lib directory not found: {src_lib}")
        copy(self, "*", src_lib, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib/perl5"]
        self.cpp_info.libs = []
        perl_dirs = glob.glob(
            os.path.join(self.package_folder, "lib", "perl5", "*")
        )
        for perl_dir in perl_dirs:
            if os.path.isdir(perl_dir):
                self.runenv_info.append_path("PERL5LIB", perl_dir)
        base_perl = os.path.join(self.package_folder, "lib", "perl5")
        if os.path.isdir(base_perl):
            self.runenv_info.append_path("PERL5LIB", base_perl)

        for ipc_path in _find_ipc_signal_paths():
            self.runenv_info.append_path("PERL5LIB", ipc_path)
