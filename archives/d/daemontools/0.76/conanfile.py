#!/usr/bin/env python3
"""Conan recipe — daemontools 0.76 (DJB Makefile)

daemontools is a UNIX service management toolset by Daniel J. Bernstein.
Build system: DJB-style Makefile (no configure script; configuration via
conf-cc/conf-ld/home files). Output: 17 command-line tools.

Key adaptation:
- conf-cc/conf-ld/home generated dynamically (replaces patches 0002/0003/0006)
- errno fix: extern int errno -> #include <errno.h> (musl libc compat)
- find-systype.sh: gcc -> clang (patch 0005)
- rts test suite skipped (FIFO/supervise tests hang on OHOS)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DaemontoolsConan(ConanFile):
    name = "daemontools"
    version = "0.76"
    description = "Collection of tools for managing UNIX services"
    license = "LicenseRef-Homebrew-public-domain"
    homepage = "https://cr.yp.to/daemontools.html"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # daemontools is pure C, no external dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # DJB source is nested: strip_root removes 'admin/', leaving daemontools-0.76/src/
        src_dir = os.path.join(self.source_folder, "daemontools-0.76", "src")

        # R33: Get compiler from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # Write DJB configuration files dynamically (replaces patches 0002/0003/0006)
        # conf-cc: compiler and flags for compiling .c files
        conf_cc = (
            f"{cc} -fPIC -O2"
            " -Wimplicit -Wunused -Wcomment -Wchar-subscripts"
            " -Wuninitialized -Wshadow -Wcast-qual -Wcast-align"
            " -Wwrite-strings"
        )
        with open(os.path.join(src_dir, "conf-cc"), "w") as f:
            f.write(conf_cc + "\n")

        # conf-ld: linker for linking .o into executables
        with open(os.path.join(src_dir, "conf-ld"), "w") as f:
            f.write(f"{cc}\n")

        # home: installation prefix (DJB reads this for path substitution in svscanboot)
        with open(os.path.join(src_dir, "home"), "w") as f:
            f.write(self.package_folder + "\n")

        # R9: Always use -j1
        self.run(f"make -C {src_dir} -j1")

    def package(self):
        src_dir = os.path.join(self.source_folder, "daemontools-0.76", "src")
        bin_dst = os.path.join(self.package_folder, "bin")

        # DJB has no make install; manually copy all built executables
        daemontools_bins = [
            "envdir", "envuidgid", "fghack", "multilog",
            "pgrphack", "readproctitle", "setlock", "setuidgid", "softlimit",
            "supervise", "svc", "svok", "svscan", "svscanboot", "svstat",
            "tai64n", "tai64nlocal",
        ]
        for binary in daemontools_bins:
            binary_path = os.path.join(src_dir, binary)
            if os.path.isfile(binary_path):
                copy(self, binary, src=src_dir, dst=bin_dst)

        # R7: Self-sign ELF binary on OHOS for local execution
        # OHOS requires ELF signatures; unsigned binaries get "Permission denied"
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool):
                for binary in daemontools_bins:
                    binary_path = os.path.join(bin_dst, binary)
                    if not os.path.isfile(binary_path):
                        continue
                    # Skip non-ELF files (svscanboot is a shell script)
                    with open(binary_path, "rb") as f:
                        if f.read(4) != b"\x7fELF":
                            continue
                    signed_path = f"{binary_path}.signed"
                    self.run(
                        f'{sign_tool} sign -inFile "{binary_path}"'
                        f' -outFile "{signed_path}"'
                        f' -selfSign 1 -signAlg SHA256withECDSA',
                        quiet=True
                    )
                    if os.path.isfile(signed_path):
                        os.replace(signed_path, binary_path)
                        os.chmod(binary_path, 0o755)

    def package_info(self):
        # daemontools is a command-line toolset, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
