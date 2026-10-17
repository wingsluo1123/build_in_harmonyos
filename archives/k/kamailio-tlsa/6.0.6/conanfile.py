#!/usr/bin/env python3
"""Conan recipe for the Kamailio 6.0.6 TLSA module (classic Makefiles)."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


PLATFORM_DEFS = (
    "-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD "
    "-DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H "
    "-DHAVE_TIMEGM -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN"
)


class KamailioTlsaConan(ConanFile):
    name = "kamailio-tlsa"
    version = "6.0.6"
    description = "Kamailio TLS transport with an isolated, statically embedded OpenSSL"
    license = "GPL-2.0-or-later"
    homepage = "https://www.kamailio.org"
    url = "https://github.com/kamailio/kamailio"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {"openssl/*:shared": False}
    exports_sources = "compat/*", "integration.md"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1", transitive_headers=False, transitive_libs=False)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("TLSA is validated on Linux and OHOS")
        if str(self.settings.arch) not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration("TLSA requires armv8 or x86_64")
        if self.dependencies["openssl"].options.get_safe("shared"):
            raise ConanInvalidConfiguration("TLSA requires PIC static OpenSSL archives")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # E254: ship added sources directly; the OHOS patch dry-run command
        # creates empty new files in the supposedly pristine baseline.
        copy(self, "tlsa_keys.*", os.path.join(self.export_sources_folder, "compat"),
             os.path.join(self.source_folder, "src", "modules", "tlsa"))
        openssl = self.dependencies["openssl"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or ("clang" if str(self.settings.compiler) == "clang" else "gcc")
        variables = [
            "CC=" + cc,
            "ARCH=" + ("aarch64" if self.settings.arch == "armv8" else "x86_64"),
            "OS=" + ("harmonyos" if self.settings.os == "OHOS" else "linux"),
            "mode=" + ("debug" if self.settings.build_type == "Debug" else "release"),
            "SSL_BUILDER=source", "CRYPTO_BUILDER=", "LIBSSL_STATIC_SRCLIB=yes",
            "LIBSSL_STATIC_SRCPATH=" + os.path.join(openssl, "lib"),
            "extra_defs=" + PLATFORM_DEFS,
        ]
        args = " ".join(shlex.quote(value) for value in variables)
        env = Environment()
        env.define("CPATH", os.path.join(openssl, "include"))
        # OHOS supplies the public resolver API, but not glibc's _res internals.
        if self.settings.os == "OHOS":
            env.define("DEFS", "-UHAVE_RESOLV_RES")
        with env.vars(self).apply():
            self.run("make cfg include_modules=tlsa " + args, cwd=self.source_folder)
            self.run("make modules modules=modules/tlsa -j2 " + args, cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        module_dir = os.path.join(self.package_folder, "lib", "kamailio", "modules")
        copy(self, "tlsa.so", os.path.join(self.source_folder, "src", "modules", "tlsa"), module_dir)
        copy(self, "tls.cfg", os.path.join(self.source_folder, "src", "modules", "tls"), module_dir)
        docs = os.path.join(self.package_folder, "share", "kamailio-tlsa")
        copy(self, "integration.md", self.export_sources_folder, docs)
        # Matching core is a runtime integration prerequisite, not a second package.
        copy(self, "0001-src-core-daemonize.c.patch",
             os.path.join(self.export_sources_folder, "patches"), docs)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib/kamailio/modules"]
        self.cpp_info.set_property("kamailio_modules_dir", "lib/kamailio/modules")
