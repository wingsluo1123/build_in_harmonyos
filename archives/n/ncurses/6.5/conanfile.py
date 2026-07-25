#!/usr/bin/env python3
"""Conan recipe for ncurses 6.5 on OHOS."""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.5"
    description = "The ncurses terminal handling library"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://invisible-island.net/ncurses/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if name == "clang":
            return compilers.get("c", name)
        if name == "clang++":
            return compilers.get("cpp", name)
        return name

    def _patch_config_scripts(self):
        replacements = {
            "config.guess": [
                ("*:Minix:*:*)", "*:HarmonyOS:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n\t;;\n    *:Minix:*:*)"),
            ],
            "config.sub": [
                ("| fiwix* )", "| fiwix* | ohos* )"),
                ("| fiwix* | mlibc* | cos* | mbr* | ironclad* )", "| fiwix* | mlibc* | cos* | mbr* | ironclad* | ohos* )"),
                ("| linux-musl* | linux-relibc* | linux-uclibc* )", "| linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )"),
                ("| linux-relibc*- | linux-uclibc*- )", "| linux-relibc*- | linux-uclibc*- | linux-ohos*- )"),
            ],
        }
        for filename, edits in replacements.items():
            path = os.path.join(self.source_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
            for old, new in edits:
                content = content.replace(old, new)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_scripts()
        tmpdir = os.environ.get("TMPDIR", os.path.join(self.build_folder, "tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        for filename in ("configure", "config.guess", "config.sub"):
            path = os.path.join(self.source_folder, filename)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
                content = content.replace("umask 077", "umask 022")
                content = content.replace("/tmp", tmpdir)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
        shell = "/system/bin/sh"
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        configure_args = [
            "--without-shared",
            "--with-normal",
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--enable-widec",
            "--enable-overwrite",
            "--without-debug",
            "--without-ada",
            "--without-cxx",
            "--without-cxx-binding",
            "--without-manpages",
            "--without-tests",
            "--disable-stripping",
            "--disable-db-install",
            "--with-fallbacks=xterm-256color,vt100",
        ]
        cc = self._compiler("clang")
        cxx = self._compiler("clang++")
        build_env = f"SHELL={shell} CONFIG_SHELL={shell} CC={cc} CXX={cxx} CPP='{cc} -E' LD=ld.lld AR=llvm-ar RANLIB=llvm-ranlib STRIP=:"
        self.run(f"{build_env} {shell} ./configure {' '.join(configure_args)}", cwd=self.source_folder)
        makefile_fixes = {
            "Makefile": "top_srcdir\t= .\n",
            "ncurses/Makefile": "top_srcdir\t= ..\n",
            "progs/Makefile": "top_srcdir\t= ..\n",
            "panel/Makefile": "top_srcdir\t= ..\n",
            "menu/Makefile": "top_srcdir\t= ..\n",
            "form/Makefile": "top_srcdir\t= ..\n",
        }
        for filename, replacement in makefile_fixes.items():
            path = os.path.join(self.source_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
            with open(path, "w", encoding="utf-8") as handle:
                skipping_top_srcdir_tail = False
                for line in lines:
                    if line.startswith("top_srcdir"):
                        handle.write(replacement)
                        skipping_top_srcdir_tail = True
                    elif skipping_top_srcdir_tail and not line.startswith("srcdir"):
                        continue
                    else:
                        skipping_top_srcdir_tail = False
                        handle.write(line)
        for script_path in glob.glob(os.path.join(self.source_folder, "**", "*.sh"), recursive=True):
            os.chmod(script_path, 0o755)
        for makefile_path in glob.glob(os.path.join(self.source_folder, "**", "Makefile"), recursive=True):
            with open(makefile_path, "r", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
            content = content.replace("; ../headers.sh", f"; {shell} ../headers.sh")
            with open(makefile_path, "w", encoding="utf-8") as handle:
                handle.write(content)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run(f"make DESTDIR={self.package_folder} install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.set_property("cmake_file_name", "ncurses")
        self.cpp_info.set_property("cmake_target_name", "ncurses::ncurses")
        self.cpp_info.set_property("pkg_config_name", "ncursesw")
