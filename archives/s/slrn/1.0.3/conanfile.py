#!/usr/bin/env python3
"""Conan recipe for slrn 1.0.3 - S-Lang based Usenet newsreader.

Upstream (jedsoft.org, GPL-2.0) is an Autotools C project.  There is no
plain "1.0.3" tarball; the official 1.0.3 release artifact is
slrn-1.0.3a.tar.bz2 (the "a" respin of the 1.0.3 release), which is what
conandata.yml downloads.

Adaptation notes (HarmonyOS PC, aarch64):
  * autoconf/config.sub (2014-05-01) does not know the linux-ohos OS token,
    so the explicit --build/--host=aarch64-linux-ohos triplets are rejected;
    patch 0001 teaches config.sub both canonicalization paths.
  * src/Makefile.in builds and immediately executes chkslang, a build-time
    helper that verifies the S-Lang header/library version.  That is
    impossible in a cross build ("cannot execute binary file"); patch 0002
    guards the run behind SKIP_CHKSLANG.  The recipe passes SKIP_CHKSLANG=1
    only when cross compiling, so native OHOS CI builds still run chkslang.
    The S-Lang version floor (>= 2.2.3) is independently guaranteed by the
    pinned conan dependency slang/2.3.3.
  * configure's config.status creates its temporary directory with
    "umask 077"; on HMDFS (HarmonyOS PC file system) the mapped directory
    ownership makes the 0700 directory unwritable for the build process
    (knowledge E011).  Patch 0003 relaxes it to umask 022.
  * configure probes va_copy/__va_copy/va_list-by-value via AC_TRY_RUN,
    which aborts while cross compiling; the recipe presets the matching
    slrn_cv_* cache variables (va_copy and __va_copy exist on aarch64-musl,
    va_list cannot be copied by value on aarch64).
  * uudeview and canlock are optional and not yet published in the ohpcd
    registry, so they stay disabled (slrn has built-in yEnc decoding;
    canlock only matters for Cancel-Lock posting).
Artifacts: bin/slrn (software-level commands.json declares the CLI, R38).
License: GPL-2.0.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SlrnConan(ConanFile):
    name = "slrn"
    version = "1.0.3"
    description = "slrn - S-Lang based text-mode Usenet newsreader (NNTP)"
    license = "GPL-2.0"
    homepage = "https://www.jedsoft.org/slrn/"
    url = "https://github.com/jedsoft/slrn"
    topics = ("usenet", "newsreader", "nntp", "slang", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "slrn 1.0.3 currently supports only Linux and OHOS"
            )

    def requirements(self):
        self.requires("slang/2.3.3")
        self.requires("openssl/3.0.16")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # src/Makefile.in has no VPATH/srcdir support: build in-source.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        slang_prefix = self.dependencies["slang"].package_folder
        ssl_prefix = self.dependencies["openssl"].package_folder
        tc.configure_args.extend([
            "--with-slang=%s" % slang_prefix,
            "--with-ssl=%s" % ssl_prefix,
            # AC_TRY_RUN probes that cannot execute while cross compiling:
            # va_copy/__va_copy are available on aarch64 musl/OHOS, and
            # va_list is an array type there, so it cannot be assigned.
            "slrn_cv_va_copy=yes",
            "slrn_cv___va_copy=yes",
            "slrn_cv_va_val_copy=no",
        ])
        if self.settings.os == "OHOS":
            # The bundled 2014 config.sub does not know linux-ohos
            # (patched in 0001); AutotoolsToolchain does not inject the
            # OHOS triplets for this old autoconf.
            tc.configure_args.append("--host=aarch64-linux-ohos")
            if self._is_native_ohos():
                # Native OHOS CI build: build == host, configure may run
                # its probes and chkslang still runs.
                tc.configure_args.append("--build=aarch64-linux-ohos")
            else:
                # Cross build (macOS dev box; also when the build profile
                # uses OHOS settings but is flagged as a local simulation
                # via user.build:flex_bison_native, see the scws recipe):
                # pass a build triplet the 2014 config.sub accepts so
                # configure enters cross mode instead of aborting with
                # "cannot run C compiled programs".
                tc.configure_args.append("--build=aarch64-apple-darwin")
        tc.generate()

    def _is_native_ohos(self):
        # True only for a real native HarmonyOS PC build.  The local
        # ohos-local profile declares OHOS settings on a macOS host and
        # flags that simulation via user.build:flex_bison_native.
        if str(self.settings.os) != "OHOS":
            return False
        if str(self.settings_build.os) != "OHOS":
            return False
        return not self.conf.get("user.build:flex_bison_native",
                                 default=False, check_type=bool)

    def _make_args(self):
        # chkslang is a build-time executable linked for the target; it can
        # only run in native builds (OHOS CI builds natively on a HarmonyOS
        # PC).  Skip running it when cross compiling.
        if self._is_native_ohos():
            return []
        return ["SKIP_CHKSLANG=1"]

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=self._make_args())

    def package(self):
        # Serial install: slrn's install targets race with installdirs
        # under -jN (mkdir "File exists" / install temp-file failures).
        args = " ".join(["install", "DESTDIR=" + self.package_folder]
                        + self._make_args() + ["-j1"])
        self.run("make %s" % args, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=self.package_folder + "/licenses", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # slrn's S-Lang interpreter needs its script library (slrn.sl & co.)
        # at startup; the path compiled in from --prefix=/ is //share/slrn/...
        # which does not exist on consumer machines, so point the documented
        # SLRN_SLANG_DIR override at the packaged copy.
        self.runenv_info.define(
            "SLRN_SLANG_DIR",
            os.path.join(self.package_folder, "share", "slrn", "slang"))
