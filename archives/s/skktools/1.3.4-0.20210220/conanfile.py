#!/usr/bin/env python3
"""Conan recipe — skktools 1.3.4-0.20210220 (Autotools SKK dictionary tools).

skktools builds four command-line tools:
  - skkdic-count / skkdic-sort : dependency-free
  - skkdic-expr                : ndbm interface (provided by gdbm/1.23 with
                                 --enable-libgdbm-compat => gdbm/ndbm.h)
  - skkdic-expr2               : glib-2.0 (provided by glib2/2.88.0.1)

Version note: upstream source is the git snapshot commit 0fe2106fbc052445c611e6c5b2a79899d740edcb
(2021-02-20) on top of the skktools-1_3_4 tag; VERSION in-tree stays 1.3.4.
The Conan version 1.3.4-0.20210220 records the snapshot date, mirroring the
Debian-style versioning; the archive directory, test_package reference and the
branch name all use the same string.

Source URL/SHA256 are kept inline in this recipe (no conandata.yml) to avoid
the CI conandata pre-download path that fails on an uninitialized BUILD_DIR
(see knowledge draft DRAFT-...-BUILD_DIR-parameter-not-set lineage).
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.files import copy, get, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

_required_source_sha256 = "6339d1ec42ca19c9ae03318a8196109dedf87140841dd9e7fa79936578a45371"

# The three portability patches are embedded verbatim in this recipe so
# that application does not depend on how a Conan build resolves patch
# file paths (they differ across Conan builds).
PATCH_SOURCES = {
    "P0001": r"""--- a/config.guess
+++ b/config.guess
@@ -879,6 +879,27 @@
     *:GNU/*:*:*)
 	# other systems with GNU libc and userland
 	echo ${UNAME_MACHINE}-unknown-`echo ${UNAME_SYSTEM} | sed 's,^[^/]*/,,' | tr '[A-Z]' '[a-z]'``echo ${UNAME_RELEASE}|sed -e 's/[-(].*//'`-${LIBC}
 	exit ;;
+    *:HarmonyOS:*:*)
+	# HarmonyOS/OpenHarmony detection
+	# Output triplet: {MACHINE}-unknown-linux-ohos
+	case "$UNAME_MACHINE" in
+		aarch64|arm64)
+			echo "aarch64-unknown-linux-ohos"
+			;;
+		armv7*|arm*)
+			echo "arm-unknown-linux-ohos"
+			;;
+		x86_64|amd64)
+			echo "x86_64-unknown-linux-ohos"
+			;;
+		i?86)
+			echo "i686-unknown-linux-ohos"
+			;;
+		*)
+			echo "$UNAME_MACHINE-unknown-linux-ohos"
+			;;
+	esac
+	exit ;;
     i*86:Minix:*:*)
 	echo ${UNAME_MACHINE}-pc-minix
 	exit ;;
""",
    "P0002": r"""--- a/config.sub
+++ b/config.sub
@@ -115,7 +115,7 @@
 # Here we must recognize all the valid KERNEL-OS combinations.
 maybe_os=`echo $1 | sed 's/^\(.*\)-\([^-]*-[^-]*\)$/\2/'`
 case $maybe_os in
-  nto-qnx* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \
+  nto-qnx* | linux-ohos* | linux-gnu* | linux-android* | linux-dietlibc | linux-newlib* | \
   linux-musl* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* | \
   knetbsd*-gnu* | netbsd*-gnu* | \
   kopensolaris*-gnu* | \
@@ -1399,6 +1399,9 @@
 		os=`echo $os | sed -e 's|mac|macos|'`
 		;;
 	-linux-dietlibc)
 		os=-linux-dietlibc
 		;;
+	-linux-ohos)
+		os=-linux-ohos
+		;;
 	-linux*)
 		;;
""",
    "P0003": r"""--- a/configure
+++ b/configure
@@ -13262,10 +13262,10 @@
 # Create a (secure) tmp directory for tmp files.

 {
-  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
+  tmp=`(mktemp -d) 2>/dev/null` &&
   test -n "$tmp" && test -d "$tmp"
 }  ||
 {
   tmp=./conf$$-$RANDOM
-  (umask 077 && mkdir "$tmp")
+  (mkdir "$tmp")
 } || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
""",
}


class SkktoolsConan(ConanFile):
    name = "skktools"
    version = "1.3.4-0.20210220"
    description = "SKK JISYO dictionary handling tools (skkdic-expr, skkdic-sort, skkdic-count, skkdic-expr2)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/skk-dev/skktools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "patches/*.patch", self.recipe_folder,
             os.path.join(self.export_sources_folder, "patches"))

    def source(self):
        # URL order: direct upstream first (works on site-CI workers),
        # then a byte-identical GitHub proxy fallback for restricted
        # networks (e.g. on-device shadow CI without direct GitHub access).
        # Conan verifies sha256 against whichever URL succeeds.
        get(
            self,
            url=[
                "https://github.com/skk-dev/skktools/archive/0fe2106fbc052445c611e6c5b2a79899d740edcb.tar.gz",
                "https://ghfast.top/https://github.com/skk-dev/skktools/archive/0fe2106fbc052445c611e6c5b2a79899d740edcb.tar.gz",
            ],
            sha256=_required_source_sha256,
            strip_root=True,
        )

    def requirements(self):
        # ndbm interface for skkdic-expr: gdbm/1.23 is built with
        # --enable-libgdbm-compat, which ships include/gdbm/ndbm.h + libgdbm_compat.
        self.requires("gdbm/1.23")
        # glib-2.0 pkg-config module for skkdic-expr2 (PKG_CHECK_MODULES(GLIB2, glib-2.0)).
        self.requires("glib2/2.88.0.1")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Force the gdbm branch of configure (gdbm/ndbm.h + -lgdbm[_compat]).
        tc.configure_args.append("--with-gdbm=yes")
        # configure's AC_CHECK_LIB/AC_CHECK_HEADERS probes link and compile
        # small conftests themselves; the dependency -L/-I flags must be
        # visible to those probes, so inject them explicitly (knowledge
        # draft: autotools dep detection macros only do existence checks —
        # headers/libs must be injected through the toolchain).
        incdirs, libdirs = [], []
        for dep in self.dependencies.host.values():
            incdirs.extend(dep.cpp_info.includedirs)
            libdirs.extend(dep.cpp_info.libdirs)
        # The packaged gdbm ships the ndbm compat header flat as
        # <include>/ndbm.h, while configure only accepts <gdbm/ndbm.h>, and
        # dbm_open lives in libgdbm_compat. Provide a gdbm/ndbm.h shim and
        # pre-seed LIBS so both the configure probes and the final link see
        # the ndbm compatibility interface.
        shim_dir = os.path.join(self.build_folder, "compat-include")
        os.makedirs(os.path.join(shim_dir, "gdbm"), exist_ok=True)
        with open(os.path.join(shim_dir, "gdbm", "ndbm.h"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write("/* generated by the skktools Conan recipe:\n"
                     "   redirect <gdbm/ndbm.h> to the flat ndbm.h shipped\n"
                     "   by the gdbm package (libgdbm-compat layout). */\n"
                     "#include <ndbm.h>\n")
        incdirs.append(shim_dir)
        tc.extra_cflags = list(tc.extra_cflags or []) + \
            ["-I" + d for d in incdirs]
        tc.extra_ldflags = list(tc.extra_ldflags or []) + \
            ["-L" + d for d in libdirs]
        from conan.tools.env import Environment
        env = tc.environment()
        env.define("LIBS", "-lgdbm_compat")
        # configure's --with-gdbm branch skips its gdbm_compat + header
        # probes when the first -lgdbm check succeeds (dbm_open actually
        # lives in libgdbm_compat). Pre-seed the autoconf cache with the
        # results that were verified on the device so the branch also
        # probes <gdbm/ndbm.h> (found via the compat shim above) and sets
        # HAVE_GDBM_NDBM_H + LIBS=-lgdbm.
        env.define("ac_cv_lib_gdbm_dbm_open", "yes")
        env.define("ac_cv_lib_gdbm_compat_dbm_open", "yes")
        # E232: on HMDFS the generated configure script itself cannot be
        # executed (exec bits on /storage); configure re-execs through
        # CONFIG_SHELL, so point it at the native OHOS bash.
        import shutil
        config_shell = shutil.which("bash") or "/data/service/hnp/bin/bash"
        env.define("CONFIG_SHELL", config_shell)
        tc.generate(env)
        # configure.ac uses PKG_CHECK_MODULES(GLIB2, glib-2.0 >= 2.0.0);
        # PkgConfigDeps exposes the glib-2.0.pc of the Conan glib2 package.
        PkgConfigDeps(self).generate()

    def build(self):
        # HMDFS does not support umask 077 temp dirs (see knowledge base);
        # also patched in configure itself, this keeps the environment sane.
        os.environ.setdefault("TMPDIR", tempfile.gettempdir())
        import patch_ng
        for name in ("P0001", "P0002", "P0003"):
            # Patches are embedded in the recipe (PATCH_SOURCES above) and
            # applied from memory via patch_ng: this is independent of how
            # any Conan build resolves patch file paths (they differ across
            # Conan builds).
            patchset = patch_ng.fromstring(
                PATCH_SOURCES[name].encode("utf-8"))
            if not patchset:
                from conan.errors import ConanException
                raise ConanException("Failed to parse patch: " + name)
            if not patchset.apply(root=self.source_folder, strip=None):
                from conan.errors import ConanException
                raise ConanException("Failed to apply patch: " + name)
        autotools = Autotools(self)
        # E232 (native-ohos-shell-prefix): when the *build* host is OHOS,
        # HMDFS cannot execute the source configure script directly (exit
        # 126); run it through /system/bin/sh with the exact arguments
        # Conan generated. Other build hosts keep autotools.configure().
        build_os = str(getattr(self, "settings_build").os) \
            if hasattr(self, "settings_build") else ""
        if build_os in ("Ohos", "OHOS"):
            configure = os.path.join(self.source_folder, "configure")
            cargs = autotools._configure_args
            args = cargs if isinstance(cargs, str) else " ".join(cargs)
            self.run('/system/bin/sh "%s" %s' % (configure, args),
                     cwd=self.build_folder)
        else:
            autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_golden_tests()

    def _run_upstream_golden_tests(self):
        """Upstream golden-file suite (equivalent of `make test`).

        Upstream Makefile runs the four test targets from the source tree
        with relative paths (`./skkdic-count test/SKK-JISYO.S ...`), which
        breaks in an out-of-source Conan build folder (and the jobserver
        mkfifo is not permitted on HMDFS). Replicate the four targets
        exactly, comparing against test/result/* byte-for-byte.
        """
        import subprocess

        src = self.source_folder
        bld = self.build_folder

        def tool(name):
            return os.path.join(bld, name)

        def golden(name):
            return os.path.join(src, "test", "result", name)

        def check(target, actual):
            with open(golden(target), "rb") as fh:
                expected = fh.read()
            if actual != expected:
                from conan.errors import ConanException
                raise ConanException(
                    "upstream golden test FAILED: %s\nexpected[:160]=%r\n"
                    "actual[:160]=%r\nlen(expected)=%d len(actual)=%d"
                    % (target, expected[:160], actual[:160],
                       len(expected), len(actual)))
            self.output.info("upstream golden test ok: %s" % target)

        def run_argv(cmd_list):
            proc = subprocess.run(
                cmd_list, cwd=src, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            if proc.returncode != 0:
                from conan.errors import ConanException
                raise ConanException(
                    "command failed (%d): %s\n%s"
                    % (proc.returncode, cmd_list,
                       proc.stderr.decode("utf-8", "replace")))
            return proc.stdout

        def run_shell(cmd_str):
            proc = subprocess.run(
                cmd_str, cwd=src, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            if proc.returncode != 0:
                from conan.errors import ConanException
                raise ConanException(
                    "command failed (%d): %s\n%s"
                    % (proc.returncode, cmd_str,
                       proc.stderr.decode("utf-8", "replace")))
            return proc.stdout

        def q(path):
            return '"' + path.replace("\\", "/") + '"'

        # test_skkdic-count (relative dict path: skkdic-count echoes the
        # given filename into its output, and the golden file expects the
        # same relative "test/SKK-JISYO.S" spelling as upstream make test)
        check("skkdic-count", run_argv([
            tool("skkdic-count"), "test/SKK-JISYO.S",
        ]))
        # test_skkdic-sort (input via stdin)
        with open(os.path.join(src, "test", "SKK-JISYO.S.shuffle"), "rb") as fh:
            shuffle_bytes = fh.read()
        proc = subprocess.run([tool("skkdic-sort")], cwd=src,
                              input=shuffle_bytes, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if proc.returncode != 0:
            from conan.errors import ConanException
            raise ConanException(
                "command failed (%d): skkdic-sort\n%s"
                % (proc.returncode,
                   proc.stderr.decode("utf-8", "replace")))
        check("skkdic-sort", proc.stdout)
        # test_skkdic-expr: split1 + split2 - split3 | skkdic-sort
        expr_cmd = "%s test/SKK-JISYO.S.split1 + test/SKK-JISYO.S.split2 - test/SKK-JISYO.S.split3 | %s" % (
            q(tool("skkdic-expr")), q(tool("skkdic-sort")))
        check("skkdic-expr", run_shell(expr_cmd))
        # test_skkdic-expr2 (glib-based merge)
        expr2_cmd = "%s test/SKK-JISYO.S.split1 + test/SKK-JISYO.S.split2 - test/SKK-JISYO.S.split3 | %s" % (
            q(tool("skkdic-expr2")), q(tool("skkdic-sort")))
        check("skkdic-expr2", run_shell(expr2_cmd))

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # The upstream Makefile builds bin_PROGRAMS into the build folder
        # root (skkdic-expr, skkdic-expr2, skkdic-sort, skkdic-count); it
        # has no install rule usable for a staged prefix, so package the
        # four tools explicitly.
        copy(self, "skkdic-*", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
