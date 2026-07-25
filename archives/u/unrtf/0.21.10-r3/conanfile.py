#!/usr/bin/env python3
"""Conan recipe for GNU UnRTF 0.21.10-r3."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import chdir, copy, get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class UnrtfConan(ConanFile):
    name = "unrtf"
    version = "0.21.10-r3"
    description = "GNU UnRTF converts Rich Text Format documents to HTML, text, LaTeX and other formats"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/unrtf/"
    url = ""
    package_type = "application"
    win_bash = True

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--datarootdir=${prefix}/share")
        tc.generate()

    def _patch_configure_umask(self):
        configure_path = f"{self.source_folder}/configure"
        replacements = {
            '(umask 077 && mktemp -d "./confXXXXXX")': '(umask 022 && mktemp -d "./confXXXXXX")',
            '(umask 077 && mkdir "$tmp")': '(umask 022 && mkdir "$tmp")',
        }
        with open(configure_path, "r", encoding="utf-8") as f:
            content = f.read()
        changed = False
        for old, new in replacements.items():
            if old in content:
                content = content.replace(old, new)
                changed = True
        if not changed:
            raise ConanException("Expected configure umask patterns not found")
        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _patch_windows_makefile_quoting(self):
        src_makefile = f"{self.source_folder}/src/Makefile"
        copy(self, "unrtf_w.c", src=f"{self.source_folder}/Windows", dst=f"{self.source_folder}/src")
        replace_in_file(
            self,
            src_makefile,
            'AM_CPPFLAGS = -DPKGDATADIR=\\"$(pkgdatadir)\\"',
            'AM_CPPFLAGS = "-DPKGDATADIR=\\"$(pkgdatadir)\\""',
        )
        replace_in_file(
            self,
            src_makefile,
            "word.$(OBJEXT)",
            "word.$(OBJEXT) unrtf_w.$(OBJEXT)",
        )
        replace_in_file(
            self,
            src_makefile,
            "LIBS = ",
            "LIBS = -liconv -lshlwapi -lkernel32",
        )

    def build(self):
        apply_conandata_patches(self)
        # Build-time HMDFS config.status temp-dir permission fix; keep generated configure out of persistent patches.
        self._patch_configure_umask()
        autotools = Autotools(self)
        configure_args = " ".join([
            autotools._configure_args,
            "--disable-maintainer-mode",
            "--disable-dependency-tracking",
        ])
        with chdir(self, self.source_folder):
            if self.settings_build.get_safe("os") == "Windows":
                self.run(f"./configure {configure_args}")
            else:
                configure_shell = os.environ.get("CONFIG_SHELL") or "bash"
                if os.path.isabs(configure_shell) and not os.path.exists(configure_shell):
                    configure_shell = "bash"
                os.environ["CONFIG_SHELL"] = configure_shell
                os.environ["SHELL"] = configure_shell
                self.run(f"CONFIG_SHELL={configure_shell} SHELL={configure_shell} {configure_shell} ./configure {configure_args}")
            if self.settings_build.get_safe("os") == "Windows":
                self._patch_windows_makefile_quoting()
                self.run("MSYS2_ARG_CONV_EXCL='*' mingw32-make -j1")
            else:
                autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        with chdir(self, self.build_folder):
            if self.settings_build.get_safe("os") == "Windows":
                self.run(f'mingw32-make install -j1 DESTDIR="{unix_path(self, self.package_folder)}"')
            else:
                autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
