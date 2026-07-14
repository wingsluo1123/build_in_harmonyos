#!/usr/bin/env python3
"""Conan recipe for tinyhttpd 1.0 — lightweight HTTP server.

tinyhttpd is a ~500-line HTTP server written in C by J. David Blackstone
in 1999. It uses a plain Makefile (no configure script) and links
against pthreads. This recipe modifies the Makefile to support
CC/CFLAGS overrides for cross-compilation.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, replace_in_file, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TinyhttpdConan(ConanFile):
    name = "tinyhttpd"
    version = "1.0"
    description = "Lightweight HTTP server written in C by J. David Blackstone"
    license = "GPL-3.0"
    homepage = "https://github.com/EZLippi/Tinyhttpd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # tinyhttpd is a CLI tool, not a library
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tinyhttpd only supports Linux/OHOS, got {self.settings.os}"
            )
        env = VirtualBuildEnv(self)
        env.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, not from shell env vars
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        # Build CFLAGS from Conan settings
        cflags = ["-fPIC", "-W", "-Wall"]
        if str(self.settings.build_type) == "Release":
            cflags.append("-O2")
        elif str(self.settings.build_type) == "Debug":
            cflags.append("-g")
        cflags_str = " ".join(cflags)

        # Modify httpd.c: add --version/--help support for CLI compatibility (L2 smoke test)
        httpd_c = os.path.join(self.source_folder, "httpd.c")
        replace_in_file(
            self,
            httpd_c,
            "int main(void)\n{",
            "int main(int argc, char **argv)\n{\n"
            "    if (argc > 1) {\n"
            "        if (strcmp(argv[1], \"--version\") == 0) {\n"
            "            printf(\"tinyhttpd 1.0\\n\");\n"
            "            return 0;\n"
            "        }\n"
            "        if (strcmp(argv[1], \"--help\") == 0) {\n"
            "            printf(\"Usage: httpd\\n"
            "  --version  Print version information\\n"
            "  --help     Print this help message\\n\");\n"
            "            return 0;\n"
            "        }\n"
            "    }\n",
        )

        # Modify Makefile: replace hardcoded gcc with $(CC) and add $(CFLAGS)
        makefile = os.path.join(self.source_folder, "Makefile")
        replace_in_file(
            self,
            makefile,
            "gcc -g -W -Wall $(LIBS) -o $@ $<",
            "$(CC) $(CFLAGS) $(LIBS) -o $@ $<",
        )
        replace_in_file(
            self,
            makefile,
            "gcc -W -Wall -o $@ $<",
            "$(CC) $(CFLAGS) -o $@ $<",
        )

        self.run(
            f'make httpd CC="{cc}" CFLAGS="{cflags_str}" -j1',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        # Copy httpd binary to bin/
        copy(self, "httpd", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Copy htdocs directory
        htdocs_src = os.path.join(self.source_folder, "htdocs")
        if os.path.isdir(htdocs_src):
            copy(self, "*", src=htdocs_src,
                 dst=os.path.join(self.package_folder, "share/tinyhttpd/htdocs"))

    def package_info(self):
        # tinyhttpd is a CLI tool — binary in bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
