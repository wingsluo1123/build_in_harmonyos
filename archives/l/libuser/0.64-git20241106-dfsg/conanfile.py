#!/usr/bin/env python3
"""Conan recipe — libuser 0.64-git20241106-dfsg (Autotools).

libuser is the standardized interface for manipulating and administering
user and group accounts: libuser.so plus the files/shadow back-end modules
and the luseradd/lusermod/lgroupadd/... CLI tools.

Adapted to HarmonyOS PC (OHOS aarch64, native build). See notes.md for the
platform adaptations (minimal configure set, PAM via linux-pam, module
lookup via LIBUSER_CONF in test_package).
"""

import glob
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Upstream automake TESTS, official registration total (Makefile.am):
#   tests/config_test.sh tests/fs_test tests/files_test
#   tests/pwhash_test tests/utils_test (always registered)
#   tests/default_pw_test tests/ldap_test (registered only under
#   `if LDAP` / AM_CONDITIONAL LDAP, i.e. with --with-ldap).
# Official total is 7; this recipe builds --without-ldap (OHOS has no
# LDAP/slapd runtime), so `make check` registers and runs the base 5.
# This is the audited registration total, not a measurement.
UPSTREAM_TEST_TOTAL = 7

_AUTOMAKE_SUMMARY_RE = re.compile(r"^#\s*(TOTAL|PASS|SKIP|XFAIL|FAIL|XPASS|ERROR)\s*:\s*(\d+)\s*$")


class LibuserConan(ConanFile):
    name = "libuser"
    version = "0.64-git20241106-dfsg"
    description = "Standardized interface for manipulating and administering user and group accounts"
    license = "LGPL-2.0-or-later"
    homepage = "https://pagure.io/libuser/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libuser supports Linux and OHOS only, not %s" % str(self.settings.os)
            )

    def requirements(self):
        # glib/gobject/gmodule are hard requirements (configure.ac
        # PKG_CHECK_MODULES for GLIB/GOBJECT/GMODULE).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # popt: all account CLI tools link -lpopt.
        self.requires("popt/1.16")
        # PAM: apps/libapputil.la links -lpam -lpam_misc unconditionally.
        self.requires("linux-pam/1.7.2")
        # proxy-libintl: glib's libintl.h remaps gettext()->g_libintl_* and
        # glib/2.84.0.1 (nls=disabled) keeps proxy-libintl private, so its
        # generated glib-2.0.pc carries no -lintl. Consumers that include
        # glib headers (libuser lib + all apps/* tools) then fail with
        # "undefined symbol: g_libintl_bindtextdomain/gettext/..." (paps
        # 0.8.0 / wv 1.2.9 precedent). Direct static requires closes the
        # loop; the absolute archive path is passed via LIBS below.
        self.requires("proxy-libintl/0.5", options={"shared": False})

    def layout(self):
        basic_layout(self, src_folder=".")
        # NOTE: build()/package() below run entirely inside the source
        # tree (true in-source via explicit cwd=self.source_folder, no
        # Autotools-helper out-of-source dir). This assignment only drops
        # the default extra level; the build never depends on the value.
        self.folders.build = "."

    def source(self):
        # Debian .orig.tar.gz is the upstream tree dumped at the archive
        # root (files like configure.ac live in ./), so strip_root must be
        # False: strip_root=True aborts with "Can't untar a tgz containing
        # files in the root with strip_root enabled".
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        # .pc files for configure's PKG_CHECK_MODULES(GLIB/GOBJECT/GMODULE).
        # The generators folder is explicitly prepended to PKG_CONFIG_PATH so
        # the configure probe finds the Conan-provided glib even when the
        # worker image has no system glib .pc files.
        PkgConfigDeps(self).generate()
        self._alias_gmodule_no_export()
        AutotoolsDeps(self).generate()
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # autopoint: the gettext tool package bakes prefix "/" into its
        # script (datarootdir=//share), so autoreconf's autopoint step
        # looks for //share/gettext/archive.dir.tar.xz and aborts with
        # "infrastructure files for version 0.18.2 not found" (avahi /
        # libzbar / libxklavier precedent). Point it at the relocatable
        # Conan package via the documented gettext_datadir override and
        # expose its aclocal macros for AM_GNU_GETTEXT.
        try:
            gettext_pkg = self.dependencies.build["gettext"].package_folder
        except Exception:
            gettext_pkg = None
        if gettext_pkg:
            gettext_datadir = os.path.join(gettext_pkg, "share", "gettext")
            if os.path.isdir(gettext_datadir):
                env.define("gettext_datadir", gettext_datadir)
            else:
                self.output.warning(
                    "gettext package lacks share/gettext: %s" % gettext_datadir)
            gettext_aclocal = os.path.join(gettext_pkg, "share", "aclocal")
            if os.path.isdir(gettext_aclocal):
                env.prepend_path("ACLOCAL_PATH", gettext_aclocal)
        env.vars(self).save_script("libuser_pkgconfig")

        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.configure_args.extend([
            # Python bindings REQUIRED for the upstream suite: 4 of 5
            # automake TESTS drive `import libuser` (files/fs/pwhash/
            # config python drivers + PYTHONPATH=$(pwd)/python/.libs).
            # --without-python leaves no python/.libs/libuser.so, so every
            # driver fails with ModuleNotFoundError (rule4 missing dep).
            # Worker HNP python3 (aarch64, with Python.h per eigenpy
            # precedent) builds the C extension natively; bindings ship
            # with the package via pyexec_LTLIBRARIES.
            "--with-python",
            # Cyrus SASL back end: no SASL provider in the OHOS registry.
            "--without-sasl",
            # LDAP back end: not needed for the files/shadow back ends.
            "--without-ldap",
            # OHOS has no SELinux userspace.
            "--without-selinux",
            # Linux Audit (libaudit) is not present on OHOS.
            "--without-audit",
            "--disable-nls",
            # Constrained-runner peak-memory guard (rm fork reported
            # "Out of memory" while the tree was under load): skip
            # .deps generation to lower I/O without changing outputs.
            "--disable-dependency-tracking",
        ])
        tc.generate()

    def _alias_gmodule_no_export(self):
        # Upstream glib installs gmodule-no-export-2.0.pc alongside
        # gmodule-2.0.pc (same Libs minus -Wl,--export-dynamic), and
        # libuser configure.ac probes PKG_CHECK_MODULES for
        # "glib-2.0 gmodule-no-export-2.0". The Conan glib recipe only
        # declares a gmodule-2.0 component, so PkgConfigDeps never emits
        # gmodule-no-export-2.0.pc -> configure aborts with
        # "No package 'gmodule-no-export-2.0' found" (true-conan-dep
        # gap, not a system/glib-version issue). Copy the generated
        # gmodule-2.0.pc to gmodule-no-export-2.0.pc in every candidate
        # pc dir (generators folder first, then the glib package's own
        # pkgconfig dirs). Extra --export-dynamic from the plain module
        # pc is harmless for a shared libuser. Precedent:
        # archives/b/babeltrace2/2.1.2/conanfile.py (same copy) and
        # ayatana-indicator-session/26.6.1 (hand-written gio-unix pc).
        candidates = []
        try:
            gen = self.generators_folder
        except Exception:
            gen = None
        if gen and os.path.isdir(gen):
            candidates.append(gen)
        try:
            dep = self.dependencies.get("glib") if hasattr(self.dependencies, "get") else self.dependencies["glib"]
        except Exception:
            dep = None
        if dep is not None:
            try:
                pkg = dep.package_folder
            except Exception:
                pkg = None
            if pkg:
                for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                    d = os.path.join(pkg, sub)
                    if os.path.isdir(d) and d not in candidates:
                        candidates.append(d)
        done = False
        for pc_dir in candidates:
            src = os.path.join(pc_dir, "gmodule-2.0.pc")
            dst = os.path.join(pc_dir, "gmodule-no-export-2.0.pc")
            try:
                if os.path.isfile(src) and not os.path.isfile(dst):
                    shutil.copy2(src, dst)
                    try:
                        with open(dst, "r", encoding="utf-8", errors="replace") as h:
                            text = h.read()
                        lines = []
                        for line in text.splitlines(True):
                            if line.startswith("Name:"):
                                lines.append("Name: gmodule-no-export-2.0\n")
                            else:
                                lines.append(line)
                        with open(dst, "w", encoding="utf-8", newline="\n") as h:
                            h.write("".join(lines))
                    except OSError:
                        pass
                    self.output.info("aliased gmodule-2.0.pc -> gmodule-no-export-2.0.pc in %s" % pc_dir)
                    done = True
                elif os.path.isfile(dst):
                    done = True
            except OSError as exc:
                self.output.warning("alias gmodule-no-export pc failed in %s: %r" % (pc_dir, exc))
        if not done:
            self.output.warning("gmodule-2.0.pc not found in %s; gmodule-no-export alias skipped" % (candidates,))

    def build_requirements(self):
        # Debian git-snapshot .orig.tar.gz ships configure.ac/Makefile.am
        # without the generated configure script, so build() bootstraps it
        # via autoreconf (same approach as abiword-plugin-t602).
        # gettext provides autopoint for AM_GNU_GETTEXT (authselect/avahi
        # precedent): CI worker autoconf lacks autopoint, so autoreconf -fi
        # aborts with "Can't exec autopoint ... exit status: 2" without it.
        # CI #93801 (PR #13254): worker autoreconf -fi aborts with
        # "autom4te: error: need GNU m4 1.4 or later: m4" because this
        # recipe never declared the bootstrap chain: archives/a/automake
        # has empty requirements(), so no autoconf/m4 reaches conanbuild
        # on workers without system m4 (HMBS true-machine has HNP m4, hence
        # preflight passed while CI failed). Full chain per bwm/0.6.3 and
        # libdill/burp2 precedent.
        self.tool_requires("m4/1.4.19")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")

    def _intl_lib_path(self):
        # Absolute proxy-libintl archive for the automake LIBS override
        # (wv 1.2.9 pattern). Prefer the static archive from the direct
        # proxy-libintl/0.5 requires (no runtime NEEDED, no rpath needed);
        # fall back to the glib-bundled proxy-libintl (paps 0.8.0 observed
        # libintl.so inside the glib package lib/). Absolute path keeps old
        # libtool from redirecting -lintl through stale dependency metadata.
        for dep_name in ("proxy-libintl", "glib"):
            try:
                dep = self.dependencies.get(dep_name) if hasattr(self.dependencies, "get") else self.dependencies[dep_name]
            except Exception:
                continue
            if dep is None:
                continue
            try:
                pkg = dep.package_folder
            except Exception:
                pkg = None
            if not pkg:
                continue
            libdir = os.path.join(pkg, "lib")
            for name in ("libintl.a", "libintl.so"):
                cand = os.path.join(libdir, name)
                try:
                    if os.path.isfile(cand):
                        return cand
                except OSError:
                    continue
        return ""

    def _intl_make_snippet(self):
        # " LIBS='...'" for `make -j1` / `make check -j1` command lines.
        # Command-line LIBS overrides only the global automake LIBS;
        # per-target LDADD (-lglib/-lpopt/-lpam/...) stays intact, so this
        # is purely additive. Round-3 (link-time strategy, wv/1.2.9 class):
        # the plain archive path left g_libintl_* UNDEFINED at runtime
        # (shared links passed with undefined refs, then failed relocation
        # in libglib and apps), so force embedding with --whole-archive and
        # bake dependency RUNPATH via libtool -R flags (old libtool turns
        # -R into RUNPATH without clobbering the toolchain LDFLAGS, which
        # carry the OHOS sysroot/target and must stay intact).
        parts = []
        for libdir in self._dep_libdirs():
            # Old libtool rejects relative -R (e.g. "-Rlib"); _dep_libdirs
            # already returns absolute dirs, but guard here so a future
            # caller can never reintroduce the failure.
            if libdir and os.path.isabs(libdir):
                parts.append("-R%s" % libdir)
            else:
                self.output.warning("skipping non-absolute libdir for -R: %r" % (libdir,))
        path = self._intl_lib_path()
        if path:
            parts.append("-Wl,--whole-archive")
            parts.append(path)
            parts.append("-Wl,--no-whole-archive")
            self.output.info("linking proxy-libintl whole-archive via LIBS=%s" % path)
        else:
            self.output.warning("proxy-libintl archive not found; LIBS carries -R only")
        if not parts:
            return ""
        return " LIBS=%s" % shlex.quote(" ".join(parts))

    def _dep_libdirs(self):
        # Absolute libdirs of direct dependencies (glib/popt/linux-pam/
        # proxy-libintl). Used for -R RUNPATH baking and LD_LIBRARY_PATH.
        # NOTE: dep.cpp_info.libdirs are package-relative (typically
        # ["lib"]); they must be joined with dep.package_folder. Using
        # them raw leaks a relative "-Rlib" (which matches the source
        # tree's own lib/ dir via isdir) and old libtool aborts with
        # "argument (-Rlib) to '-R' is not an absolute path".
        dirs = []
        try:
            for dep in self.dependencies.values():
                try:
                    pkg = dep.package_folder
                except Exception:
                    pkg = None
                try:
                    libdirs = dep.cpp_info.libdirs
                except Exception:
                    libdirs = []
                for path in libdirs or []:
                    try:
                        if not path:
                            continue
                        cand = path if os.path.isabs(path) else (os.path.join(pkg, path) if pkg else "")
                        if cand and os.path.isabs(cand) and os.path.isdir(cand) and cand not in dirs:
                            dirs.append(cand)
                    except OSError:
                        continue
        except Exception:
            pass
        return dirs

    def _scrub_stale_la(self):
        # Published GLib-chain packages retain non-relocatable libtool
        # archives whose dependency_libs point at stale //lib/*.la paths;
        # old libtool follows them and mislinks colocated shared objects
        # (wv/1.2.9 OHOS precedent: delete them so libtool selects the
        # colocated .so via -L/-l). Cache-metadata only, never installed.
        removed = 0
        for libdir in self._dep_libdirs():
            try:
                stale = sorted(glob.glob(os.path.join(libdir, "*.la")))
            except OSError:
                continue
            for archive in stale:
                try:
                    os.remove(archive)
                    removed += 1
                    self.output.info("removed stale libtool archive: %s" % archive)
                except OSError as exc:
                    self.output.warning("keep stale libtool archive %s: %r" % (archive, exc))
        if not removed:
            self.output.info("no stale *.la in dep libdirs")

    def _writable_tmpdir(self):
        # HMBS injects a task-private writable TMPDIR (experience 1).
        # Prefer it; fall back to a tree-local tmp dir under umask 022.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                return candidate
        fallback = os.path.join(self.source_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _mktemp_fallback_shim(self, tmpdir):
        # Gate strictly behind HMBS_AUTOCONF_MKTEMP_FALLBACK (experience 1):
        # only then shadow mktemp so "./conf*" calls fail and autoconf
        # falls back to its mkdir path. Otherwise return "" (inactive).
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _pick_shell(self):
        # True shell on the worker, not the recipe host assumption.
        # Prefer the HMBS-injected SHELL/CONFIG_SHELL, then the OHOS
        # system shell, then POSIX fallbacks. First executable wins.
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "/bin/sh"

    def _pick_python(self):
        # Upstream TESTS drivers run `$PYTHON "$srcdir"/xxx.py` via
        # AM_TESTS_ENVIRONMENT, and 4 of 5 TESTS `import libuser` from
        # python/.libs (built only with --with-python). The same worker
        # interpreter is used for configure (AM_PATH_PYTHON via $PYTHON),
        # for `make check PYTHON=...`, and its headers (PYINCLUDEDIR via
        # sysconfig) build the C extension. HMBS_* paths first.
        for candidate in (
            os.environ.get("HMBS_PYTHON3"),
            "/data/service/hnp/bin/python3",
            "/system/bin/python3",
        ):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        for name in ("python3", "python"):
            for d in os.environ.get("PATH", "").split(os.pathsep):
                if not d:
                    continue
                cand = os.path.join(d, name)
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    continue
        return ""

    def _build_cc_for_ohos(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(executables, dict):
            return executables.get("c") or executables.get("cc") or "clang"
        return "clang"

    def _manual_configure_args(self):
        args = ["--prefix=/"]
        if self.options.shared:
            args.append("--enable-shared")
            args.append("--disable-static")
        else:
            args.append("--disable-shared")
            args.append("--enable-static")
        args.extend([
            # Same as generate(): python bindings required for upstream
            # TESTS (import libuser); see comment above.
            "--with-python",
            "--without-sasl",
            "--without-ldap",
            "--without-selinux",
            "--without-audit",
            "--disable-nls",
            # Same peak-memory guard as generate(): --disable-dependency
            # -tracking only skips .deps files, no behavior change.
            # Python bindings stay enabled: 4 of 5 automake TESTS need
            # python/.libs/libuser.so (ModuleNotFoundError otherwise).
            "--disable-dependency-tracking",
        ])
        if str(self.settings.os) == "OHOS":
            # Force cross mode (build != host) with triplets that even
            # this era config.sub recognizes: the preflight/CI profiles
            # use OHOS for both host and build contexts, so the helper
            # declares a native build and configure tries to EXECUTE its
            # CC sanity binary -> "cannot run C compiled programs" in
            # this sandbox ("If you meant to cross compile, use
            # '--host'"). The OHOS SDK clang IS a cross toolchain
            # (sysroot/target flags), so declaring cross is honest and
            # makes configure skip execution tests. Build-time helpers
            # (CC_FOR_BUILD) still execute natively: the worker itself
            # is aarch64. `make check` programs are unaffected: automake
            # TESTS run regardless of cross_compiling.
            args.append("--build=x86_64-pc-linux-gnu")
            args.append("--host=aarch64-unknown-linux-gnu")
        return args

    def build(self):
        apply_conandata_patches(self)
        # Round-3 link-time fix (wv/1.2.9 precedent): drop stale *.la
        # metadata from dependency libdirs before autoreconf/configure so
        # old libtool links the colocated shared objects via -L/-l.
        self._scrub_stale_la()
        # libtoolize aux-dir heuristic scans ./../.. for install-sh; make
        # sure . wins so ltmain.sh lands in the source root.
        install_sh = os.path.join(self.source_folder, "install-sh")
        if not os.path.exists(install_sh):
            with open(install_sh, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n# placeholder for libtoolize aux-dir heuristic\n")
        # OHOS: sgml docs need linuxdoc-tools (sgml2txt/sgml2html),
        # unavailable on the worker. Yocto/Gentoo precedent
        # (disable-sgml-doc.patch / nodocs.patch): drop the sgml
        # outputs from `all` and turn their recipes into no-ops so
        # `make -j1`/`make install` succeed without the tools. The
        # libuser.conf.5 man-page rule is kept intact.
        docs_am = os.path.join(self.source_folder, "docs", "Makefile.am")
        try:
            if os.path.isfile(docs_am):
                with open(docs_am, "r", encoding="utf-8", errors="replace") as handle:
                    docs_content = handle.read()
                docs_orig = docs_content
                # 1) `all: sgml/libuser.txt sgml/libuser.html` -> keep
                # only the man page so sgml tools are never invoked.
                docs_content = re.sub(
                    r"^all\s*:.*$",
                    "all: libuser.conf.5",
                    docs_content,
                    flags=re.MULTILINE,
                )
                # 2) Neutralize any remaining sgml2txt/sgml2html recipe
                # lines (matched loosely across versions).
                neutralized = []
                for line in docs_content.splitlines(True):
                    if "sgml2txt" in line or "sgml2html" in line:
                        neutralized.append("\t@: sgml docs disabled on OHOS (no linuxdoc-tools)\n")
                    else:
                        neutralized.append(line)
                docs_content = "".join(neutralized)
                if docs_content != docs_orig:
                    with open(docs_am, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(docs_content)
                    self.output.info("patched docs/Makefile.am: sgml docs disabled (sgml2txt/sgml2html no-op)")
                else:
                    self.output.warning("docs/Makefile.am sgml rules not found; sgml patch left as-is")
            else:
                self.output.warning("docs/Makefile.am not found at %s; sgml patch skipped" % docs_am)
        except OSError as exc:
            self.output.warning("patch docs/Makefile.am sgml docs failed: %r" % (exc,))
        # OHOS: gtk-doc tooling is unavailable. docs/reference/Makefile.am
        # includes gtk-doc.make, so automake fails without it:
        #   ".automake-real: error: cannot open < docs/reference/gtk-doc.make"
        # (same root cause as libgsf/libaccounts). autoreconf installs
        # missing aux files but never creates gtk-doc.make; provide minimal
        # stubs so `autoreconf -fi` can complete. Docs stay disabled via
        # the ENABLE_GTK_DOC=false conditional below, no doc content changes.
        gtk_doc_stub = (
            "# gtk-doc disabled (OHOS stub)\n"
            "# Minimal definitions for variables appended to with +=\n"
            "# in docs/reference/Makefile.am.\n"
            "CLEANFILES =\n"
            "EXTRA_DIST =\n"
        )
        for rel in ("docs/reference/gtk-doc.make", "gtk-doc.make"):
            stub_path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(stub_path):
                parent = os.path.dirname(stub_path)
                if parent and not os.path.isdir(parent):
                    os.makedirs(parent, exist_ok=True)
                with open(stub_path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(gtk_doc_stub)
        # Round 2: docs/reference/Makefile.am:80 guards docs with
        # `if ENABLE_GTK_DOC`, but the gtk-doc.m4 macro providing that
        # AM_CONDITIONAL is absent on the OHOS worker, so automake aborts
        # with "ENABLE_GTK_DOC does not appear in AM_CONDITIONAL".
        # Same class as libaccounts: neutralize the upstream GTK_DOC_CHECK
        # call and define the conditional as always-false. Docs stay
        # disabled, no --enable-gtk-doc flag remains.
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        try:
            with open(configure_ac, "r", encoding="utf-8", errors="replace") as handle:
                ac_content = handle.read()
            patched = re.sub(
                r"^[ \t]*GTK_DOC_CHECK[^\n]*$",
                "AM_CONDITIONAL([ENABLE_GTK_DOC], [false])",
                ac_content,
                flags=re.MULTILINE,
            )
            if patched != ac_content:
                with open(configure_ac, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(patched)
            else:
                self.output.warning("GTK_DOC_CHECK not found in configure.ac; ENABLE_GTK_DOC left as-is")
        except OSError as exc:
            self.output.warning("patch configure.ac GTK_DOC_CHECK failed: %r" % (exc,))
        # OHOS secure_getenv fallback (musl/Yocto class): configure reports
        # neither secure_getenv nor __secure_getenv, so lib/config.c hits
        # `#error Neither secure_getenv ...`. Precedent is Yocto's
        # issetugid patch (Khem Raj): probe issetugid, and when even that
        # is absent fall back to a uid/gid-equality guard around getenv
        # (getuid!=geteuid || getgid!=getegid -> NULL, else getenv).
        # Applied as in-recipe text edits before autoreconf (no new patch
        # files, one-PR-one-lib).
        try:
            if os.path.isfile(configure_ac):
                with open(configure_ac, "r", encoding="utf-8", errors="replace") as handle:
                    ac_text = handle.read()
                if "issetugid" not in ac_text:
                    ac_text2 = re.sub(
                        r"AC_CHECK_FUNCS\(\[__secure_getenv secure_getenv\]\)",
                        "AC_CHECK_FUNCS([__secure_getenv secure_getenv])\nAC_CHECK_FUNCS([issetugid])",
                        ac_text,
                    )
                    if ac_text2 != ac_text:
                        with open(configure_ac, "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(ac_text2)
                        self.output.info("patched configure.ac: added issetugid probe")
                    else:
                        self.output.warning("secure_getenv probe line not found; issetugid probe skipped")
        except OSError as exc:
            self.output.warning("patch configure.ac issetugid failed: %r" % (exc,))
        config_c = os.path.join(self.source_folder, "lib", "config.c")
        try:
            if os.path.isfile(config_c):
                with open(config_c, "r", encoding="utf-8", errors="replace") as handle:
                    cfg_text = handle.read()
                cfg_orig = cfg_text
                if "safe_getenv_uidcheck" not in cfg_text:
                    # Ensure <unistd.h> for getuid/geteuid/getgid/getegid.
                    if "unistd.h" not in cfg_text:
                        cfg_text = re.sub(
                            r"(#include\s*<stdlib\.h>)",
                            r"\1\n#include <unistd.h>",
                            cfg_text,
                            count=1,
                        )
                    # Insert issetugid branch before the #else (Yocto).
                    if "HAVE_ISSETUGID" not in cfg_text:
                        cfg_text = re.sub(
                            r"(#[ \t]*elif[^\n]*HAVE___SECURE_GETENV[^\n]*\n[^\n]*safe_getenv[^\n]*\n)",
                            r"\1#elif defined(HAVE_ISSETUGID)\n# define safe_getenv(string) safe_getenv_issetugid(string)\n",
                            cfg_text,
                            count=1,
                        )
                    # Replace the hard #error with a uid/gid-guarded
                    # getenv fallback (works even without issetugid).
                    cfg_text = re.sub(
                        r"^[ \t]*#[ \t]*error[^\n]*[Ss]ecure_getenv[^\n]*$",
                        "# define safe_getenv(string) safe_getenv_uidcheck(string)",
                        cfg_text,
                        flags=re.MULTILINE,
                    )
                    # Provide the fallback helpers after the safe_getenv
                    # #endif block (first occurrence).
                    fallback_helpers = (
                        "\n"
                        "#ifdef HAVE_ISSETUGID\n"
                        "static const char *\n"
                        "safe_getenv_issetugid(const char *name)\n"
                        "{\n"
                        "\tif (issetugid ())\n"
                        "\t\treturn 0;\n"
                        "\treturn getenv (name);\n"
                        "}\n"
                        "#endif\n"
                        "#if !defined(HAVE_SECURE_GETENV) && !defined(HAVE___SECURE_GETENV) && !defined(HAVE_ISSETUGID)\n"
                        "static const char *\n"
                        "safe_getenv_uidcheck(const char *name)\n"
                        "{\n"
                        "\tif (getuid () != geteuid () || getgid () != getegid ())\n"
                        "\t\treturn 0;\n"
                        "\treturn getenv (name);\n"
                        "}\n"
                        "#endif\n"
                    )
                    # Anchor: the #endif closing the safe_getenv chain.
                    # Fall back to file end if the shape differs.
                    anchor = re.search(
                        r"#\s*define\s+safe_getenv\(string\)\s+safe_getenv_uidcheck\(string\)\s*\n(#\s*endif[^\n]*\n)",
                        cfg_text,
                    )
                    if anchor:
                        insert_at = anchor.end()
                        cfg_text = cfg_text[:insert_at] + fallback_helpers + cfg_text[insert_at:]
                    else:
                        cfg_text = cfg_text + fallback_helpers
                    if cfg_text != cfg_orig:
                        with open(config_c, "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(cfg_text)
                        self.output.info("patched lib/config.c: secure_getenv fallback (issetugid + uidcheck)")
                    else:
                        self.output.warning("lib/config.c secure_getenv block not matched; patch left as-is")
            else:
                self.output.warning("lib/config.c not found at %s; secure_getenv patch skipped" % config_c)
        except OSError as exc:
            self.output.warning("patch lib/config.c secure_getenv failed: %r" % (exc,))
        # OHOS/musl getusershell fallback (BSD shells API): python/
        # libusermodule.c implements get_user_shells via
        # setusershell/getusershell/endusershell (<unistd.h> on glibc),
        # but the OHOS libc provides none of them, so clang reports
        # implicit declarations plus `-Wint-conversion` (getusershell
        # assumed int) and `make -j1` stops in python/. Probe the three
        # symbols and, when absent, compile a minimal /etc/shells reader
        # with glibc fallback semantics (/bin/sh + /bin/csh when the
        # file is missing/unreadable). In-recipe text edits, no new
        # patch files, one-PR-one-lib.
        try:
            if os.path.isfile(configure_ac):
                with open(configure_ac, "r", encoding="utf-8", errors="replace") as handle:
                    ac_shell = handle.read()
                if "getusershell" not in ac_shell:
                    ac_shell2 = ac_shell
                    if "AC_CHECK_FUNCS([issetugid])" in ac_shell2:
                        ac_shell2 = ac_shell2.replace(
                            "AC_CHECK_FUNCS([issetugid])",
                            "AC_CHECK_FUNCS([issetugid])\nAC_CHECK_FUNCS([getusershell setusershell endusershell])",
                            1,
                        )
                    elif "AC_CHECK_FUNCS([__secure_getenv secure_getenv])" in ac_shell2:
                        ac_shell2 = ac_shell2.replace(
                            "AC_CHECK_FUNCS([__secure_getenv secure_getenv])",
                            "AC_CHECK_FUNCS([__secure_getenv secure_getenv])\nAC_CHECK_FUNCS([getusershell setusershell endusershell])",
                            1,
                        )
                    if ac_shell2 != ac_shell:
                        with open(configure_ac, "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(ac_shell2)
                        self.output.info("patched configure.ac: added getusershell probe")
                    else:
                        self.output.warning("getusershell probe anchor not found; probe skipped")
        except OSError as exc:
            self.output.warning("patch configure.ac getusershell failed: %r" % (exc,))
        try:
            shell_mod = os.path.join(self.source_folder, "python", "libusermodule.c")
            if os.path.isfile(shell_mod):
                with open(shell_mod, "r", encoding="utf-8", errors="replace") as handle:
                    mod_text = handle.read()
                if "hmbs_shells_fp" not in mod_text:
                    fallback_c = (
                        "\n"
                        "#ifndef HAVE_GETUSERSHELL\n"
                        "/* OHOS/musl: no BSD getusershell family. Minimal\n"
                        " * /etc/shells reader with glibc semantics (fall back to\n"
                        " * /bin/sh + /bin/csh when the file is missing/unreadable).\n"
                        " * Guarded by configure's AC_CHECK_FUNCS probe above; the\n"
                        " * three functions come as a family on every libc.\n"
                        " */\n"
                        "#include <stdio.h>\n"
                        "#include <string.h>\n"
                        "static FILE *hmbs_shells_fp = NULL;\n"
                        "static char hmbs_shell_buf[1024];\n"
                        "static const char *hmbs_fallback_shells[] = {\"/bin/sh\", \"/bin/csh\", NULL};\n"
                        "static int hmbs_fallback_idx = 0;\n"
                        "static void setusershell(void)\n"
                        "{\n"
                        "    if (hmbs_shells_fp != NULL) { fclose(hmbs_shells_fp); hmbs_shells_fp = NULL; }\n"
                        "    hmbs_fallback_idx = 0;\n"
                        "    hmbs_shells_fp = fopen(\"/etc/shells\", \"r\");\n"
                        "}\n"
                        "static void endusershell(void)\n"
                        "{\n"
                        "    if (hmbs_shells_fp != NULL) { fclose(hmbs_shells_fp); hmbs_shells_fp = NULL; }\n"
                        "    hmbs_fallback_idx = 0;\n"
                        "}\n"
                        "static char *getusershell(void)\n"
                        "{\n"
                        "    if (hmbs_shells_fp == NULL) { setusershell(); }\n"
                        "    if (hmbs_shells_fp != NULL) {\n"
                        "        while (fgets(hmbs_shell_buf, sizeof(hmbs_shell_buf), hmbs_shells_fp) != NULL) {\n"
                        "            size_t n = strlen(hmbs_shell_buf);\n"
                        "            while (n > 0 && (hmbs_shell_buf[n - 1] == 10 || hmbs_shell_buf[n - 1] == 13)) { hmbs_shell_buf[--n] = 0; }\n"
                        "            if (n == 0 || hmbs_shell_buf[0] == '#') { continue; }\n"
                        "            return hmbs_shell_buf;\n"
                        "        }\n"
                        "        return NULL;\n"
                        "    }\n"
                        "    if (hmbs_fallback_shells[hmbs_fallback_idx] != NULL) { return (char *)hmbs_fallback_shells[hmbs_fallback_idx++]; }\n"
                        "    return NULL;\n"
                        "}\n"
                        "#endif\n"
                    )
                    anchor_m = re.search(r'#include\s+"common\.h"\s*\n', mod_text)
                    if anchor_m:
                        at = anchor_m.end()
                        mod_text = mod_text[:at] + fallback_c + mod_text[at:]
                        with open(shell_mod, "w", encoding="utf-8", newline="\n") as handle:
                            handle.write(mod_text)
                        self.output.info("patched python/libusermodule.c: getusershell fallback")
                    else:
                        self.output.warning("common.h include not found; getusershell fallback skipped")
            else:
                self.output.warning("python/libusermodule.c not found at %s; getusershell patch skipped" % shell_mod)
        except OSError as exc:
            self.output.warning("patch python/libusermodule.c getusershell failed: %r" % (exc,))
        # Experience 1 (libcitadel/917): explicit writable TMPDIR for this
        # old-autoconf tree; mktemp shim only when HMBS signals fallback.
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        shim_dir = self._mktemp_fallback_shim(tmpdir)
        if shim_dir:
            old_path = os.environ.get("PATH", "")
            if not old_path.startswith(shim_dir):
                os.environ["PATH"] = shim_dir + os.pathsep + old_path
        # Preflight 2026-10-16 (PR #13254): same Perl_my_cxt_init crash
        # persists after the 10-15 all-conan attempt, so switch to the
        # proven single-Perl route (ytnef/2.1.2, zzuf/0.15): system perl
        # plus Conan automake/autoconf pure-perl shares only.
        tool_bins = []
        for _tname in ("autoconf", "automake", "libtool", "m4", "gettext"):
            try:
                if hasattr(self.dependencies.build, "get"):
                    _tdep = self.dependencies.build.get(_tname)
                else:
                    try:
                        _tdep = self.dependencies.build[_tname]
                    except Exception:
                        _tdep = None
            except Exception:
                _tdep = None
            if _tdep is None:
                continue
            try:
                _tpkg = _tdep.package_folder
            except Exception:
                _tpkg = None
            if not _tpkg:
                continue
            _tbin = os.path.join(_tpkg, "bin")
            try:
                if os.path.isdir(_tbin) and _tbin not in tool_bins:
                    tool_bins.append(_tbin)
            except OSError:
                continue
        def _pkg_of(_name):
            try:
                if hasattr(self.dependencies.build, "get"):
                    _d = self.dependencies.build.get(_name)
                else:
                    try:
                        _d = self.dependencies.build[_name]
                    except Exception:
                        _d = None
            except Exception:
                _d = None
            if _d is None:
                return ""
            try:
                return _d.package_folder or ""
            except Exception:
                return ""
        _perl5lib_dirs = []
        _am_pkg = _pkg_of("automake")
        if _am_pkg:
            try:
                for _cand in sorted(glob.glob(os.path.join(_am_pkg, "share", "automake-*"))):
                    if os.path.isdir(_cand) and _cand not in _perl5lib_dirs:
                        _perl5lib_dirs.append(_cand)
            except OSError:
                pass
        _ac_pkg = _pkg_of("autoconf")
        if _ac_pkg:
            _ac_share = os.path.join(_ac_pkg, "share", "autoconf")
            try:
                if os.path.isdir(_ac_share) and _ac_share not in _perl5lib_dirs:
                    _perl5lib_dirs.append(_ac_share)
            except OSError:
                pass
        _sys_perl = ""
        for _cand in ("/data/service/hnp/bin/perl", "/system/bin/perl", "/bin/perl", "/usr/bin/perl"):
            try:
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    _sys_perl = _cand
                    break
            except OSError:
                continue
        if not _sys_perl:
            for _d in os.environ.get("PATH", "").split(os.pathsep):
                if not _d or _d in tool_bins or "conan-home" in _d:
                    continue
                _cand = os.path.join(_d, "perl")
                try:
                    if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                        _sys_perl = _cand
                        break
                except OSError:
                    continue
        _path_prefix = ":".join(tool_bins) + ":" if tool_bins else ""
        _perl5lib = ":".join(_perl5lib_dirs)
        if _sys_perl:
            self.output.info("autoreconf with system perl %s PERL5LIB=%s" % (_sys_perl, _perl5lib))
            _perl_prefix = "PERL=%s PERL5LIB=%s " % (shlex.quote(_sys_perl), shlex.quote(_perl5lib))
        elif _perl5lib:
            self.output.warning("system perl not found; autoreconf with PERL unset + PERL5LIB=%s" % (_perl5lib,))
            _perl_prefix = "PERL5LIB=%s " % shlex.quote(_perl5lib)
        else:
            self.output.warning("system perl and automake shares not found; autoreconf without PERL override")
            _perl_prefix = ""
        _conan_m4 = ""
        for _b in tool_bins:
            _cand = os.path.join(_b, "m4")
            try:
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    _conan_m4 = _cand
                    break
            except OSError:
                continue
        _m4_prefix = "M4=%s " % shlex.quote(_conan_m4) if _conan_m4 else ""
        try:
            os.makedirs(os.path.join(self.source_folder, "m4"), exist_ok=True)
        except OSError:
            pass
        _autoreconf_cmd = "autoreconf"
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "PATH=\"%s$PATH\" %s%s%s -fi" % (
                tmpdir, tmpdir, tmpdir, _path_prefix, _perl_prefix, _m4_prefix, _autoreconf_cmd),
            cwd=self.source_folder,
            env="conanbuild",
        )
        # E114 HMDFS: autoconf emits `umask 077` for its temp dirs, which
        # become unwritable under HMDFS setgid handling; relax to 022.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        # (helper intentionally unused here; see comment below)
        try:
            os.umask(0o022)
        except OSError:
            pass
        # True in-source manual configure (libcitadel/917 proven route):
        # never enter the Autotools-helper out-of-source dir whose cwd
        # the old configure cannot re-resolve on this worker
        # ("working directory cannot be determined" + cascading getcwd
        # failures while the helper-invoked shell starts). Run the
        # freshly generated source-tree configure with an explicit
        # worker-verified SHELL/CONFIG_SHELL, writable TMPDIR, umask 022.
        shell = self._pick_shell()
        build_cc = self._build_cc_for_ohos()
        # Python bindings: pin the same worker interpreter for configure's
        # AM_PATH_PYTHON (via $PYTHON) so PYINCLUDEDIR comes from headers
        # that can actually build python/.libs/libuser.so for make check.
        cfg_python = self._pick_python()
        if cfg_python:
            os.environ["PYTHON"] = cfg_python
            self.output.info("configure PYTHON=%s" % cfg_python)
        else:
            self.output.warning("no python3 for configure; python binding may not build")
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            raise ConanInvalidConfiguration(
                "configure not found in source tree: %s" % configure_path
            )
        configure_args = " ".join(shlex.quote(a) for a in self._manual_configure_args())
        for key in ("SHELL", "CONFIG_SHELL"):
            os.environ[key] = shell
        try:
            os.chmod(self.source_folder, 0o755)
        except OSError:
            pass
        try:
            os.chmod(tmpdir, 0o755)
        except OSError:
            pass
        path_prefix = ("%s:" % shim_dir) if shim_dir else ""
        cfg_python_prefix = ("PYTHON=\"%s\" " % cfg_python) if cfg_python else ""
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "CONFIG_SHELL=\"%s\" SHELL=\"%s\" "
            "%sCC_FOR_BUILD=\"%s\" CPP_FOR_BUILD=\"%s -E\" "
            "PATH=\"%s$PATH\" "
            "\"%s\" \"%s\" %s"
            % (tmpdir, tmpdir, tmpdir, shell, shell, cfg_python_prefix,
               build_cc, build_cc,
               path_prefix, shell, configure_path, configure_args),
            cwd=self.source_folder,
            env="conanbuild",
        )
        # R9/single-job: parallel make hits HMDFS-backed build dirs.
        # proxy-libintl LIBS (g_libintl_* closure): command-line LIBS only
        # overrides the global automake LIBS; per-target LDADD stays intact.
        intl_snippet = self._intl_make_snippet()
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "CONFIG_SHELL=\"%s\" SHELL=\"%s\" make -j1%s"
            % (tmpdir, tmpdir, tmpdir, shell, shell, intl_snippet),
            cwd=self.source_folder,
            env="conanbuild",
        )
        # Upstream official suite (automake TESTS). Best-effort so a
        # platform-gated test failure never hides the evidence marker;
        # counts below are parsed from the real test-suite.log.
        self._diagnose_link()
        self._run_upstream_checks()

    def _find_test_suite_logs(self):
        hits = []
        for root in (self.source_folder, self.build_folder):
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                if "test-suite.log" in filenames:
                    hits.append(os.path.join(dirpath, "test-suite.log"))
        unique = []
        for path in hits:
            if path not in unique:
                unique.append(path)
        return unique

    def _parse_automake_summary(self, path):
        counts = {}
        tail = ""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return None, ""
        for line in text.splitlines():
            match = _AUTOMAKE_SUMMARY_RE.match(line.strip())
            if match:
                counts[match.group(1)] = int(match.group(2))
        tail = "\n".join(text.splitlines()[-15:])
        return counts, tail

    def _emit_upstream_marker(self, check_rc, check_detail):
        command = "make check -j1 PYTHON=<worker python3> (automake TESTS, LDAP/SASL disabled, python bindings enabled, see test_package/MANIFEST.yml audit)"
        logs = self._find_test_suite_logs()
        counts = None
        tail = ""
        if logs:
            counts, tail = self._parse_automake_summary(logs[0])
        gaps = []
        if counts and "TOTAL" in counts:
            log_total = counts.get("TOTAL", 0)
            passed = counts.get("PASS", 0) + counts.get("XFAIL", 0)
            failed = counts.get("FAIL", 0) + counts.get("XPASS", 0) + counts.get("ERROR", 0)
            skipped = counts.get("SKIP", 0)
            executed = passed + failed
            status = "passed" if failed == 0 else "failed"
            reason = "automake test-suite.log parsed (%s); make check rc=%s" % (logs[0], check_rc)
            # Official registration total is 7 (Makefile.am TESTS: base 5
            # plus tests/default_pw_test + tests/ldap_test under `if LDAP`).
            # This recipe builds --without-ldap (OHOS has no LDAP/slapd
            # runtime), so `make check` registers only the base 5 and
            # test-suite.log TOTAL is 5. Report discovered as the official
            # total 7 and carry the 2 LDAP-conditional entries as an
            # explicit ohos_feature gap (not missing_dependency: even with
            # libldap, both scripts require /usr/sbin/slapd plus
            # ldapadd/ldapsearch and an OpenSSL-issued key, none of which
            # exists on the OHOS worker; tests/ldap_test exits 77 without
            # slapd by upstream design).
            discovered = log_total
            if log_total != UPSTREAM_TEST_TOTAL:
                reason += "; NOTE: test-suite.log TOTAL=%s vs official Makefile.am audit total %s (base 5 + LDAP-conditional default_pw_test/ldap_test, unregistered with --without-ldap)" % (
                    log_total, UPSTREAM_TEST_TOTAL)
            if log_total < UPSTREAM_TEST_TOTAL:
                discovered = UPSTREAM_TEST_TOTAL
                gaps.append({
                    "count": UPSTREAM_TEST_TOTAL - log_total,
                    "category": "ohos_feature",
                    "detail": "tests/default_pw_test + tests/ldap_test register only under `if LDAP` (Makefile.am TESTS += under AM_CONDITIONAL LDAP); recipe builds --without-ldap because OHOS has no LDAP/slapd runtime, so these 2 never register in `make check`; upstream tests/ldap_test exits 77 without /usr/sbin/slapd and tests/default_pw_test skips ldap module combos without slapd",
                    "evidence": "Makefile.am: TESTS = tests/config_test.sh tests/fs_test tests/files_test tests/pwhash_test tests/utils_test; if LDAP: TESTS += tests/default_pw_test tests/ldap_test; tests/ldap_test: [ ! -x /usr/sbin/slapd ] -> exit 77",
                })
            if failed:
                # utils_test files-backend locking fails on the worker
                # ("Cannot obtain lock ... group.lock: Operation not
                # permitted", hardlink/chmod unsupported) while the binary
                # itself runs: classify that single entry as ohos_feature
                # with its own evidence instead of generic test_failure.
                lock_hit = False
                try:
                    with open(logs[0], "r", encoding="utf-8", errors="replace") as handle:
                        full_log = handle.read()
                    lock_hit = ("Cannot obtain lock" in full_log
                                and "Operation not permitted" in full_log)
                except OSError:
                    full_log = ""
                if lock_hit and failed >= 1:
                    lock_tail = full_log[-800:]
                    gaps.append({
                        "count": 1,
                        "category": "ohos_feature",
                        "detail": "tests/utils_test files-backend lock files (group.lock) get Operation not permitted on the worker filesystem; test binary runs, locking unsupported",
                        "evidence": lock_tail,
                    })
                    if failed - 1 > 0:
                        gaps.append({
                            "count": failed - 1,
                            "category": "test_failure",
                            "detail": "remaining automake FAIL/XPASS/ERROR entries in test-suite.log",
                            "evidence": tail[-800:],
                        })
                else:
                    gaps.append({
                        "count": failed,
                        "category": "test_failure",
                        "detail": "automake FAIL/XPASS/ERROR entries in test-suite.log",
                        "evidence": tail[-800:],
                    })
            if skipped:
                gaps.append({
                    "count": skipped,
                    "category": "environment",
                    "detail": "automake SKIP entries (exit 77); per-test cause taken from the log tail",
                    "evidence": tail[-800:],
                })
        else:
            # No log: report honestly, claim nothing ran. discovered stays
            # the audited registration total so the gate can verify identity.
            discovered, executed, passed, failed, skipped = UPSTREAM_TEST_TOTAL, 0, 0, 0, 0
            status = "failed"
            searched = [p for p in (self.source_folder, self.build_folder) if p]
            reason = "test-suite.log not found (searched %s); make check rc=%s; %s" % (
                "; ".join(searched), check_rc, check_detail[:500])
            gaps.append({
                "count": UPSTREAM_TEST_TOTAL,
                "category": "environment",
                "detail": "upstream suite produced no test-suite.log; audited TESTS unexecuted",
                "evidence": reason[-800:],
            })
        marker = {
            "status": status,
            "framework": "autotools-make-check",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
        }
        if gaps:
            marker["gaps"] = gaps
        try:
            persisted_src = os.path.join(self.source_folder, "hmbs_upstream.json")
            with open(persisted_src, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
        except OSError as exc:
            self.output.warning("persist upstream marker failed: %r" % (exc,))
        message = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        try:
            print(message, flush=True)
        except OSError:
            pass
        self.output.info(message)

    def _runtime_libdirs(self):
        # stale_runtime_library: test processes resolved system old .so
        # instead of the just-built tree + Conan deps (g_str_equal /
        # g_ascii_table from glib, g_libintl_* from proxy-libintl). Collect
        # every build-tree .libs dir plus every dependency libdir so the
        # make-check runtime finds the current products first.
        # ykclient/2.15 + irqbalance + xz precedent (LD_LIBRARY_PATH for
        # make check); only used for the check runtime, never for
        # configure/compile (xmlsec lesson: LD_LIBRARY_PATH then poisons
        # the SDK lld at link time).
        dirs = []
        try:
            roots = [p for p in (self.source_folder, self.build_folder) if p]
        except Exception:
            roots = []
        for root in roots:
            try:
                if not root or not os.path.isdir(root):
                    continue
                for dirpath, dirnames, _filenames in os.walk(root):
                    if os.path.basename(dirpath) == ".libs":
                        if dirpath not in dirs:
                            dirs.append(dirpath)
            except OSError:
                continue
        for path in self._dep_libdirs():
            if path not in dirs:
                dirs.append(path)
        return [d for d in dirs if d and os.path.isdir(d)]

    def _is_elf_shared(self, path):
        # LD_PRELOAD needs a real ELF object: a plain ".so" is often a
        # text linker script (INPUT(...)), which the loader rejects.
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _shared_intl_path(self):
        # Round-2 learning: the Conan libglib-2.0.so itself has undefined
        # g_libintl_gettext/dcgettext/dngettext, so preloading glib alone
        # cannot help. The glib package ships the shared provider
        # (wv/1.2.9 _glib_proxy_libintl_path asserts libintl.so|.a inside
        # the glib package libdir); prefer that versioned ELF for the
        # test-only LD_PRELOAD chain. proxy-libintl/0.5 is static-only on
        # OHOS by its own validate(), so it is only a link-time archive.
        search_dirs = []
        for dep_name in ("glib", "proxy-libintl"):
            try:
                dep = self.dependencies.get(dep_name) if hasattr(self.dependencies, "get") else self.dependencies[dep_name]
            except Exception:
                continue
            if dep is None:
                continue
            try:
                pkg_for_libdirs = None
                try:
                    pkg_for_libdirs = dep.package_folder
                except Exception:
                    pkg_for_libdirs = None
                for path in (dep.cpp_info.libdirs or []):
                    if not path:
                        continue
                    cand_libdir = path if os.path.isabs(path) else (os.path.join(pkg_for_libdirs, path) if pkg_for_libdirs else "")
                    if cand_libdir and os.path.isabs(cand_libdir) and os.path.isdir(cand_libdir) and cand_libdir not in search_dirs:
                        search_dirs.append(cand_libdir)
            except Exception:
                pass
            try:
                pkg = dep.package_folder
            except Exception:
                pkg = None
            if pkg:
                for sub in ("lib", "lib64"):
                    cand = os.path.join(pkg, sub)
                    if os.path.isdir(cand) and cand not in search_dirs:
                        search_dirs.append(cand)
        cands = []
        for libdir in search_dirs:
            try:
                found = sorted(glob.glob(os.path.join(libdir, "libintl.so*")))
            except OSError:
                continue
            cands.extend(found)
        # Prefer versioned files; verify ELF (skip linker-script stubs).
        for cand in cands:
            try:
                if os.path.isfile(cand) and ".so." in cand and self._is_elf_shared(cand):
                    self.output.info("shared intl provider for test preload: %s" % cand)
                    return cand
            except OSError:
                continue
        for cand in cands:
            try:
                if os.path.isfile(cand) and self._is_elf_shared(cand):
                    self.output.info("shared intl provider for test preload: %s" % cand)
                    return cand
            except OSError:
                continue
        self.output.warning("no shared libintl.so found in %s; glib runtime symbols may stay unresolved" % (search_dirs,))
        return ""

    def _check_preloads(self):
        # OHOS loader ignores LD_LIBRARY_PATH, so LD_PRELOAD for the check
        # command only (HMBS platform diagnosis). Round-2 fix: the chain
        # must START with the shared intl provider (glib's libintl.so),
        # because libglib-2.0.so itself needs g_libintl_* at relocation;
        # then the freshly built libuser, then the glib trio. Round-1 only
        # preloaded libuser+glib (same broken lib, symbols still missing).
        preloads = []
        intl_so = self._shared_intl_path()
        if intl_so:
            preloads.append(intl_so)
        try:
            src = self.source_folder
        except Exception:
            src = None
        if src:
            cands = sorted(glob.glob(os.path.join(src, "lib", ".libs", "libuser.so*")))
            pick = None
            for cand in cands:
                try:
                    if os.path.isfile(cand) and ".so." in cand:
                        pick = cand
                        break
                except OSError:
                    continue
            if pick is None:
                for cand in cands:
                    try:
                        if os.path.isfile(cand):
                            pick = cand
                            break
                    except OSError:
                        continue
            if pick:
                preloads.append(pick)
        try:
            dep = None
            try:
                dep = self.dependencies.get("glib") if hasattr(self.dependencies, "get") else self.dependencies["glib"]
            except Exception:
                dep = None
            search_dirs = []
            if dep is not None:
                try:
                    pkg_for_glib = None
                    try:
                        pkg_for_glib = dep.package_folder
                    except Exception:
                        pkg_for_glib = None
                    for path in (dep.cpp_info.libdirs or []):
                        if not path:
                            continue
                        cand_dir = path if os.path.isabs(path) else (os.path.join(pkg_for_glib, path) if pkg_for_glib else "")
                        if cand_dir and os.path.isabs(cand_dir) and os.path.isdir(cand_dir) and cand_dir not in search_dirs:
                            search_dirs.append(cand_dir)
                except Exception:
                    pass
                try:
                    pkg = dep.package_folder
                except Exception:
                    pkg = None
                if pkg:
                    for sub in ("lib", "lib64"):
                        cand = os.path.join(pkg, sub)
                        if os.path.isdir(cand) and cand not in search_dirs:
                            search_dirs.append(cand)
            for libdir in search_dirs:
                for pattern in ("libglib-2.0.so*", "libgobject-2.0.so*", "libgmodule-2.0.so*"):
                    for cand in sorted(glob.glob(os.path.join(libdir, pattern))):
                        try:
                            if os.path.isfile(cand) and cand not in preloads:
                                # Prefer the real versioned ELF file over the
                                # linker-script/.so stub when both exist.
                                if cand.endswith(".so"):
                                    continue
                                if not self._is_elf_shared(cand):
                                    continue
                                preloads.append(cand)
                        except OSError:
                            continue
                # Fallback: if only .so stubs exist, take them.
                if not preloads:
                    for pattern in ("libglib-2.0.so", "libgobject-2.0.so"):
                        cand = os.path.join(libdir, pattern)
                        try:
                            if os.path.isfile(cand) and cand not in preloads:
                                preloads.append(cand)
                        except OSError:
                            continue
                if preloads:
                    break
        except Exception:
            pass
        return [p for p in preloads if p and os.path.isfile(p) and self._is_elf_shared(p)]

    def _diagnose_link(self):
        # One-shot ground truth for the next round (info-level, few lines):
        # dep libdir contents (*.la left? shared intl present?), whether
        # the built libuser.so DEFINES g_libintl_* (whole-archive proof),
        # and NEEDED/RUNPATH of one test binary + libgobject.
        try:
            libdirs = self._dep_libdirs()
            for libdir in libdirs:
                try:
                    names = sorted(os.listdir(libdir))
                except OSError:
                    continue
                interesting = [n for n in names if n.endswith(".la") or "libintl" in n
                               or n.startswith(("libglib-2.0", "libgobject-2.0", "libgmodule-2.0"))]
                self.output.info("dep libdir %s: %s" % (libdir, ", ".join(interesting[:12]) or "(none)"))
        except Exception as exc:
            self.output.warning("dep libdir listing failed: %r" % (exc,))
        which = None
        for tool in ("llvm-nm", "nm"):
            try:
                from shutil import which as _which
                which = _which(tool)
            except Exception:
                which = None
            if which:
                break
        built = os.path.join(self.source_folder or "", "lib", ".libs", "libuser.so.1")
        if which and os.path.isfile(built):
            try:
                self.run("%s -D --defined-only \"%s\" | grep -c g_libintl || true" % (which, built),
                         cwd=self.source_folder, env="conanbuild")
            except Exception as exc:
                self.output.warning("nm intl probe failed: %r" % (exc,))
        reader = None
        for tool in ("llvm-readelf", "readelf"):
            try:
                from shutil import which as _which
                reader = _which(tool)
            except Exception:
                reader = None
            if reader:
                break
        if reader:
            probes = [os.path.join(self.source_folder or "", "tests", ".libs", "pwhash_test")]
            try:
                dep = self.dependencies.get("glib") if hasattr(self.dependencies, "get") else self.dependencies["glib"]
                pkg = dep.package_folder if dep is not None else None
            except Exception:
                pkg = None
            if pkg:
                probes.append(os.path.join(pkg, "lib", "libgobject-2.0.so"))
            for probe in probes:
                if os.path.isfile(probe):
                    try:
                        self.run("%s -d \"%s\" 2>&1 | grep -E 'NEEDED|RUNPATH|RPATH' || true" % (reader, probe),
                                 cwd=self.source_folder, env="conanbuild")
                    except Exception as exc:
                        self.output.warning("readelf probe failed for %s: %r" % (probe, exc))

    def _chmod_test_drivers(self):
        # Best-effort chmod +x for the automake TESTS shell/python
        # drivers (noexec/chmod-limited FS may refuse; then the
        # explicit PYTHON=... override below still lets `sh script`
        # invoke `python script.py` without the exec bit).
        for rel in ("tests/config_test.sh", "tests/fs_test",
                    "tests/files_test", "tests/pwhash_test",
                    "tests/utils_test", "tests/config_test.py",
                    "tests/fs_test.py", "tests/files_test.py",
                    "tests/pwhash.py"):
            path = os.path.join(self.source_folder, rel)
            try:
                if os.path.isfile(path):
                    os.chmod(path, 0o755)
            except OSError as exc:
                self.output.warning("chmod %s failed: %r" % (rel, exc))
                continue
        # One-shot ground truth for the next round: mode bits + shebang.
        try:
            for rel in ("tests/files_test.py", "tests/pwhash.py"):
                path = os.path.join(self.source_folder, rel)
                if os.path.isfile(path):
                    try:
                        st = os.stat(path)
                        mode = oct(st.st_mode & 0o777)
                    except OSError:
                        mode = "?"
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as h:
                            first = h.readline().strip()
                    except OSError:
                        first = "?"
                    self.output.info("test driver %s mode=%s shebang=%s" % (rel, mode, first[:120]))
        except OSError:
            pass

    def _run_upstream_checks(self):
        check_rc = 0
        check_detail = ""
        try:
            tmpdir = self._writable_tmpdir()
            shell = self._pick_shell()
            intl_snippet = self._intl_make_snippet()
            runtime_dirs = self._runtime_libdirs()
            preloads = self._check_preloads()
            ld_path = ":".join(runtime_dirs)
            ld_preload = ":".join(preloads)
            if ld_path:
                self.output.info("make check LD_LIBRARY_PATH=%s" % ld_path)
            if ld_preload:
                self.output.info("make check LD_PRELOAD=%s" % ld_preload)
            self._chmod_test_drivers()
            py_interp = self._pick_python()
            if py_interp:
                self.output.info("make check PYTHON=%s" % py_interp)
                # CI #91463: PYTHON must be a *make argument* (after
                # `make check`), not an env prefix before `make`: env
                # vars do not become make variables without -e, so
                # AM_TESTS_ENVIRONMENT's $(PYTHON) stayed empty and the
                # .py drivers (no shebang) were exec'd as shell.
                py_arg = " PYTHON=%s" % shlex.quote(py_interp)
            else:
                self.output.warning("no python3 interpreter found; TESTS python drivers will try direct exec")
                py_arg = ""
            runtime_prefix = ""
            if ld_path:
                runtime_prefix += "LD_LIBRARY_PATH=%s " % shlex.quote(ld_path)
            if ld_preload:
                runtime_prefix += "LD_PRELOAD=%s " % shlex.quote(ld_preload)
            self.run(
                "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
                "CONFIG_SHELL=\"%s\" SHELL=\"%s\" %smake check -j1%s%s"
                % (tmpdir, tmpdir, tmpdir, shell, shell, runtime_prefix, py_arg, intl_snippet),
                cwd=self.source_folder,
                env="conanbuild",
            )
        except Exception as exc:
            check_rc = 1
            check_detail = str(exc)
            self.output.warning("make check did not complete cleanly: %s" % check_detail[:2000])
        self._emit_upstream_marker(check_rc, check_detail)

    def _find_install_sh(self):
        # HMBS install shim (runtime/<task>/bin/install) accepts only
        # single-file two-arg calls and exits 64 (EX_USAGE) on automake
        # multi-file batches: install-man1 `install -c -m 644 a.1 b.1 ...
        # <destdir>` with 12 man pages is exactly that shape (single-file
        # .so installs just above it pass, the 12-file man batch fails).
        # Same family as lzop 1.04 dist_docDATA / cronolog install-man /
        # torsocks install-dist_docDATA / viennarna install-pkgincludeHEADERS
        # / cxxtools (all Error 64). Drive `make install` with the
        # automake-bundled install-sh (via /bin/sh) which parses the
        # multi-file batch correctly. Use /bin/sh literally (not
        # /system/bin/sh): old libtool only recognizes
        # `/bin/sh .../install-sh -c` as an install command (viennarna /
        # cracklib2 / cyrus-sasl precedent). Skip the placeholder
        # root install-sh this recipe creates for the libtoolize heuristic
        # (2 lines); prefer the real admin/install-sh autoreconf installs.
        candidates = []
        for rel in ("admin/install-sh", "install-sh"):
            cand = os.path.join(self.source_folder, rel)
            if os.path.isfile(cand):
                candidates.append(cand)
        try:
            for dirpath, _dirnames, filenames in os.walk(self.source_folder):
                if "install-sh" in filenames:
                    full = os.path.join(dirpath, "install-sh")
                    if full not in candidates:
                        candidates.append(full)
        except OSError:
            pass
        for cand in candidates:
            try:
                if os.path.getsize(cand) < 5000:
                    continue
                with open(cand, "r", encoding="utf-8", errors="replace") as handle:
                    head = handle.read(2000)
                if "install" not in head.lower():
                    continue
                return cand
            except OSError:
                continue
        return None

    def package(self):
        tmpdir = self._writable_tmpdir()
        shell = self._pick_shell()
        install_sh = self._find_install_sh()
        if install_sh:
            self.output.info("make install via bundled install-sh: %s" % install_sh)
            install_vars = (
                "MKDIR_P=\"/bin/sh %s -c -d\" "
                "INSTALL=\"/bin/sh %s -c\" "
                "INSTALL_PROGRAM=\"/bin/sh %s -c\" "
                "INSTALL_DATA=\"/bin/sh %s -c -m 644\""
                % (install_sh, install_sh, install_sh, install_sh)
            )
        else:
            self.output.warning("bundled install-sh not found; make install uses host install")
            install_vars = ""
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "CONFIG_SHELL=\"%s\" SHELL=\"%s\" "
            "make install DESTDIR=\"%s\" -j1 %s"
            % (tmpdir, tmpdir, tmpdir, shell, shell, self.package_folder, install_vars),
            cwd=self.source_folder,
            env="conanbuild",
        )
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    try:
                        os.remove(os.path.join(libdir, name))
                    except OSError:
                        pass
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        try:
            persisted_src = os.path.join(self.source_folder, "hmbs_upstream.json")
            if os.path.isfile(persisted_src):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json",
                     src=os.path.dirname(persisted_src), dst=res_dir)
        except Exception as exc:
            self.output.warning("persist upstream marker on package: %r" % (exc,))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libuser")
        self.cpp_info.set_property("cmake_target_name", "libuser::libuser")
        self.cpp_info.set_property("pkg_config_name", "libuser")
        self.cpp_info.libs = ["user"]
        # glib headers come through lib/user.h; popt is linked by the tools.
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gmodule-2.0",
            "popt::popt",
            # apps/* link -lpam -lpam_misc -lpamc unconditionally; every
            # direct requires must appear here (Conan 2 package_info gate).
            "linux-pam::pam",
            "linux-pam::pam_misc",
            "linux-pam::pamc",
            # Direct static requires closing the g_libintl_* loop (see
            # requirements()); same ref style as libpeas2/libsecret
            # ("proxy-libintl::proxy-libintl").
            "proxy-libintl::proxy-libintl",
        ]
        if str(self.settings.os) == "OHOS":
            # libuser.so embeds the static proxy-libintl archive at build
            # time, but its headers still expose glib's g_libintl_* remap to
            # CMakeDeps/PkgConfigDeps consumers (wv 1.2.9 pattern): keep the
            # consumer search path + -lintl so any remaining reference
            # resolves to the same proxy-libintl package.
            try:
                dep = self.dependencies.get("proxy-libintl") if hasattr(self.dependencies, "get") else self.dependencies["proxy-libintl"]
                pkg = dep.package_folder if dep is not None else None
            except Exception:
                pkg = None
            if pkg:
                intl_libdir = os.path.join(pkg, "lib")
                if os.path.isdir(intl_libdir):
                    self.cpp_info.system_libs = list(getattr(self.cpp_info, "system_libs", []) or []) + ["intl"]
                    self.cpp_info.sharedlinkflags = list(getattr(self.cpp_info, "sharedlinkflags", []) or []) + ["-L%s" % intl_libdir]
                    self.cpp_info.exelinkflags = list(getattr(self.cpp_info, "exelinkflags", []) or []) + ["-L%s" % intl_libdir]
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
