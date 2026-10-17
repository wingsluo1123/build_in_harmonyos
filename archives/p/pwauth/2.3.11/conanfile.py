#!/usr/bin/env python3
"""Conan recipe for pwauth 2.3.11 - PAM based Unix authenticator (plain Makefile).

pwauth reads "<login>\\n<password>\\n" from stdin and reports the result through
its exit status; Apache mod_authnz_external uses it as an external
authentication command.  Upstream has no configure script: the build is
configured by hand editing config.h and built with a plain Makefile that
hardcodes CC/LIB and has no install target.

This recipe therefore:
  * selects the PAM backend in config.h (the same choice the Debian package
    makes) and depends on the separately adapted linux-pam/1.7.2;
  * passes the Conan toolchain compiler/flags and the linux-pam include/lib
    paths on the make command line, because the upstream Makefile assigns
    CC/CFLAGS/LIB itself (R33: never rely on bare ${CC}/${CFLAGS});
  * installs the built binary manually into bin/ (R38 tool package).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PwauthConan(ConanFile):
    name = "pwauth"
    version = "2.3.11"
    description = "pwauth - PAM based authenticator for mod_authnz_external and Apache httpd"
    license = "BSD-3-Clause"
    homepage = "https://github.com/phokz/pwauth"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pwauth needs POSIX PAM (linux-pam) and a Unix passwd database"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # The Autotools toolchain is used here only to compute the build_type /
        # arch flags for the plain Makefile build; upstream has no configure.
        toolchain = AutotoolsToolchain(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        pam_root = self.dependencies["linux-pam"].package_folder
        pam_include = os.path.join(pam_root, "include")
        pam_libdir = os.path.join(pam_root, "lib")

        cflags = list(toolchain.cflags)
        cflags.extend("-D{}".format(define) for define in toolchain.defines)
        cflags.append("-I{}".format(pam_include))
        # -lpam plus the dl system library declared by linux-pam; the rpath lets
        # the installed tool locate libpam.so.0 outside a `conanrun` shell.
        libs = "-L{} -Wl,-rpath,{} -lpam -ldl".format(pam_libdir, pam_libdir)

        # R9: always -j1 (also avoids the make jobserver FIFO on OHOS).
        # R33: CC/CFLAGS come from the Conan toolchain and conf, not from the shell.
        self.run(
            'make -j1 CC="{}" CFLAGS="{}" LIB="{}"'.format(cc, " ".join(cflags), libs),
            cwd=self.source_folder,
        )

    def package(self):
        # Upstream Makefile has no install target: package the built binary.
        copy(self, "pwauth", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
