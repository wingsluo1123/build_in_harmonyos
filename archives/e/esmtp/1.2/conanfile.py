#!/usr/bin/env python3
"""Conan recipe for esmtp 1.2 — sendmail-compatible SMTP relay client.

esmtp is an SMTP *client* (not a server): it reads a message on stdin and
relays it to a preconfigured MTA, exposing sendmail/mailq/newaliases entry
points.  The whole protocol face — EHLO capability negotiation, STARTTLS
upgrade, SASL mechanism selection — is implemented by libESMTP, which
esmtp's configure requires through the `libesmtp-config` helper script.

Adaptation notes
----------------
* ``libesmtp-config`` shim: esmtp 1.2's configure aborts with
  ``libESMTP library not found`` when the helper is absent, but libESMTP
  >= 1.0 (meson) only installs headers, the library and a pkg-config file.
  ``generate()`` therefore writes a neutral helper script that reports the
  conan dependency's include/lib directories and prepends it to PATH.
  It carries no platform macro and no OS-specific branch — it only
  translates conan-provided paths (POSIX sh, same behaviour everywhere).
* Patch 0001 adds the conventional ``--version``/``--help`` options
  (see conandata.yml).
* Runtime linking: esmtp links the shared libesmtp from the conan cache, so
  an rpath to that dependency's libdir is added at link time — otherwise the
  installed binary cannot resolve libesmtp.so.6 when it is executed outside
  the ``conanrun`` environment (platform smoke test, direct invocation).
* Upstream ships no test suite (audit in test_package/MANIFEST.yml), so the
  consumer test_package performs the protocol-level verification: it starts
  a local ESMTP listener on a loopback non-privileged TCP port and drives a
  full EHLO → MAIL FROM → RCPT TO → DATA → QUIT session through the
  installed binary.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

_LIBESMTP_CONFIG = """#!/bin/sh
# Neutral capability helper for esmtp 1.2's configure.
# Upstream libESMTP >= 1.0 no longer installs `libesmtp-config`; the conan
# package ships headers, libesmtp.so and libesmtp-1.0.pc instead.  Report the
# dependency directories handed over by the recipe.  No platform conditionals.
includedir="@INCLUDEDIR@"
libdir="@LIBDIR@"
case "$1" in
  --version)      echo "1.1.0" ;;
  --cflags)       echo "-I$includedir" ;;
  --cflags-only-I) echo "-I$includedir" ;;
  --libs)         echo "-L$libdir -lesmtp" ;;
  --libs-only-L)  echo "-L$libdir" ;;
  --libs-only-l)  echo "-lesmtp" ;;
  *)              echo "libesmtp-config (conan-provided helper)" ;;
esac
exit 0
"""


class EsmtpConan(ConanFile):
    name = "esmtp"
    version = "1.2"
    description = "Sendmail-compatible SMTP relay client (STARTTLS + SASL via libESMTP)"
    license = "GPL-2.0-or-later"
    homepage = "https://esmtp.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI package: single binary + sendmail/mailq/newaliases symlinks (R38)
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0: published on ohpcd (libesmtp/1.1.0, OHOS/armv8 binary present)
        self.requires("libesmtp/1.1.0")

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "esmtp is only supported on Linux/OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # E011/E114 受控方案：configure 用 `umask 077 && mktemp -d ./confXXXXXX`
        # 建临时目录，在本文件系统上得到 drwx--S---（setgid 叠加），随后
        # config.status 写 $tmp/subs1.awk 报 "Permission denied"。
        # 只把 077 改成 022 —— 保留真实临时目录创建，不换环境、不伪造成功。
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

    def _write_libesmtp_config_shim(self):
        """Write the `libesmtp-config` helper configure insists on."""
        dep = self.dependencies["libesmtp"]
        includedir = dep.cpp_info.includedirs[0]
        libdir = dep.cpp_info.libdirs[0]
        shim_dir = os.path.join(self.build_folder, "conan-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "libesmtp-config")
        script = _LIBESMTP_CONFIG.replace("@INCLUDEDIR@", includedir).replace(
            "@LIBDIR@", libdir
        )
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write(script)
        os.chmod(shim, 0o755)
        self.output.info(
            "libesmtp-config helper: include=%s lib=%s" % (includedir, libdir)
        )
        return shim_dir

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        # The installed binary links the shared libesmtp living in the conan
        # cache; without an rpath it cannot be executed outside conanrun
        # (platform smoke test runs it with the ambient environment only).
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append("-Wl,-rpath,{}".format(libdir))
        tc.generate()

        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                # configure compiles and *runs* conftest programs, which must
                # resolve the shared dependency at run time (aaphoto precedent)
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path("PATH", self._write_libesmtp_config_shim())
        env.vars(self, scope="build").save_script("esmtp_buildenv")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # Upstream registers no tests; `make check` is still executed so the
        # build records the real (empty) result instead of skipping it.
        autotools.make(args=["-j1"], target="check")

    def _relocate_upstream_symlinks(self):
        """upstream's install hooks create prefix-absolute symlinks.

        install-exec-hook does `$(LN_S) $(bindir)/esmtp <dest>`, and this build
        configures prefix="/" (conan convention), so the packaged links aim at
        /bin/esmtp and dangle once packaged.  Rewrite only links whose absolute
        target also exists under package_folder into a relative path; anything
        else is left untouched.
        """
        rewritten = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                link = os.path.join(root, name)
                if not os.path.islink(link):
                    continue
                target = os.readlink(link)
                if not os.path.isabs(target):
                    continue
                candidate = os.path.join(self.package_folder, target.lstrip("/"))
                if not os.path.exists(candidate):
                    continue
                new_target = os.path.relpath(candidate, root)
                os.unlink(link)
                os.symlink(new_target, link)
                rewritten.append(
                    "%s -> %s" % (os.path.relpath(link, self.package_folder), new_target)
                )
        if rewritten:
            self.output.info("relocated %d upstream symlinks" % len(rewritten))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._relocate_upstream_symlinks()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "esmtp")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
