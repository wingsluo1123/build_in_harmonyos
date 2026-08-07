#!/usr/bin/env python3
"""Conan recipe — Pod::Wrap (pure Perl module).

Wrap pod paragraphs, leaving verbatim text and code alone.
Built with ExtUtils::MakeMaker (Makefile.PL).
Pure Perl — no XS, no compiled libraries.

Dependencies:
  - Pod::Parser: removed from Perl 5.36+ core, pre-installed on OHOS worker
  - Text::Wrap: Perl core module (always available)

R32: settings.os check uses `in ("Linux", "OHOS")`
R33: No shell env vars for compiler — pure Perl, no compiler needed
"""
import os
import subprocess
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlPodWrapConan(ConanFile):
    name = "perl-pod-wrap"
    version = "0.01"
    description = "Wrap pod paragraphs, leaving verbatim text and code alone (pure Perl module)"
    license = "GPL-1.0-or-later OR Artistic-1.0"
    homepage = "https://metacpan.org/dist/Pod-Wrap"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Pure Perl module — no compiler/build_type needed
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan dependencies — Pod::Parser is a system Perl module
        # (pre-installed on OHOS CI workers at ~/usr/local/lib/site_perl/)
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_perl5lib(self):
        """Construct PERL5LIB for Pod::Parser (removed from Perl 5.36+ core).

        Detects Perl version dynamically and locates the site_perl directory
        where Pod::Parser is pre-installed on OHOS workers.
        """
        home = os.path.expanduser("~")
        # Detect Perl version (e.g. "5.42.0" → "5.42.0")
        try:
            result = subprocess.run(
                ["perl", "-e", "print $]"],
                capture_output=True, text=True, timeout=10
            )
            perl_ver_full = result.stdout.strip()  # e.g. "5.042000"
            # Convert to x.y.z format
            major = int(float(perl_ver_full))
            minor = int((float(perl_ver_full) * 1000) % 1000)
            perl_ver = f"{major}.{minor // 100}.0"
        except Exception:
            perl_ver = "5.42.0"  # Fallback to known OHOS Perl version

        parts = []
        site_perl = os.path.join(home, "usr", "local", "lib", "site_perl", perl_ver)
        std_perl = os.path.join(home, "usr", "local", "lib", perl_ver)
        if os.path.isdir(site_perl):
            parts.append(site_perl)
        if os.path.isdir(std_perl):
            parts.append(std_perl)

        existing = os.environ.get("PERL5LIB", "")
        if existing:
            parts.insert(0, existing)
        return ":".join(parts) if parts else ""

    def build(self):
        apply_conandata_patches(self)

        # R32: platform check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

        # Pod::Parser was removed from Perl 5.36+ core
        # Provide it via PERL5LIB pointing to pre-installed site_perl
        perl5lib = self._build_perl5lib()
        env = [f"PERL5LIB={perl5lib}"] if perl5lib else None

        # Use INSTALL_BASE for staging dir in build folder
        # MakeMaker installs to $INSTALL_BASE/lib/perl5/Pod/Wrap.pm
        install_base = os.path.join(self.build_folder, "staging")

        # Step 1: Generate Makefile using ExtUtils::MakeMaker
        self.run(f'perl Makefile.PL INSTALL_BASE="{install_base}"',
                 cwd=self.source_folder, env=env)

        # Step 2: Build
        self.run("make -j1", cwd=self.source_folder, env=env)

        # Step 3: Install to staging dir
        self.run("make install", cwd=self.source_folder, env=env)

    def package(self):
        # Copy installed .pm files to package folder
        # MakeMaker installs to staging/lib/perl5/Pod/Wrap.pm
        copy(self, "*.pm",
             src=os.path.join(self.build_folder, "staging", "lib", "perl5"),
             dst=os.path.join(self.package_folder, "lib", "perl5"))

        # Copy the podwrap script from source (not auto-installed by Makefile.PL)
        script_src = os.path.join(self.source_folder, "scripts", "podwrap")
        if os.path.exists(script_src):
            os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
            shutil.copy2(script_src, os.path.join(self.package_folder, "bin", "podwrap"))

    def package_info(self):
        # Pure Perl module — no compiled libraries
        self.cpp_info.libs = []
        # Declare bin directory for the podwrap script
        self.cpp_info.bindirs = ["bin"]
        # Set PERL5LIB to the package's perl lib directory
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
