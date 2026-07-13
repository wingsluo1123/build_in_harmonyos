#!/usr/bin/env python3
"""Conan recipe — lowdown 3.0.1 (Markdown translator CLI + library).

Build system: oconfigure (custom configure with KEY=value syntax, not --key=value).
Produces: lowdown CLI tool, lowdown-diff CLI tool, liblowdown library.
R38: includes CLI tools -> commands.json required.
"""
import os, glob as glob_mod

from conan import ConanFile
from conan.tools.files import get, copy, rmdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LowdownConan(ConanFile):
    name = "lowdown"
    version = "3.0.1"
    description = "simple markdown translator (HTML5, roff, LaTeX, gemini, ODT, terminal)"
    license = "ISC"
    homepage = "https://kristaps.bsd.lv/lowdown"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # oconfigure uses env vars directly

    def _convert_makefile(self):
        """Convert BSD make syntax to GNU make compatible syntax.
        Also fix HMDFS-incompatible operations (hard links -> copy)."""
        src_dir = self.source_folder
        with open(os.path.join(src_dir, "Makefile")) as f:
            content = f.read()

        lines = content.split("\n")
        result = []
        for line in lines:
            s = line.strip()
            if s.startswith(".ifdef "):
                result.append(line.replace(".ifdef ", "ifdef ", 1))
            elif s.startswith(".ifndef "):
                result.append(line.replace(".ifndef ", "ifndef ", 1))
            elif s.startswith(".if "):
                rest = s[4:].strip()
                rest = rest.replace("$(LINKER_SOSUFFIX)", "LINKER_SOSUFFIX")
                rest = rest.replace("$(SANDBOX_INIT_ERROR_IGNORE)", "SANDBOX_INIT_ERROR_IGNORE")
                rest = rest.replace("$(LINK_METHOD)", "LINK_METHOD")
                rest = rest.replace(' == "', ', "')
                rest = rest.replace('"', "", 1) if rest.endswith('"') else rest
                indent = line[:len(line) - len(line.lstrip())]
                result.append(f"{indent}ifeq ({rest})")
            elif s == ".else":
                indent = line[:len(line) - len(line.lstrip())]
                result.append(f"{indent}else")
            elif s == ".endif":
                indent = line[:len(line) - len(line.lstrip())]
                result.append(f"{indent}endif")
            else:
                # HMDFS: replace hard/soft links with copy
                if "ln -f" in s or "ln -sf" in s:
                    # ln -f lowdown lowdown-diff -> cp -f lowdown lowdown-diff
                    line = line.replace("ln -f", "cp -f")
                    line = line.replace("ln -sf", "cp -f")
                result.append(line)

        out = os.path.join(src_dir, "GNUmakefile")
        with open(out, "w") as f:
            f.write("\n".join(result))

    def build(self):
        apply_conandata_patches(self)

        # Convert BSD makefile to GNU make compatible
        self._convert_makefile()

        # oconfigure: KEY=value syntax, not --key=value
        # Use /system/bin/sh explicitly (HMDFS chmod E046 - can't set +x)
        cc = os.environ.get("CC", "clang")
        pkg_dir = self.package_folder
        src_dir = self.source_folder

        self.run(f"/system/bin/sh ./configure CC={cc} PREFIX={pkg_dir}", cwd=src_dir)
        self.run("make -f GNUmakefile -j1", cwd=src_dir)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Binaries
        copy(self, "lowdown", src=src, dst=os.path.join(pkg, "bin"), keep_path=False)
        # lowdown-diff is a symlink; copy as real file
        diff_src = os.path.join(src, "lowdown-diff")
        diff_dst = os.path.join(pkg, "bin", "lowdown-diff")
        if os.path.exists(diff_src):
            self.run(f"cp -a \"{diff_src}\" \"{diff_dst}\"")
        else:
            # If symlink creation failed, copy lowdown as lowdown-diff
            copy(self, "lowdown", src=os.path.join(pkg, "bin"),
                 dst=os.path.join(pkg, "bin"))
            os.rename(os.path.join(pkg, "bin", "lowdown"),
                      diff_dst)
            copy(self, "lowdown", src=src,
                 dst=os.path.join(pkg, "bin"), keep_path=False)

        # Library (static only)
        copy(self, "liblowdown.a", src=src, dst=os.path.join(pkg, "lib"), keep_path=False)

        # Header
        copy(self, "lowdown.h", src=src, dst=os.path.join(pkg, "include"), keep_path=False)

        # pkg-config
        copy(self, "lowdown.pc", src=src,
             dst=os.path.join(pkg, "lib", "pkgconfig"), keep_path=False)

        # Man pages (all .1, .3, .5)
        for section in ["man1", "man3", "man5"]:
            man_dir = os.path.join(pkg, "man", section)
            for mf in glob_mod.glob(os.path.join(src, "man", f"*.{section[-1]}")):
                copy(self, os.path.basename(mf), src=os.path.join(src, "man"),
                     dst=man_dir, keep_path=False)

        # Shared templates
        for fmt in ["html", "latex", "man", "ms", "odt"]:
            share_src = os.path.join(src, "share", fmt)
            if os.path.isdir(share_src):
                copy(self, "*", src=share_src,
                     dst=os.path.join(pkg, "share", "lowdown", fmt))

        # Clean up
        for d in ["__pycache__"]:
            path = os.path.join(pkg, d)
            if os.path.isdir(path):
                rmdir(self, path)

    def package_info(self):
        self.cpp_info.libs = ["lowdown"]
        self.cpp_info.bindirs = ["bin"]
