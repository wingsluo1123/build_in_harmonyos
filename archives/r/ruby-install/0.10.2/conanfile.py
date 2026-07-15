#!/usr/bin/env python3
"""Conan recipe for ruby-install 0.10.2 — pure Shell (Bash) script project.

ruby-install is a command-line tool for installing Ruby, JRuby, TruffleRuby,
or mruby. It is a pure Shell script project with no compilation step;
"installation" consists of copying scripts from bin/ and share/ to the
prefix directory.

Platform adaptations for OHOS:
  1. Shebang already uses #!/usr/bin/env bash — OHOS compatible.
  2. No compilation needed, only make install with PREFIX and DESTDIR.
  3. Tests require shellcheck (not available on OHOS); skipped in CI.

R32: settings.os check uses `in ("Linux", "OHOS")` where needed.
R28: test_package/ exists.
R38: commands.json declared (command-line tool type).
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RubyInstallConan(ConanFile):
    name = "ruby-install"
    version = "0.10.2"
    description = "Installs Ruby, JRuby, TruffleRuby, or mruby (pure Bash scripts)"
    license = "MIT"
    homepage = "https://github.com/postmodern/ruby-install"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ruby-install is a pure shell script project — no compilation step.
        # The Makefile's "all" target is empty; "install" copies scripts.

    def package(self):
        # Replicate what `make install PREFIX=... DESTDIR=...` does:
        #   for dir in $(find bin share -type d); do mkdir -p $(DESTDIR)$(PREFIX)/$dir; done
        #   for file in $(find bin share -type f); do cp $file $(DESTDIR)$(PREFIX)/$file; done
        src_dir = self.source_folder

        # Copy bin/ scripts
        bin_src = os.path.join(src_dir, "bin")
        if os.path.isdir(bin_src):
            copy(self, "*", src=bin_src, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
            # Ensure scripts are executable
            pkg_bin = os.path.join(self.package_folder, "bin")
            for fname in os.listdir(pkg_bin):
                fpath = os.path.join(pkg_bin, fname)
                if os.path.isfile(fpath):
                    os.chmod(fpath, os.stat(fpath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        # Copy share/ directory (ruby-install scripts and version data)
        share_src = os.path.join(src_dir, "share")
        if os.path.isdir(share_src):
            copy(self, "*", src=share_src, dst=os.path.join(self.package_folder, "share"), keep_path=True)

        # Copy doc files
        copy(self, "*.md", src=src_dir, dst=os.path.join(self.package_folder, "share", "doc", "ruby-install-0.10.2"), keep_path=False)
        copy(self, "*.txt", src=src_dir, dst=os.path.join(self.package_folder, "share", "doc", "ruby-install-0.10.2"), keep_path=False)

    def package_info(self):
        # Pure script project: no libraries, just executables in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
