#!/usr/bin/env python3
"""Conan recipe -- Erlang/OTP 28.5.0.7 for HarmonyOS PC (native aarch64 clang/musl).

Erlang/OTP does not use a single autotools project.  The release tarball ships a
hand-written top-level ``configure`` that drives ``erts`` plus the autoconf
``configure`` scripts of the few applications that need one, and the real work is
done by recursive ``make`` invocations below that.  The recipe therefore runs
``./configure`` / ``make`` / ``make install`` directly instead of going through
``AutotoolsToolchain``.

The portability patches (see patches/ and notes.md) cover:
  * the ``aarch64-unknown-linux-ohos`` triplet in the bundled config.sub,
  * HarmonyOS refusing the umask-077 temporary directories of the autoconf helpers,
  * the wide-character ncurses archive in the erts termcap probe,
  * musl not providing gethostid(), and mallopt() being declared in <malloc.h>,
  * the vendor HarmonyOS kernel release string in the inet driver.
"""
import os
import re
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout

# configure triplet used by the OHOS conan profile (os=OHOS -> linux-ohos).
OHOS_TRIPLET = "aarch64-unknown-linux-ohos"
# /system/bin/sh (mksh) cannot run ELF binaries on HarmonyOS PC.
OHOS_BASH = "/data/service/hnp/bin/bash"


class ErlangConan(ConanFile):
    name = "erlang"
    version = "28.5.0.7"
    description = ("Erlang/OTP 28: BEAM virtual machine, Erlang compiler, "
                   "standard libraries and development tools")
    license = "Apache-2.0"
    homepage = "https://www.erlang.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Bare references: the ohpcd remote stores packages without a user/channel.
        self.requires("openssl/3.5.7")
        self.requires("zlib/1.3.1")
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                "erlang/%s only supports OHOS (HarmonyOS PC)" % self.version)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers
    def _staging_prefix(self):
        return os.path.join(self.build_folder, "_install")

    def _configure_env(self):
        deps = [self.dependencies[name].package_folder
                for name in ("openssl", "zlib", "ncurses")]
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("CPPFLAGS", " ".join("-I%s/include" % d for d in deps))
        env.define("LDFLAGS", " ".join("-L%s/lib" % d for d in deps))
        env.define("CONFIG_SHELL", OHOS_BASH)
        env.define("SHELL", OHOS_BASH)
        env.define("LC_ALL", "C")
        return env

    def _make_args(self):
        jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        if not jobs:
            jobs = os.cpu_count() or 1
        args = ["-j%d" % jobs]
        # HarmonyOS has no mkfifo(1), so GNU make cannot create its default FIFO
        # jobserver and every recursive make degrades to -j1.  GNU make 4.4 can use
        # a pipe jobserver instead, which keeps the recursion parallel.
        out = StringIO()
        self.run("make --version", stdout=out, ignore_errors=True)
        m = re.search(r"GNU Make (\d+)\.(\d+)", out.getvalue())
        if m and (int(m.group(1)), int(m.group(2))) >= (4, 4):
            args.append("--jobserver-style=pipe")
        return args

    # -------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        openssl = self.dependencies["openssl"].package_folder

        configure = [
            "./configure",
            "--prefix=%s" % self._staging_prefix(),
            "--build=%s" % OHOS_TRIPLET,
            "--host=%s" % OHOS_TRIPLET,
            # wx needs a GUI toolkit, odbc needs unixODBC, jinterface needs a Java
            # compiler: none of them exist on HarmonyOS PC.
            "--without-wx",
            "--without-odbc",
            "--without-javac",
            "--with-ssl=%s" % openssl,
            "--with-ssl-incl=%s" % openssl,
        ]
        with self._configure_env().vars(self, scope="build").apply():
            self.run(" ".join(configure), cwd=self.source_folder)
            self.run("make %s" % " ".join(self._make_args()), cwd=self.source_folder)

    def package(self):
        with self._configure_env().vars(self, scope="build").apply():
            self.run("make install", cwd=self.source_folder)
        copy(self, "*", src=self._staging_prefix(), dst=self.package_folder)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Consumers drive Erlang through its command line tools; the VM and the
        # standard libraries are found relative to the installed root directory.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["lib/erlang/usr/include"]
        self.cpp_info.set_property("cmake_file_name", "Erlang")
        self.cpp_info.set_property("pkg_config_name", "erlang")
