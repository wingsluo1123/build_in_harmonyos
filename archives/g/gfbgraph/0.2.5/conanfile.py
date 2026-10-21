#!/usr/bin/env python3
"""Conan recipe — gfbgraph 0.2.5 (autotools).

GFBGraph is a GLib/GObject wrapper for the Facebook Graph API that
integrates with GNOME Online Accounts.

OHOS adaptation notes:
  - Build system: autotools (tarball ships configure, no autoreconf needed).
  - Upstream 0.2.5 targets rest-0.7 + libsoup-2.4 (soup-request unstable API),
    neither of which is published in the OHOS registry (librest/0.10.2 is the
    rest-1.0/libsoup3 generation; soup2 and soup3 cannot coexist in one
    process). Ported to rest-1.0 + libsoup-3.0 in-code via
    _port_to_soup3_rest1() (generated configure + configure.ac,
    .pc.in, GIR includes, SoupURI->GUri, SoupRequester->SoupSession send;
    no unified-diff patch file, so no hunk-offset fragility).
  - GOA backend excised (see _excise_goa_backend): upstream links
    GFBGraphGoaAuthorizer against goa-1.0, whose only OHOS provider
    (libgoa/3.58.1) pins glib/2.88.3 while the rest of this closure unifies
    on glib/2.84.0.1.1, so it can only ever source-build; its meson recipe
    hard-codes a profile compiler path invisible in the preflight sandbox.
    OHOS runs no goa-daemon, so the online-accounts authorizer cannot function
    at runtime here; the simple authorizer (offline token) is unaffected and
    is what the consumer test exercises. No upstream test program covers the
    GoaAuthorizer (TESTS = gtestutils + autoptr only).
  - Introspection and gtk-doc disabled (no g-ir-scanner on OHOS workers).
  - Upstream tests/ holds 2 programs (gtestutils, autoptr). Network cases in
    gtestutils are disabled upstream (#if 0, needs Facebook credentials), so
    make check runs green without network: gtestutils exits 0 with 0 cases,
    autoptr runs 4 GObject cases.
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
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


UPSTREAM_TEST_TOTAL = 2


class GfbgraphConan(ConanFile):
    name = "gfbgraph"
    version = "0.2.5"
    description = "GLib/GObject wrapper for the Facebook Graph API"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgfbgraph"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Unify glib across the closure: json-glib/1.10.6.1 pins glib/2.84.0.1
        # while librest/libsoup3 pin glib/2.84.0.1.1 (and goa pins its own
        # generation). Without override conan aborts with "Version conflict:
        # Conflict between glib/2.84.0.1 and glib/2.84.0.1.1 ... originates
        # from json-glib/1.10.6.1". Root override selects the published
        # 2.84.0.1.1 shared generation (gtk4-chain aligned, same as
        # gnome-recipes/libadwaita/zathura precedents); newer patch over older
        # pin is ABI-compatible within the 2.84 generation. force=True follows
        # the librest/0.10.2 precedent so the root unification stays stable in
        # platform graph resolution instead of drifting per-node.
        self.requires("glib/2.84.0.1.1", options={"shared": True},
                      transitive_headers=True, transitive_libs=True,
                      override=True, force=True)
        # librest/0.10.2 pins json-glib/1.10.6 while this recipe tracks 1.10.6.1
        # (ohpcd-published, gnome-recipes same-generation pin); root override
        # unifies upward to the newer patch.
        self.requires("json-glib/1.10.6.1", transitive_headers=True, transitive_libs=True,
                      override=True)
        self.requires("librest/0.10.2", transitive_headers=True, transitive_libs=True)
        # Pin the same r3 recipe revision librest/0.10.2 anchors
        # (3bbc75da3c320deddf009771ec0406f9) so this graph cannot resolve a
        # drifted RREV of the same version next to librest's pinned one.
        self.requires("libsoup3/3.6.5-r3#3bbc75da3c320deddf009771ec0406f9",
                      transitive_headers=True, transitive_libs=True)
        # NOTE: no goa provider on purpose. Upstream's GFBGraphGoaAuthorizer
        # needs goa-1.0; the only OHOS recipe (libgoa/3.58.1) pins glib/2.88.3
        # against this closure's unified glib/2.84.0.1.1, forcing a sandbox
        # source build whose meson hard-codes an invisible profile compiler
        # path (preflight Errno 2, twice). _excise_goa_backend() below drops
        # the authorizer from the build instead of dragging that leg along.
        # Steer librest's libxml2/2.15.3 (bare version exists on BOTH remotes;
        # preflight checks conancenter first, so the conancenter CMake recipe
        # wins and drags tool-require cmake/4.4.4 into an OHOS source build)
        # to the ohpcd-only 2.15.3.1 patch release (same API, bare-cmake build
        # with no tool_requires, has OHOS binary). Directly addresses the
        # failing-log evidence: "libxml2/2.15.3: Downloaded recipe revision
        # ... from conancenter" followed by "cmake/4.4.4 ... KeyError: 'OHOS'".
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True,
                      override=True)
        # CCI-shadow guard for glib's libffi/3.4.4 (2026-10-16 preflight
        # compile failure): bare 3.4.4 exists on BOTH remotes and preflight
        # resolves conancenter first (log applies the CCI-only patch
        # 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the in-repo
        # recipe), whose configure dies with
        # "configure[139]: /data/service/hnp/bin/bash: inaccessible or not
        # found" (Error 127) because the profile's CONFIG_SHELL/SHELL path
        # is missing on that runner. Pin the ohpcd-published RREV of the
        # hardened in-repo recipe (same value xwrited/3 validated
        # end-to-end for the identical fingerprint). Same version, so glib's
        # package_id is untouched (a 3.5.2 swap would force a glib rebuild).
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
                      override=True)
        # CCI-shadow guard for libsoup3's sqlite3/3.49.1 (2026-10-16 preflight
        # compile failure): bare 3.49.1 exists on BOTH remotes (ohpcd manual
        # amalgamation recipe + conancenter CMake recipe) and preflight checks
        # conancenter first, so the conancenter CMake recipe wins and dies in
        # build() with "System is unknown to cmake ... CMAKE_C_COMPILER:
        # /data/service/hnp/bin/clang ... Configuring incomplete" (no OHOS
        # platform support + read-only /tmp compiler-test files). Pin the
        # ohpcd-published RREV of the hardened in-repo recipe (direct clang
        # amalgamation build, HMDFS-safe; same value bzrtp/5.3.105 and
        # kyua/0.13 validated end-to-end for the identical fingerprint).
        # Same version, so libsoup3's package_id is untouched.
        self.requires("sqlite3/3.49.1#669361066cc2c76e0ed897e6b6a27e38",
                      override=True)

    def build_requirements(self):
        # configure uses PKG_CHECK_MODULES(LIBGFBGRAPH/SOUP): needs a
        # pkg-config binary on PATH. HMBS preflight only injects
        # cmake/make/ninja/python3, no system pkg-config (2026-10-16
        # configure dies with "The pkg-config script could not be found").
        # Same precedent as ctpl/0.3.5, zurl/1.12.0, ekg2/0.3.1:
        # pkgconf/3.0.5 via build context; AutotoolsToolchain forwards
        # PKG_CONFIG and conanbuild PATH exposes the binary.
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gfbgraph requires Linux or OHOS, got %s" % self.settings.os)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generation-gap guard (gnome-recipes/2.0.4 precedent): librest/0.10.2
        # declares bare glib component refs ("glib::glib") authored against
        # glib/2.88.3, while the unified glib/2.84.0.1.1 spells components
        # suffixed ("glib-2.0", ...). PkgConfigDeps resolves cpp_info.requires
        # verbatim and aborts with "Component 'glib::glib' not found in 'glib'
        # package requirement". Normalize before generating; no-op when names
        # already match.
        self._normalize_glib_component_refs()
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-introspection")
        tc.configure_args.append("--disable-gtk-doc")
        tc.generate()

    def build(self):
        self._port_to_soup3_rest1()
        self._patch_config_guess()
        # Drop the GOA authorizer from the unpacked tree before configuring
        # (no autoreconf on workers, so generated files are edited in place).
        self._excise_goa_backend()
        # Sandbox compiler fallback (mailx/8.1.2 precedent, HMBS experience 1):
        # the profile hard-codes the CI worker layout (/data/service/hnp/bin/...)
        # which is not visible inside the preflight sandbox (meson dies with
        # "Unknown compiler(s): [['/data/service/hnp/bin/clang']]" / Errno 2).
        # Resolve via PATH instead; no-op on CI where the path exists.
        cc = self._resolve_cc()
        # E236 la-free link dir (ezstream/1.0.2 precedent) + E522 closure
        # lesson: published autotools archives in this closure ship .la
        # files with a stale build-time prefix (libdir='//lib',
        # dependency_libs with '//lib/*.la' from --prefix=/ builds).
        # Libtool gives a visible .la precedence over the sibling .so on
        # the -L search path, so the gfbgraph/tests links die with
        # "'//lib/libpcre2-8.la' is not a valid libtool archive" (this
        # round's log: libffi.la/pcre2-8.la "was moved" then
        # "'//lib/libpcre2-8.la' ... Error 1" in tests/gtestutils).
        # The previous shadow-.la revision failed in preflight: libtool
        # recursively opens transitive .la files via absolute paths in
        # dependency_libs, bypassing any -L search order, so a sanitized
        # shadow is never consulted when its parent is reached by absolute
        # path (E522 root cause). Fix: (1) la-free holds ONLY .so*/.a
        # copies (no .la, so no shadow can be parsed); (2)
        # _neutralize_poisoned_la() renames every dependency *.la to
        # *.la.hmbs-bak inside the task-local preflight conan-home, so
        # libtool finds no .la anywhere and links the .so directly via
        # the pkg-config -L/-l closure (already complete on our link
        # lines). Cache mutation is task-local: preflight uses a
        # per-client conan-home (log: preflight/clients/<id>/conan-home).
        self._prepare_la_free_dir()
        self._neutralize_poisoned_la()
        # Sandbox shell fallback (ballandpaddle/0.8.1 precedent): the profile
        # exports CONFIG_SHELL=/data/service/hnp/bin/bash, which exists on
        # CI workers but not in the preflight sandbox (configure dies with
        # "configure[159]: /data/service/hnp/bin/bash: inaccessible or not
        # found", Error 127). Root cause (verified against the 0.2.5
        # tarball): configure lines 139-154 re-exec via
        # `exec $CONFIG_SHELL ...` BEFORE parsing any VAR=VALUE configure
        # arguments, so passing CONFIG_SHELL=/bin/sh as a configure *arg*
        # (previous cycle, still Error 127 with identical line 159) can never
        # fix the first exec -- only the *process environment* matters.
        # Hence this cycle drops the Autotools-helper route entirely and uses
        # self.run() with shell-prefix env assignments (CONFIG_SHELL/SHELL
        # as process env, not configure args) plus the autoconf kill-switch
        # _as_can_reexec=no and an explicit `/bin/sh configure` interpreter
        # (no exec-bit needed, HMBS chmod=0 safe). No-op on CI where the
        # profile path exists and /bin/sh is the same shell.
        # NOTE: CC stays a configure/make command-line assignment (autoconf
        # VAR=VALUE overrides env; make cmdline overrides baked-in Makefile
        # CC) so it wins over the toolchain-exported dead absolute path.
        # GOA_CFLAGS/GOA_LIBS use the pkg.m4 short-circuit (both non-empty
        # skips the goa-1.0 probe); a single space adds no effective flag.
        env_prefix = self._shell_env_prefix()
        # HMBS platform diagnosis [unsafe_local_mktemp]: relax umask in the
        # shipped configure before running it (buildtorrent/zurl precedent),
        # so the `(umask 077 && mktemp -d)` tmpdir stays writable on HMFS.
        # Idempotent; no-op when the pattern is absent (e.g. healthy CI).
        self._patch_autoconf_umask(os.path.join(self.source_folder, "configure"))
        # Maintainer-mode guard (juise/3.0.0 precedent): _port/_excise edit
        # configure.ac + Makefile.am in place without autoreconf, which bumps
        # their mtimes past the shipped aclocal.m4/configure/Makefile.in, so
        # make fires the maintainer rules via `missing aclocal-1.16` (this
        # round's Error 127; no aclocal/perl on device). Pin template mtimes
        # back to their generated counterparts (equal mtimes do not trigger
        # make); generated files stay newest. No test is skipped.
        self._stabilize_autotools_mtimes()
        # Configure-phase-only mktemp shim: when HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, fail "./conf*" mktemp calls so
        # Autoconf takes its mkdir fallback (which the umask fix above keeps
        # writable). Scoped to configure only per the platform diagnosis.
        _tmp_for_shim = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(_tmp_for_shim, exist_ok=True)
        except OSError:
            pass
        _shim_dir = self._mktemp_fallback_shim_for_ohos(_tmp_for_shim)
        _configure_prefix = env_prefix
        if _shim_dir:
            _configure_prefix = "PATH=%s:$PATH %s" % (shlex.quote(_shim_dir), env_prefix)
        if self.options.shared:
            shr_args = ["--enable-shared", "--disable-static"]
        else:
            shr_args = ["--enable-static", "--disable-shared"]
        # --libdir uses absolute /lib (not ${prefix}/lib): with --prefix=/
        # the ${prefix} form expands to //lib, which libtool bakes into
        # libgfbgraph.la as libdir='//lib' (same poison as the deps).
        cfg_args = ["--prefix=/", "--bindir=/bin",
                    "--sbindir=/bin", "--libdir=/lib",
                    "--includedir=/include",
                    "--oldincludedir=/include"] + shr_args + [
            "--disable-introspection", "--disable-gtk-doc",
            # Belt-and-braces with _stabilize_autotools_mtimes(): when the
            # package uses AM_MAINTAINER_MODE this turns the aclocal/automake
            # rebuild rules off entirely; when it does not, configure prints
            # one harmless "unrecognized options" warning and continues.
            "--disable-maintainer-mode",
            "CC=%s" % cc, "GOA_CFLAGS= ", "GOA_LIBS= ",
        ]
        # Native triplet bypass (buildtorrent/0.9.1 + ballandpaddle/0.8.1
        # precedent): the 0.2.5 config.sub predates HarmonyOS, so without an
        # explicit triplet configure leans on the patched config.guess. The
        # explicit gnu triplet keeps build==host native (the real OHOS target
        # still comes from the forwarded toolchain CFLAGS --target/--sysroot
        # above, not from the triplet) and lets the fallback host clang pass
        # the conftest without an OS-name rejection.
        if self.settings.get_safe("os") == "OHOS":
            cfg_args += ["--build=aarch64-unknown-linux-gnu",
                         "--host=aarch64-unknown-linux-gnu"]
            self.output.info("using gnu triplet bypass for OHOS configure")
        configure = os.path.join(self.source_folder, "configure")
        self.output.info("Using shell: /bin/sh (CONFIG_SHELL/SHELL re-exec guard)")
        try:
            self.run("umask 022 && %s /bin/sh %s %s" % (
                _configure_prefix, shlex.quote(configure),
                " ".join(shlex.quote(a) for a in cfg_args)),
                cwd=self.build_folder, env="conanbuild")
        except Exception:
            self._dump_configure_evidence(cc)
            raise
        # Generated config.status embeds its own hardcoded `umask 077` copy;
        # relax it as well so later `make` re-invocations of config.status
        # stay writable on HMFS (cxxtools/zurl precedent).
        self._patch_autoconf_umask(os.path.join(self.build_folder, "config.status"))
        # R9/DRAFT-11327: force serial make; parallel forks hit
        # "tar (child): Cannot fork: Out of memory" on constrained workers.
        # V=1 keeps the full libtool/shell command in the log so a future
        # `/bin/sh: no closing quote` points at the exact command, not a
        # hidden silent-rules line.
        self.run("umask 022 && %s make -j1 V=1 %s" % (env_prefix, shlex.quote("CC=%s" % cc)),
                 cwd=self.build_folder, env="conanbuild")
        self._run_upstream_tests(cc)

    def _shell_env_prefix(self, with_loader_path=False):
        # Process-environment prefix for self.run() calls. LD_LIBRARY_PATH
        # is OFF by default and only enabled for test execution (see
        # _run_upstream_tests, which passes it via TESTS_ENVIRONMENT):
        # exporting the dep-graph libdirs during configure/make hijacks the
        # OHOS SDK lld's own libxml2.so.16 with conan's incompatible
        # libxml2 (this round: lld dies with xmlFreeDoc/xmlReadMemory/...
        # "symbol not found" -> "C compiler cannot create executables"),
        # so link-phase processes must keep a clean loader path.
        # Assignments precede the command
        # so the shell exports them before configure starts -- this is what
        # the configure-arg route could not do (args parse after re-exec).
        # _as_can_reexec=no is the documented autoconf kill-switch for the
        # line 139-154 `exec $CONFIG_SHELL` block: with it, configure never
        # execs any shell at all. TMPDIR/TMP/TEMP isolate to the build
        # folder (HMBS per-task tmp discipline).
        # PKG_CONFIG: this recipe bypasses the Autotools helper (shell-guard
        # route), so the toolchain-forwarded PKG_CONFIG may not reach the
        # manual self.run() process env. Resolve the pkgconf build-require
        # binary explicitly (best-effort; falls back to PATH lookup at run
        # time when the build-dep folder is not yet visible).
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        parts = [
            "CONFIG_SHELL=/bin/sh",
            "SHELL=/bin/sh",
            "_as_can_reexec=no",
            "TMPDIR=%s" % shlex.quote(tmp),
            "TMP=%s" % shlex.quote(tmp),
            "TEMP=%s" % shlex.quote(tmp),
        ]
        pkg_config = self._resolve_pkg_config()
        if pkg_config:
            parts.append("PKG_CONFIG=%s" % shlex.quote(pkg_config))
        # Test-execution loader path (xauth/ezstream in-tree check loader
        # lesson): automake parallel-tests executes freshly linked test
        # binaries inside the build tree, but their shared deps live only
        # in the conan cache, so without the dep-graph libdirs the loader
        # kills both test programs before main() -> automake FAIL:2.
        # Scoped to test execution ONLY via TESTS_ENVIRONMENT (see
        # _run_upstream_tests), never exported globally here: a global
        # LD_LIBRARY_PATH also redirects the OHOS SDK lld's own
        # libxml2.so.16 to conan's incompatible copy (xmlFreeDoc/...
        # symbol-not-found -> conftest "cannot create executables").
        if not with_loader_path:
            _libdirs = []
        else:
            try:
                _libdirs = self._dependency_libdirs()
            except Exception:
                _libdirs = []
        if _libdirs:
            _prior_ld = os.environ.get("LD_LIBRARY_PATH", "")
            _joined = os.pathsep.join(_libdirs + ([_prior_ld] if _prior_ld else []))
            parts.append("LD_LIBRARY_PATH=%s" % shlex.quote(_joined))
            self.output.info("Using LD_LIBRARY_PATH with %d dep libdir(s)" % len(_libdirs))
        # E236 la-free -L first: when the build la-free dir exists,
        # prepend it to LDFLAGS while preserving the incoming conanbuild
        # LDFLAGS via shell expansion. The dir holds only .so*/.a
        # copies (no .la by design) and dependency *.la files are
        # neutralized to *.hmbs-bak (see _neutralize_poisoned_la), so
        # libtool finds the clean shared archives first and never parses
        # a poisoned '//lib' .la. No-op when la-free is absent (e.g.
        # package() on CI without it).
        try:
            _la_free = os.path.join(self.build_folder, "la-free")
        except Exception:
            _la_free = ""
        try:
            _has_la_free = bool(_la_free) and os.path.isdir(_la_free)
        except Exception:
            _has_la_free = False
        if _has_la_free:
            _esc = _la_free.replace("\\", "\\\\").replace('"', '\\"').replace(
                "$", "\\$").replace("`", "\\`")
            parts.append('LDFLAGS="-L%s $LDFLAGS"' % _esc)
        # Manual-route toolchain flag forwarding (this round's
        # "C compiler cannot create executables" fix): this recipe bypasses
        # the Autotools helper (CONFIG_SHELL re-exec guard, see build()),
        # so conanautotoolchain.sh is never sourced and a bare
        # `CC=<fallback>` reaches configure without the profile sysroot /
        # --target flags. Forward the toolchain-computed CFLAGS/CPPFLAGS /
        # CXXFLAGS explicitly as process-env prefix assignments (same shell
        # discipline as above, no inner-double-quote configure_args, so no
        # ufiformat quote-leak). Replaces (not appends) the conanbuild
        # value for this command only; identical value on healthy CI is a
        # harmless no-op.
        try:
            _tc_flags = self._toolchain_flags_prefix()
        except Exception as exc:
            self.output.warning("toolchain flag forward skipped: %s" % exc)
            _tc_flags = ""
        if _tc_flags:
            parts.append(_tc_flags)
        return " ".join(parts)

    def _toolchain_flags_prefix(self):
        # Compute AutotoolsToolchain flags fresh (same inputs as generate())
        # and render them as shell-prefix assignments. Only plain flags are
        # forwarded (R33: never CC/CXX here, CC stays a configure/make
        # command-line override so the sandbox fallback wins).
        tc = AutotoolsToolchain(self)
        rendered = []
        try:
            cflags = " ".join(list(getattr(tc, "cflags", []) or []))
        except Exception:
            cflags = ""
        try:
            cxxflags = " ".join(list(getattr(tc, "cxxflags", []) or []))
        except Exception:
            cxxflags = ""
        try:
            ldflags = " ".join(list(getattr(tc, "ldflags", []) or []))
        except Exception:
            ldflags = ""
        try:
            defines = list(getattr(tc, "defines", []) or [])
        except Exception:
            defines = []
        cppflags = " ".join("-D%s" % d for d in defines if d)
        if cflags:
            rendered.append("CFLAGS=%s" % shlex.quote(cflags))
            self.output.info("forwarding toolchain CFLAGS (%d chars)" % len(cflags))
        else:
            self.output.warning("toolchain CFLAGS empty, configure probe may lack sysroot")
        if cxxflags:
            rendered.append("CXXFLAGS=%s" % shlex.quote(cxxflags))
        if cppflags:
            rendered.append("CPPFLAGS=%s" % shlex.quote(cppflags))
        if ldflags:
            # Preserve the incoming conanbuild LDFLAGS (which already carries
            # the la-free -L prepend from this prefix) via shell expansion.
            _esc_ld = ldflags.replace("\\", "\\\\").replace('"', '\\"').replace(
                "$", "\\$").replace("`", "\\`")
            rendered.append('LDFLAGS="%s $LDFLAGS"' % _esc_ld)
            self.output.info("forwarding toolchain LDFLAGS (%d chars)" % len(ldflags))
        return " ".join(rendered)

    def _dependency_libdirs(self):
        # Whole dep-graph libdirs for the LD_LIBRARY_PATH above (xauth
        # lesson: link-line libs are not enough, loader follows recursive
        # DT_NEEDED into run-only deps).
        result = []
        try:
            items = list(self.dependencies.items())
        except Exception:
            return result
        for _name, dep in items:
            try:
                cpp = dep.cpp_info
                agg = cpp.aggregated_components() if hasattr(
                    cpp, "aggregated_components") else cpp
                libdirs = list(getattr(agg, "libdirs", []) or [])
            except Exception:
                continue
            for d in libdirs:
                if d and d not in result:
                    result.append(d)
        return result

    def _resolve_pkg_config(self):
        # Prefer the pkgconf build-require binary (absolute path, immune to
        # PATH ordering); the pkgconf recipe ships `pkgconf` and usually a
        # `pkg-config` symlink, accept either. PATH fallback covers CI
        # workers with a system pkg-config. Returns None when nothing is
        # found so the caller simply omits the assignment.
        candidates = []
        try:
            build_deps = self.dependencies.build
        except Exception:
            build_deps = None
        if build_deps is not None:
            try:
                pkgconf = build_deps["pkgconf"]
                folder = getattr(pkgconf, "package_folder", None)
            except Exception:
                folder = None
            if folder:
                for name in ("pkg-config", "pkgconf"):
                    for sub in ("bin", ""):
                        cand = os.path.join(folder, sub, name) if sub else os.path.join(folder, name)
                        candidates.append(cand)
        for cand in candidates:
            try:
                if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                    self.output.info("Using PKG_CONFIG: %s" % cand)
                    return cand
            except Exception:
                continue
        for name in ("pkg-config", "pkgconf"):
            found = shutil.which(name)
            if found:
                self.output.info("Using PKG_CONFIG: %s" % found)
                return found
        self.output.warning("PKG_CONFIG binary not found (pkgconf tool-require missing?)")
        return None

    def _resolve_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = (compilers.get("c") or "clang").strip()
        if not os.path.isfile(cc):
            resolved = (
                shutil.which(os.path.basename(cc))
                or shutil.which("clang")
                or shutil.which("cc")
                or cc
            )
            if resolved != cc:
                self.output.warning(
                    "configured C compiler '%s' not found, "
                    "falling back to PATH lookup: %s" % (cc, resolved)
                )
            cc = resolved
        self.output.info("Using C compiler: %s" % cc)
        return cc

    def _dump_configure_evidence(self, cc):
        # zurl#31 precedent: configure conftest failure without config.log
        # is undiagnosable from the tail alone. Dump the compiler probe,
        # effective flags, and the config.log compiler section + tail so the
        # next round can distinguish missing-compiler / missing-flags /
        # toolchain-broken without guessing. Success path untouched.
        try:
            self.output.info("CONFIGURE-EVIDENCE CC=%s" % cc)
        except Exception:
            pass
        try:
            import subprocess
            prob = subprocess.run([cc, "--version"], capture_output=True,
                                  text=True, timeout=60)
            out = (prob.stdout + prob.stderr).strip().splitlines()
            self.output.info("CONFIGURE-EVIDENCE cc --version rc=%d: %s"
                             % (prob.returncode, (out[0][:300] if out else "<empty>")))
        except Exception as exc:
            self.output.info("CONFIGURE-EVIDENCE cc --version failed: %s" % exc)
        for var in ("CFLAGS", "CPPFLAGS", "CXXFLAGS", "LDFLAGS"):
            try:
                val = os.environ.get(var, "<unset>")
                self.output.info("CONFIGURE-EVIDENCE env %s=%s" % (var, str(val)[:500]))
            except Exception:
                pass
        try:
            log = os.path.join(self.build_folder, "config.log")
            if not os.path.isfile(log):
                self.output.info("CONFIGURE-EVIDENCE config.log absent at %s" % log)
                return
            with open(log, encoding="utf-8", errors="replace") as handle:
                text = handle.read().splitlines()
            self.output.info("CONFIGURE-EVIDENCE config.log (%d lines)" % len(text))
            started = None
            for i, ln in enumerate(text):
                if "checking whether the C compiler works" in ln:
                    started = i
                    break
            if started is not None:
                for ln in text[max(0, started - 5):started + 40]:
                    self.output.info("CONFIGURE-EVIDENCE config.log: %s" % ln[:500])
            else:
                for ln in text[:30]:
                    self.output.info("CONFIGURE-EVIDENCE config.log head: %s" % ln[:500])
            if len(text) > 40:
                self.output.info("CONFIGURE-EVIDENCE config.log tail:")
                for ln in text[-40:]:
                    self.output.info("CONFIGURE-EVIDENCE config.log: %s" % ln[:500])
        except Exception as exc:
            self.output.warning("configure evidence dump skipped: %s" % exc)

    def _prepare_la_free_dir(self):
        # E236 scoped la-free dir, NO .la shadows (E522 lesson applied):
        # copy only linkable archives (.so*, .a, flattened, no symlink
        # capability needed) into a build-private dir prepended via
        # LDFLAGS (see _shell_env_prefix). No .la is copied on purpose:
        # libtool scans every -L dir for lib<name>.la AND follows
        # absolute .la paths inside dependency_libs, so a sanitized
        # shadow can never reliably hide a poisoned cache .la (this
        # round's shadow-.la revision still died on the cache original
        # '//lib/libpcre2-8.la'). Cache .la files themselves are
        # neutralized separately by _neutralize_poisoned_la(), so with
        # no .la left visible anywhere libtool links the .so directly.
        # Best-effort: copy errors warn only; the LDFLAGS prepend in
        # _shell_env_prefix is a no-op when the dir is absent.
        try:
            dest = os.path.join(self.build_folder, "la-free")
        except Exception:
            return ""
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as exc:
            self.output.warning("la-free mkdir skipped: %s" % exc)
            return ""
        try:
            items = list(self.dependencies.items())
        except Exception as exc:
            self.output.warning("la-free dep walk skipped: %s" % exc)
            return dest
        copied = 0
        for _name, dep in items:
            try:
                cpp = dep.cpp_info
                agg = cpp.aggregated_components() if hasattr(
                    cpp, "aggregated_components") else cpp
                libdirs = list(getattr(agg, "libdirs", []) or [])
            except Exception:
                continue
            for d in libdirs:
                if not d or not os.path.isdir(d):
                    continue
                try:
                    names = os.listdir(d)
                except OSError:
                    continue
                for fn in names:
                    if not (fn.endswith(".so") or ".so." in fn
                            or fn.endswith(".a")):
                        continue
                    src = os.path.join(d, fn)
                    dst = os.path.join(dest, fn)
                    if os.path.exists(dst):
                        continue
                    try:
                        if os.path.islink(src):
                            real = os.path.realpath(src)
                            if not os.path.isfile(real):
                                continue
                            shutil.copy2(real, dst)
                        elif os.path.isfile(src):
                            shutil.copy2(src, dst)
                        else:
                            continue
                    except OSError as exc:
                        self.output.warning(
                            "la-free copy skipped %s: %s" % (src, exc))
                        continue
                    copied += 1
        self.output.info(
            "la-free dir prepared: %s (%d file(s), no .la by design)"
            % (dest, copied))
        return dest

    def _neutralize_poisoned_la(self):
        # E236/E522 cache neutralization (task-local): rename every
        # dependency *.la to *.la.hmbs-bak so libtool finds no .la
        # metadata anywhere and links the sibling .so directly via the
        # pkg-config -L/-l closure. Needed because libtool follows
        # absolute .la paths inside dependency_libs (E522), bypassing
        # -L order, and the published archives bake libdir='//lib' /
        # '//lib/*.la' (prefix=/ builds) -- this round's
        # tests/gtestutils died on exactly that ('//lib/libpcre2-8.la'
        # is not a valid libtool archive after libffi.la/pcre2 .la
        # "was moved" warnings). Scope is strictly the task-local
        # preflight conan-home (per-client dir); the recipe source and
        # this build's own fresh libgfbgraph.la are untouched. The .pc
        # Libs closures already carry the full transitive -l set (see
        # the failing link line: -lrest-1.0 -lsoup-3.0 ... -lpcre2-8),
        # so no transitive entry is lost when .la expansion is skipped.
        # Idempotent: existing *.hmbs-bak backups are kept as-is.
        # Best-effort: walk errors warn only.
        try:
            items = list(self.dependencies.items())
        except Exception as exc:
            self.output.warning("la neutralize dep walk skipped: %s" % exc)
            return 0
        renamed = 0
        seen = set()
        for _name, dep in items:
            try:
                cpp = dep.cpp_info
                agg = cpp.aggregated_components() if hasattr(
                    cpp, "aggregated_components") else cpp
                libdirs = list(getattr(agg, "libdirs", []) or [])
            except Exception:
                continue
            for d in libdirs:
                if not d or not os.path.isdir(d) or d in seen:
                    continue
                seen.add(d)
                try:
                    names = os.listdir(d)
                except OSError:
                    continue
                for fn in names:
                    if not fn.endswith(".la"):
                        continue
                    src = os.path.join(d, fn)
                    dst = src + ".hmbs-bak"
                    if os.path.exists(dst):
                        continue
                    try:
                        os.rename(src, dst)
                        renamed += 1
                    except OSError as exc:
                        self.output.warning(
                            "la neutralize skipped %s: %s" % (src, exc))
        self.output.info(
            "la neutralize: %d .la file(s) renamed to *.hmbs-bak "
            "(task-local conan-home)" % renamed)
        return renamed

    def _normalize_glib_component_refs(self):
        try:
            glib_comps = set(self.dependencies["glib"].cpp_info.components.keys())
        except Exception:
            return
        if not glib_comps:
            return

        def fix(ref):
            pkg, sep, comp = ref.partition("::")
            if not sep or pkg != "glib" or not comp:
                return ref
            if comp in glib_comps:
                return ref
            suffixed = comp + "-2.0"
            if suffixed in glib_comps:
                return pkg + "::" + suffixed
            if comp.endswith("-2.0") and comp[:-len("-2.0")] in glib_comps:
                return pkg + "::" + comp[:-len("-2.0")]
            return ref

        for _name, dep in self.dependencies.items():
            try:
                cpp = dep.cpp_info
            except Exception:
                continue
            try:
                if getattr(cpp, "requires", None):
                    fixed = [fix(r) for r in cpp.requires]
                    if fixed != list(cpp.requires):
                        cpp.requires = fixed
                        self.output.info("normalized root cpp_info.requires for %s" % _name)
                for comp in getattr(cpp, "components", {}).values():
                    if getattr(comp, "requires", None):
                        fixed = [fix(r) for r in comp.requires]
                        if fixed != list(comp.requires):
                            comp.requires = fixed
                            self.output.info("normalized component requires for %s" % _name)
            except Exception as exc:
                self.output.warning("glib component ref normalize skipped for %s: %s"
                                    % (_name, exc))

    @staticmethod
    def _is_make_recipe(line):
        # TAB-led commands, including automake `@COND@`-prefixed conditionals.
        if line.startswith("\t"):
            return True
        return re.match(r"^(@[^@\s]+@)+\t", line) is not None

    @staticmethod
    def _is_make_target(line):
        # `target: prereq` is always emitted at column 0 by automake, while
        # assignments carry `=` before any `:`.
        if line.startswith(("\t", " ", "#", "@")):
            return False
        if ":" not in line:
            return False
        eq = line.find("=")
        return eq == -1 or line.find(":") < eq

    @staticmethod
    def _odd_quote_logicals(lines):
        # Join backslash continuations, strip make `#` comments, and report
        # logical lines holding an odd number of single quotes.
        logicals = []
        buf = ""
        for line in lines:
            stripped = line.rstrip("\r\n")
            if stripped.endswith("\\") and not stripped.endswith("\\\\"):
                buf += stripped[:-1]
                continue
            buf += stripped
            logicals.append(buf)
            buf = ""
        if buf:
            logicals.append(buf)
        odd = []
        for idx, logical in enumerate(logicals):
            code = logical.split("#", 1)[0]
            if code.count("'") % 2:
                odd.append((idx, code[:200]))
        return odd

    def _drop_make_tokens(self, path, needle, strict):
        # Quote-parity-safe excision (cvsgraph lesson: a bare
        # ``\\S*needle\\S*`` regex can swallow one half of a shell-quoted span
        # and surface later as ``/bin/sh: no closing quote`` inside an
        # unrelated compile rule). Comment lines, recipe lines and whole
        # `target:` blocks holding needle are dropped outright; anywhere else
        # only whitespace-delimited tokens with even quote parity are removed,
        # and a line whose parity would break is dropped instead of repaired.
        # A fail-loud audit aborts on newly introduced odd-quote logical
        # lines (continuations joined) with the exact text, instead of a
        # blind shell error on the device.
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        raw_lines = text.splitlines(keepends=True)
        before = {content for _, content in self._odd_quote_logicals(raw_lines)}
        out = []
        removed = 0
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            if needle not in line:
                out.append(line)
                i += 1
                continue
            if line.lstrip(" \t").startswith("#"):
                removed += 1
                i += 1
                continue
            if self._is_make_recipe(line):
                removed += 1
                i += 1
                continue
            if self._is_make_target(line):
                removed += 1
                i += 1
                while i < len(raw_lines) and self._is_make_recipe(raw_lines[i]):
                    removed += 1
                    i += 1
                continue
            unsafe = any(
                tok.count("'") % 2 or tok.count('"') % 2
                for tok in re.findall(r"\S+", line)
                if needle in tok
            )
            if unsafe:
                removed += 1
                i += 1
                continue
            new_line = re.sub(
                r"\S*" + re.escape(needle) + r"\S*", "", line)
            code = new_line.split("#", 1)[0]
            if code.count("'") % 2:
                removed += 1
                i += 1
                continue
            bare = new_line.strip(" \t\r\n")
            if bare == "\\":
                removed += 1
                i += 1
                continue
            if bare in ("include", "-include", "sinclude"):
                # Emptied include directive: expands to nothing yet confuses
                # some make readers, so drop it instead of keeping `include `.
                removed += 1
                i += 1
                continue
            out.append(new_line)
            removed += 1
            i += 1
        new_text = "".join(out)
        new_text = re.sub(r"\\[ \t]*\Z", "", new_text)
        if needle in new_text:
            raise ConanInvalidConfiguration(
                "GOA excision failed for %s: references remain" % path)
        if strict and not removed:
            raise ConanInvalidConfiguration(
                "GOA excision found no reference in %s, upstream layout changed"
                % path)
        fresh_odd = [content for _, content in self._odd_quote_logicals(
            new_text.splitlines(keepends=True)) if content not in before]
        if fresh_odd:
            raise ConanInvalidConfiguration(
                "GOA excision broke shell quoting in %s: %d new odd-quote "
                "line(s), first: %s" % (path, len(fresh_odd), fresh_odd[0]))
        self.output.info(
            "GOA excision quote audit clean for %s (%d removal(s))"
            % (path, removed))
        if new_text != text:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(new_text)
        return removed

    def _replace_once(self, path, old, new, desc):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        n = text.count(old)
        if n != 1:
            raise ConanInvalidConfiguration(
                "soup3 port: %s: expected 1 occurrence in %s, found %d "
                "(upstream layout changed)" % (desc, path, n))
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace(old, new, 1))
        self.output.info("soup3 port: %s in %s" % (desc, path))

    def _replace_all(self, path, old, new, desc):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        n = text.count(old)
        if n < 1:
            raise ConanInvalidConfiguration(
                "soup3 port: %s: expected >=1 occurrence in %s, found 0 "
                "(upstream layout changed)" % (desc, path))
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace(old, new))
        self.output.info("soup3 port: %s: %d replacement(s) in %s" % (desc, n, path))

    def _port_to_soup3_rest1(self):
        """Port upstream 0.2.5 from rest-0.7/soup-2.4 to rest-1.0/soup-3.0.

        Replaces the former patches/0001 unified diff (which failed in
        preflight with hunk-offset mismatches: photo.c expected
        'GInputStream*' at 409 vs actual signature line, simple/goa
        authorizer hunks off by 2 lines, and -- more fundamentally --
        the diff only touched configure.ac/Makefile.am while the build
        consumes the pre-generated configure/Makefile.in, so even a
        perfectly applied diff could not redirect the pkg-config probes).
        Exact-token replacements with loud count asserts: any upstream
        layout change fails the build instead of silently shipping a
        half-ported tree.
        Must run before _excise_goa_backend (the excise asserts the
        ported libgfbgraph.pc.in Requires line).
        """
        src = self.source_folder
        # --- configure.ac (template) + configure (generated, actually used) ---
        cac = os.path.join(src, "configure.ac")
        self._replace_once(
            cac,
            "PKG_CHECK_MODULES(LIBGFBGRAPH, [glib-2.0 gio-2.0 gobject-2.0 rest-0.7 json-glib-1.0])",
            "PKG_CHECK_MODULES(LIBGFBGRAPH, [glib-2.0 gio-2.0 gobject-2.0 rest-1.0 json-glib-1.0])",
            "configure.ac rest-0.7")
        self._replace_once(
            cac,
            "PKG_CHECK_MODULES(SOUP, [libsoup-2.4])\nSOUP_UNSTABLE_CPPFLAGS=-DLIBSOUP_USE_UNSTABLE_REQUEST_API",
            "PKG_CHECK_MODULES(SOUP, [libsoup-3.0])\nSOUP_UNSTABLE_CPPFLAGS=",
            "configure.ac soup-2.4")
        cfg = os.path.join(src, "configure")
        self._replace_all(cfg, "rest-0.7", "rest-1.0", "configure rest token")
        self._replace_all(cfg, "libsoup-2.4", "libsoup-3.0", "configure soup token")
        self._replace_once(
            cfg,
            "SOUP_UNSTABLE_CPPFLAGS=-DLIBSOUP_USE_UNSTABLE_REQUEST_API",
            "SOUP_UNSTABLE_CPPFLAGS=",
            "configure SOUP_UNSTABLE define")
        if "rest-0.7" in open(cfg, encoding="utf-8").read():
            raise ConanInvalidConfiguration("soup3 port: configure still references rest-0.7")
        if "libsoup-2.4" in open(cfg, encoding="utf-8").read():
            raise ConanInvalidConfiguration("soup3 port: configure still references libsoup-2.4")
        # --- GIR includes (.am template + .in generated, introspection off but keep consistent) ---
        mam = os.path.join(src, "gfbgraph", "Makefile.am")
        self._replace_once(mam, "Rest-0.7", "Rest-1.0", "Makefile.am Rest GIR")
        self._replace_once(mam, "Soup-2.4", "Soup-3.0", "Makefile.am Soup GIR")
        mki = os.path.join(src, "gfbgraph", "Makefile.in")
        self._replace_once(mki, "Rest-0.7", "Rest-1.0", "Makefile.in Rest GIR")
        self._replace_once(mki, "Soup-2.4", "Soup-3.0", "Makefile.in Soup GIR")
        # --- libgfbgraph.pc.in (goa-1.0 kept here; _excise_goa_backend drops it) ---
        pcin = os.path.join(src, "libgfbgraph.pc.in")
        self._replace_once(
            pcin,
            "Requires: gio-2.0 glib-2.0 goa-1.0 json-glib-1.0 libsoup-2.4 rest-0.7",
            "Requires: gio-2.0 glib-2.0 goa-1.0 json-glib-1.0 libsoup-3.0 rest-1.0",
            "pc.in Requires")
        # --- gfbgraph-photo.c: drop soup-request headers ---
        photo = os.path.join(src, "gfbgraph", "gfbgraph-photo.c")
        self._replace_once(
            photo,
            "#include <libsoup/soup.h>\n"
            "#include <libsoup/soup-request.h>\n"
            "#include <libsoup/soup-request-http.h>\n"
            "#include <libsoup/soup-requester.h>\n",
            "#include <libsoup/soup.h>\n",
            "photo.c soup-request headers")
        # --- gfbgraph-photo.c: SoupRequester -> SoupSession send (soup3) ---
        old_dl = (
            "        SoupSession *session;\n"
            "        SoupRequester *requester;\n"
            "        SoupRequest *request;\n"
            "        SoupMessage *message;\n"
        )
        new_dl = (
            "        SoupSession *session;\n"
            "        SoupMessage *message;\n"
        )
        self._replace_once(photo, old_dl, new_dl, "photo.c download locals")
        old_body = (
            "        session = soup_session_sync_new ();\n"
            "        requester = soup_requester_new ();\n"
            "        g_object_set (G_OBJECT (session), \"ssl-use-system-ca-file\", TRUE, NULL);\n"
            "        soup_session_add_feature (session, SOUP_SESSION_FEATURE (requester));\n"
            "\n"
            "        request = soup_requester_request (requester, priv->source, error);\n"
            "        if (request != NULL) {\n"
            "                message = soup_request_http_get_message (SOUP_REQUEST_HTTP (request));\n"
            "\n"
            "                stream = soup_request_send (request, NULL, error);\n"
            "                if (stream != NULL) {\n"
            "                        g_object_weak_ref (G_OBJECT (stream), (GWeakNotify) g_object_unref, session);\n"
            "                }\n"
            "\n"
            "                g_clear_object (&message);\n"
            "                g_clear_object (&request);\n"
            "        }\n"
            "\n"
            "        g_clear_object (&requester);\n"
            "\n"
            "        return stream;\n"
        )
        new_body = (
            "        session = soup_session_new ();\n"
            "\n"
            "        message = soup_message_new (\"GET\", priv->source);\n"
            "        if (message != NULL) {\n"
            "                stream = soup_session_send (session, message, NULL, error);\n"
            "                if (stream != NULL) {\n"
            "                        g_object_weak_ref (G_OBJECT (stream), (GWeakNotify) g_object_unref, session);\n"
            "                } else {\n"
            "                        g_object_unref (session);\n"
            "                }\n"
            "\n"
            "                g_clear_object (&message);\n"
            "        } else {\n"
            "                g_object_unref (session);\n"
            "                g_set_error (error, G_IO_ERROR, G_IO_ERROR_INVALID_ARGUMENT,\n"
            "                             \"Invalid photo source URI: %s\", priv->source);\n"
            "        }\n"
            "\n"
            "        return stream;\n"
        )
        self._replace_once(photo, old_body, new_body, "photo.c download body")
        # --- authorizer SoupURI -> GUri (simple + goa; goa file is excised from
        # --- the build but kept consistent so the tree has one soup generation) ---
        for fname, priv_macro in (
            ("gfbgraph-simple-authorizer.c", "GFBGRAPH_SIMPLE_AUTHORIZER"),
            ("gfbgraph-goa-authorizer.c", "GFBGRAPH_GOA_AUTHORIZER"),
        ):
            apath = os.path.join(src, "gfbgraph", fname)
            old_auth = (
                "        gchar *auth_value;\n"
                "        SoupURI *uri;\n"
            )
            new_auth = (
                "        gchar *auth_value;\n"
                "        GUri *old_uri;\n"
                "        gchar *old_str;\n"
                "        gchar *new_str;\n"
                "        GUri *new_uri;\n"
                "        GError *uri_error = NULL;\n"
            )
            self._replace_once(apath, old_auth, new_auth, fname + " auth locals")
            old_q = (
                "        uri = soup_message_get_uri (message);\n"
                "        auth_value = g_strconcat (\"access_token=\", priv->access_token, NULL);\n"
                "        soup_uri_set_query (uri, auth_value);\n"
            )
            new_q = (
                "        old_uri = soup_message_get_uri (message);\n"
                "        auth_value = g_strconcat (\"access_token=\", priv->access_token, NULL);\n"
                "        old_str = g_uri_to_string (old_uri);\n"
                "        if (strchr (old_str, \'?\') != NULL)\n"
                "                new_str = g_strconcat (old_str, \"&\", auth_value, NULL);\n"
                "        else\n"
                "                new_str = g_strconcat (old_str, \"?\", auth_value, NULL);\n"
                "        new_uri = g_uri_parse (new_str, G_URI_FLAGS_NONE, &uri_error);\n"
                "        if (new_uri != NULL) {\n"
                "                soup_message_set_uri (message, new_uri);\n"
                "                g_uri_unref (new_uri);\n"
                "        } else {\n"
                "                g_warning (\"gfbgraph: cannot append auth query to message URI: %s\",\n"
                "                           uri_error ? uri_error->message : \"parse error\");\n"
                "                g_clear_error (&uri_error);\n"
                "        }\n"
                "        g_free (old_str);\n"
                "        g_free (new_str);\n"
            )
            self._replace_once(apath, old_q, new_q, fname + " auth query")
            with open(apath, encoding="utf-8") as handle:
                atext = handle.read()
            if "#include <string.h>" not in atext:
                anchor_inc = '#include "gfbgraph-authorizer.h"'
                if fname == "gfbgraph-simple-authorizer.c":
                    anchor_inc = '#include "gfbgraph-simple-authorizer.h"'
                else:
                    anchor_inc = '#include "gfbgraph-goa-authorizer.h"'
                self._replace_once(
                    apath, anchor_inc + "\n", anchor_inc + "\n#include <string.h>\n",
                    fname + " string.h")
        # --- tests teardown: send_message -> send_and_read (soup3) ---
        gtest = os.path.join(src, "tests", "gtestutils.c")
        self._replace_once(
            gtest,
            "        g_autoptr(SoupMessage) smessage = NULL;\n",
            "        g_autoptr(SoupMessage) smessage = NULL;\n"
            "        g_autoptr(GBytes) body = NULL;\n",
            "gtestutils body local")
        self._replace_once(
            gtest,
            "        status = soup_session_send_message (ssession, smessage);\n",
            "        body = soup_session_send_and_read (ssession, smessage, NULL, NULL);\n"
            "        status = soup_message_get_status (smessage);\n",
            "gtestutils teardown send")
        # --- fail-loud gate: no soup2-generation token may remain in built inputs ---
        leftovers = []
        for root, _dirs, files in os.walk(src):
            for fn in files:
                if not fn.endswith((".c", ".h", ".ac", ".am", ".in")):
                    continue
                if fn == "gfbgraph-goa-authorizer.c" or fn == "gfbgraph-goa-authorizer.h":
                    continue
                pp = os.path.join(root, fn)
                try:
                    with open(pp, encoding="utf-8", errors="replace") as handle:
                        tt = handle.read()
                except OSError:
                    continue
                for tok in ("rest-0.7", "libsoup-2.4", "Rest-0.7", "Soup-2.4",
                            "soup-requester", "soup_requester", "SoupURI",
                            "soup_uri_set_query", "soup_session_sync_new",
                            "soup_session_send_message",
                            "LIBSOUP_USE_UNSTABLE_REQUEST_API"):
                    if tok in tt:
                        leftovers.append("%s:%s" % (os.path.relpath(pp, src), tok))
                        break
        if leftovers:
            raise ConanInvalidConfiguration(
                "soup3 port incomplete, soup2 tokens remain in: " + ", ".join(sorted(leftovers)))
        self.output.info("soup3 port gate passed: no soup2 tokens in built inputs")

    def _excise_goa_backend(self):
        """Remove the GOA authorizer from the build (OHOS scope decision).

        Upstream builds gfbgraph-goa-authorizer.c against goa-1.0, whose only
        OHOS provider would force a sandbox source build that cannot succeed
        here; OHOS runs no goa-daemon so the backend is dead at runtime. The
        tarball ships pre-generated files and workers run no autoreconf, so
        the generated gfbgraph/Makefile.in is edited in place (Makefile.am is
        mirrored best-effort), the umbrella header include is dropped, the
        libgfbgraph.pc.in Requires is trimmed (exact-line assert, which also
        proves _port_to_soup3_rest1() ran), and the configure probe is bypassed via
        GOA_CFLAGS/GOA_LIBS (see build()).
        Every step asserts loudly: an upstream layout change must fail the
        build, never silently ship a half-excised tree.
        """
        needle = "gfbgraph-goa-authorizer"
        excised_pair = ("gfbgraph-goa-authorizer.c", "gfbgraph-goa-authorizer.h")
        src = self.source_folder
        goa_c = os.path.join(src, "gfbgraph", excised_pair[0])
        if not os.path.isfile(goa_c):
            raise ConanInvalidConfiguration(
                "GOA excision aborted: %s not found, upstream layout changed"
                % goa_c)
        made_in = os.path.join(src, "gfbgraph", "Makefile.in")
        if not os.path.isfile(made_in):
            raise ConanInvalidConfiguration(
                "GOA excision aborted: %s not found" % made_in)
        subs = self._drop_make_tokens(made_in, needle, strict=True)
        self.output.info("GOA excision: %d reference(s) dropped from Makefile.in" % subs)
        made_am = os.path.join(src, "gfbgraph", "Makefile.am")
        if os.path.isfile(made_am):
            subs_am = self._drop_make_tokens(made_am, needle, strict=False)
            if subs_am:
                self.output.info(
                    "GOA excision: %d reference(s) dropped from Makefile.am" % subs_am)
            else:
                self.output.warning("GOA excision: no reference in Makefile.am, left untouched")
        umbrella = os.path.join(src, "gfbgraph", "gfbgraph.h")
        if os.path.isfile(umbrella):
            with open(umbrella, encoding="utf-8") as handle:
                header = handle.read()
            kept = [ln for ln in header.splitlines(keepends=True)
                    if needle not in ln or not ln.lstrip().startswith("#")]
            if len(kept) != len(header.splitlines(keepends=True)):
                with open(umbrella, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("".join(kept))
                self.output.info("GOA excision: umbrella header include dropped")
            else:
                self.output.warning("GOA excision: umbrella header has no goa include")
        pc_in = os.path.join(src, "libgfbgraph.pc.in")
        if not os.path.isfile(pc_in):
            raise ConanInvalidConfiguration(
                "GOA excision aborted: %s not found" % pc_in)
        with open(pc_in, encoding="utf-8") as handle:
            pc_text = handle.read()
        old_requires = ("Requires: gio-2.0 glib-2.0 goa-1.0 "
                        "json-glib-1.0 libsoup-3.0 rest-1.0")
        new_requires = ("Requires: gio-2.0 glib-2.0 "
                        "json-glib-1.0 libsoup-3.0 rest-1.0")
        if old_requires not in pc_text:
            raise ConanInvalidConfiguration(
                "GOA excision aborted: expected Requires line not found in "
                "libgfbgraph.pc.in (patch 0001 output changed?)")
        with open(pc_in, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(pc_text.replace(old_requires, new_requires, 1))
        self.output.info("GOA excision: goa-1.0 dropped from libgfbgraph.pc.in")
        # Fail-loud gate: nothing that gets compiled may reference goa any
        # more. The excised (now unbuilt) pair keeps its code and is skipped;
        # configure.ac is not consumed without autoreconf and is skipped.
        markers = ("goa-1.0", "goa/", "Goa", "GOA")
        leftovers = []
        for root, _dirs, files in os.walk(src):
            for fn in files:
                if fn in excised_pair:
                    continue
                is_source = fn.endswith((".c", ".h"))
                is_make = fn in ("Makefile.in", "Makefile.am")
                if not (is_source or is_make):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        text = handle.read()
                except OSError:
                    continue
                if is_make:
                    hit = needle in text or "goa-1.0" in text
                else:
                    hit = any(m in text for m in markers)
                if hit:
                    leftovers.append(os.path.relpath(path, src))
        if leftovers:
            raise ConanInvalidConfiguration(
                "GOA excision incomplete, goa references remain in: "
                + ", ".join(sorted(leftovers)))
        self.output.info("GOA excision gate passed: no compiled input references goa")

    def _patch_config_guess(self):
        guess = os.path.join(self.source_folder, "config.guess")
        if not os.path.isfile(guess):
            return
        with open(guess, encoding="utf-8") as handle:
            content = handle.read()
        if "HarmonyOS|HongMeng)" in content:
            return
        old = 'case "$UNAME_SYSTEM" in'
        if old not in content:
            self.output.warning("config.guess UNAME_SYSTEM case not found, skip E160 patch")
            return
        patched = content.replace(
            old, old + '\n    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;', 1)
        with open(guess, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info("config.guess patched for HarmonyOS (E160)")

    def _patch_autoconf_umask(self, path):
        # HMBS platform diagnosis [unsafe_local_mktemp] (buildtorrent/zurl
        # precedent): HMFS forces setgid on directories, so the autoconf
        # idiom `(umask 077 && mktemp -d ...)` creates drwx--S--- dirs that
        # even the owner cannot write, and config.status dies with
        # `can't create ./confXXXXXX/subs1.awk: Permission denied` ->
        # `could not setup config files machinery` (this round's log).
        # Replace umask 077 with 022 so the mktemp/mkdir tmpdir stays
        # writable. Idempotent; only configure/config.status file names
        # are touched. Deliberately the primary fix: under HMBS_CAP_CHMOD=0
        # a mktemp-exit-1 shim alone may not be executable and the mkdir
        # fallback carries the same umask 077 (avahi R22->R23 evidence,
        # buildtorrent draft prohibition), so the shim below is only a
        # configure-phase complement, never the sole fix.
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return 0
        fixed = text.replace("umask 077", "umask 022")
        fixed = fixed.replace("umash 077", "umash 022")
        if fixed != text:
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(fixed)
            except OSError:
                return 0
            n = text.count("umask 077") + text.count("umash 077")
            self.output.info(
                "patched autoconf umask 077->022 in %s (%d occurrence(s))" % (path, n))
            return n
        return 0

    def _stabilize_autotools_mtimes(self):
        # Keep `make` from firing maintainer rebuild rules (juise/3.0.0
        # `touch -r aclocal.m4 configure.ac` precedent, reimplemented with
        # os.utime so no shell/toybox dependency). In-place edits of
        # configure.ac/Makefile.am without autoreconf bump their mtimes past
        # the shipped aclocal.m4/configure/Makefile.in, so make tries to
        # rebuild via `missing aclocal-1.16`/`automake-1.16` (absent on the
        # device, Error 127).
        # Past-only pin (no future touch): the previous two-tier scheme
        # touched generated files to now+5, which puts distributed files in
        # the future so configure's sanity check ("newly created file is
        # older than distributed files!") fails. Instead, pin every template
        # to (min generated mtime - 2s): strictly older than any generated
        # file, past-dated, so both the maintainer rules and the sanity
        # check pass. Generated files are left untouched (edited ones are
        # already `now`, unedited ones stay at tarball time).
        # Best-effort: missing files are skipped silently.
        src = self.source_folder
        try:
            gen_mtimes = []
            for rel in ("aclocal.m4", "configure", "config.h.in"):
                p = os.path.join(src, rel)
                if os.path.isfile(p):
                    try:
                        gen_mtimes.append(int(os.stat(p).st_mtime))
                    except OSError:
                        pass
            for root, _dirs, files in os.walk(src):
                if "Makefile.in" in files:
                    try:
                        gen_mtimes.append(int(os.stat(
                            os.path.join(root, "Makefile.in")).st_mtime))
                    except OSError:
                        pass
            if not gen_mtimes:
                self.output.warning("no generated autotools files found, mtime pin skipped")
                return
            pin = min(gen_mtimes) - 2
            pinned = 0
            for rel in ("configure.ac", "acinclude.m4"):
                p = os.path.join(src, rel)
                if os.path.isfile(p):
                    os.utime(p, (pin, pin))
                    pinned += 1
            for root, _dirs, files in os.walk(src):
                if "Makefile.am" in files:
                    os.utime(os.path.join(root, "Makefile.am"), (pin, pin))
                    pinned += 1
            self.output.info(
                "pinned %d autotools template(s) to %d "
                "(min generated %d minus 2s, past-only)" % (pinned, pin, min(gen_mtimes)))
        except OSError as exc:
            self.output.warning("autotools mtime pin skipped: %s" % exc)

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp] complement: when
        # HMBS injects HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during
        # the configure step only so calls for "./conf*" fail and Autoconf
        # falls back to its `mkdir` path (cyrus-sasl-*/cxxtools precedent).
        # All other mktemp calls delegate to the real binary; TMPDIR itself
        # stays writable. Uses /bin/sh shebang (HMBS guarantees shell
        # /bin/sh, same shell this recipe already uses). Created with
        # os.open mode 0o755 so the exec bit is set at creation even when
        # HMBS_CAP_CHMOD=0 ignores later chmod. Returns shim dir or "".
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        try:
            shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        real = shutil.which("mktemp") or ""
        candidates = " ".join(
            c for c in (real, "/bin/mktemp", "/usr/bin/mktemp") if c)
        script = (
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in %s; do\n" % candidates +
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        except OSError:
            return ""
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
        except OSError:
            try:
                os.unlink(shim)
            except OSError:
                pass
            return ""
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        self.output.info("HMBS mktemp fallback shim active for configure: %s" % shim_dir)
        return shim_dir

    def _run_upstream_tests(self, cc):
        # Same shell discipline as build(): env-prefix (not configure args,
        # not a scoped Environment that the helper re-orders) plus the
        # _as_can_reexec kill-switch. Serial check: same OOM fork guard.
        # CC= stays a make command-line override for the sandbox fallback.
        # Loader path is scoped to test processes via TESTS_ENVIRONMENT
        # (automake prepends it to each test command only): the global
        # process env stays clean so clang/lld link steps inside this same
        # `make check` invocation keep using the system libxml2 instead of
        # conan's incompatible copy (conftest/lld hijack fix).
        env_prefix = self._shell_env_prefix()
        try:
            _libdirs = self._dependency_libdirs()
        except Exception:
            _libdirs = []
        _tests_env_arg = ""
        if _libdirs:
            _joined = os.pathsep.join(_libdirs)
            self.output.info("Using TESTS_ENVIRONMENT LD_LIBRARY_PATH with %d dep libdir(s)"
                             % len(_libdirs))
            _tests_env_arg = " %s" % shlex.quote(
                "TESTS_ENVIRONMENT=LD_LIBRARY_PATH=%s" % _joined)
        _check_failed = False
        _check_error = ""
        try:
            self.run("umask 022 && %s make check -j1 V=1%s %s" % (
                env_prefix, _tests_env_arg, shlex.quote("CC=%s" % cc)),
                     cwd=self.build_folder, env="conanbuild")
        except Exception as exc:
            # make check exits 2 on any FAIL; must still dump per-test logs
            # and emit markers so the failure is diagnosable instead of a
            # bare "Error 2" with discovered=0.
            _check_failed = True
            _check_error = str(exc)[-500:]
            self.output.warning("make check exited non-zero, collecting test logs: %s" % _check_error)
        self._dump_upstream_logs()
        payload = self._parse_autotools_results()
        if _check_failed and int(payload.get("failed", 0)) == 0 and int(payload.get("passed", 0)) == 0:
            payload["reason"] = ("make check failed before test-suite.log was written: %s "
                                 "(searched tests/test-suite.log)" % _check_error)
            payload["status"] = "failed"
            try:
                payload["failed"] = int(payload.get("discovered", UPSTREAM_TEST_TOTAL))
            except Exception:
                pass
        self._emit_upstream_marker(payload)
        self._write_upstream_json(payload)
        if _check_failed or payload.get("failed", 0) > 0:
            raise ConanInvalidConfiguration(
                "gfbgraph upstream tests failed: %s" % json.dumps(payload))

    def _dump_upstream_logs(self):
        # Evidence preserver (xauth takeaway): CI/preflight only keeps the
        # log tail, while the loader/assertion clue sits in per-test *.log
        # files ahead of the summary. Re-print them here so the next round
        # sees the real stderr (e.g. "Error loading shared library" vs a
        # genuine g_assert failure). Most valuable last: per-test logs after
        # the suite summary. Capped per file to bound log volume.
        try:
            tests_dir = os.path.join(self.build_folder, "tests")
        except Exception:
            return
        paths = []
        try:
            suite = os.path.join(tests_dir, "test-suite.log")
            if os.path.isfile(suite):
                paths.append(suite)
            try:
                names = sorted(os.listdir(tests_dir))
            except OSError:
                names = []
            for fn in names:
                if fn.endswith(".log") and fn != "test-suite.log":
                    fp = os.path.join(tests_dir, fn)
                    if os.path.isfile(fp) and fp not in paths:
                        paths.append(fp)
        except Exception as exc:
            self.output.warning("upstream log collect skipped: %s" % exc)
            return
        for fp in paths:
            try:
                with open(fp, encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError as exc:
                self.output.warning("cannot read %s: %s" % (fp, exc))
                continue
            rel = fp
            try:
                rel = os.path.relpath(fp, self.build_folder)
            except Exception:
                pass
            self.output.info("===== upstream log %s (%d lines) =====" % (rel, len(lines)))
            cap = 120
            shown = lines[-cap:] if len(lines) > cap else lines
            if len(lines) > cap:
                self.output.info("[... %d earlier line(s) omitted ...]" % (len(lines) - cap))
            for ln in shown:
                self.output.info("UPSTREAMLOG %s: %s" % (os.path.basename(fp), ln[:500]))

    def _parse_autotools_results(self):
        candidates = [
            os.path.join(self.build_folder, "tests", "test-suite.log"),
            os.path.join(self.build_folder, "test-suite.log"),
        ]
        log_path = next((p for p in candidates if os.path.isfile(p)), None)
        if log_path is None:
            try:
                found = glob.glob(
                    os.path.join(self.build_folder, "**", "test-suite.log"), recursive=True)
            except Exception:
                found = []
            if found:
                log_path = sorted(found)[0]
        if log_path is None:
            searched = candidates + [os.path.join(self.build_folder, "**", "test-suite.log")]
            return {
                "status": "failed",
                "framework": "autotools",
                "command": "make check",
                "discovered": UPSTREAM_TEST_TOTAL,
                "executed": 0,
                "passed": 0,
                "failed": UPSTREAM_TEST_TOTAL,
                "skipped": 0,
                "reason": "test-suite.log not found; searched: " + "; ".join(searched),
            }
        total = passed = failed = skipped = None
        try:
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            return {
                "status": "failed",
                "framework": "autotools",
                "command": "make check",
                "discovered": UPSTREAM_TEST_TOTAL,
                "executed": 0,
                "passed": 0,
                "failed": UPSTREAM_TEST_TOTAL,
                "skipped": 0,
                "reason": "cannot read %s: %s" % (log_path, exc),
            }
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("# TOTAL:"):
                total = int(line.split(":", 1)[1].strip())
            elif line.startswith("# PASS:"):
                passed = int(line.split(":", 1)[1].strip())
            elif line.startswith("# FAIL:"):
                failed = int(line.split(":", 1)[1].strip())
            elif line.startswith("# SKIP:"):
                skipped = int(line.split(":", 1)[1].strip())
        if total is None or passed is None or failed is None or skipped is None:
            return {
                "status": "failed",
                "framework": "autotools",
                "command": "make check",
                "discovered": UPSTREAM_TEST_TOTAL,
                "executed": 0,
                "passed": 0,
                "failed": UPSTREAM_TEST_TOTAL,
                "skipped": 0,
                "reason": "cannot parse TOTAL/PASS/FAIL/SKIP from %s" % log_path,
            }
        executed = passed + failed
        status = "passed" if failed == 0 else "failed"
        return {
            "status": status,
            "framework": "autotools",
            "command": "make check",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    def _emit_upstream_marker(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload, separators=(",", ":"))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def _write_upstream_json(self, payload):
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except OSError as exc:
            self.output.warning("write hmbs_upstream.json failed: %s" % exc)

    def _write_install_shim(self):
        # Multi-file install shim (zurl/1.12.0 + fslsfonts/1.0.7 precedent):
        # the HMBS-provided `install` accepts only single-file two-arg
        # invocations (`[ $# -eq 2 ] || exit 64`, EX_USAGE), while automake's
        # install-libgfbgraph_0.2_laHEADERS batches all 10 headers into one
        # `install -c -m 644 h1 h2 ... includedir` call -> Error 64 (this
        # round's log shows the batched header install then
        # `install-libgfbgraph_0.2_laHEADERS Error 64`). Same family as
        # lzop (E098/E174) and myman (E182/E188). The shim copies SRC...
        # DEST (DEST may be a directory), parses -c/-m only, and treats
        # chmod as best-effort (`|| true`) for HMBS_CAP_CHMOD=0.
        # Created executable via os.open mode (HMFS takes the mode from the
        # open call, no later chmod needed); executed by direct path, so
        # the exec bit matters (qt5-qtbase precedent).
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            pass
        shim = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
            "set -eu\n"
            "mode=\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -p|-c) shift ;;\n"
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
            "    --) shift; break ;;\n"
            "    -*) shift ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "[ $# -ge 2 ] || exit 2\n"
            "dest=\n"
            "for arg in \"$@\"; do dest=$arg; done\n"
            "count=$(($# - 1))\n"
            "if [ \"$count\" -gt 1 ]; then\n"
            "  mkdir -p \"$dest\"\n"
            "else\n"
            "  mkdir -p \"$(dirname \"$dest\")\"\n"
            "fi\n"
            "i=1\n"
            "for src in \"$@\"; do\n"
            "  [ $i -gt $count ] && break\n"
            "  cp -f \"$src\" \"$dest\"\n"
            "  if [ -n \"$mode\" ]; then\n"
            "    if [ -d \"$dest\" ]; then\n"
            "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
            "    else\n"
            "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        try:
            fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        except OSError as exc:
            self.output.warning("install shim create skipped: %s" % exc)
            return shim
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
        except Exception:
            try:
                os.unlink(shim)
            except OSError:
                pass
            raise
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        self.output.info("install shim ready: %s" % shim)
        return shim

    def _redirect_install_to_shim(self, shim_install):
        # configure baked the probed `install` absolute path into every
        # generated Makefile (INSTALL = <runtime>/bin/install -c).
        # INSTALL_DATA/INSTALL_PROGRAM derive from ${INSTALL}, so
        # redirecting INSTALL covers the failing header-install rule; any
        # direct INSTALL_DATA/PROGRAM/SCRIPT line carrying an absolute
        # /install path is redirected as well (zurl/lzop precedent). Only
        # Makefile file names are touched. Idempotent.
        redirected = 0
        for _dir, _dirs, _files in os.walk(self.build_folder):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_dir, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    _content = handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            if "/install" not in _content and "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append("%sINSTALL = %s\n" % (_indent, shim_install))
                    _changed = True
                elif (_stripped.startswith("INSTALL_DATA = ")
                      or _stripped.startswith("INSTALL_PROGRAM = ")
                      or _stripped.startswith("INSTALL_SCRIPT = ")) \
                        and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _key = _stripped.split(" = ", 1)[0]
                    _lines.append("%s%s = %s\n" % (_indent, _key, shim_install))
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                try:
                    with open(_mp, "w", encoding="utf-8",
                              errors="surrogateescape", newline="\n") as handle:
                        handle.write("".join(_lines))
                    redirected += 1
                except OSError as exc:
                    self.output.warning("redirect %s skipped: %s" % (_mp, exc))
        self.output.info("install shim redirect: %d Makefile(s)" % redirected)

    def package(self):
        # Direct `make install` under the same shell prefix (Makefile SHELL
        # was baked as /bin/sh by the guarded configure above; the prefix
        # also guards the spawning shell itself). DESTDIR replicates
        # Autotools.install() staging with --prefix=/.
        # HMBS install-shim redirect first (see _write_install_shim): the
        # preflight `install` only handles single-file installs, while this
        # package batches 10 headers in one call -> Error 64 without it.
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(_shim)
        except Exception as exc:
            self.output.warning("install shim setup failed: %s" % exc)
        env_prefix = self._shell_env_prefix()
        self.run("umask 022 && %s make -j1 V=1 install DESTDIR=%s" % (
            env_prefix, shlex.quote(self.package_folder)),
            cwd=self.build_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # E236: drop installed libtool archives (hwloc precedent). Our
        # install uses --libdir=/lib, so libgfbgraph.la would bake
        # libdir='/lib' plus dependency -L/-l lines with build-machine
        # absolute paths -- the same non-relocatable poison class that
        # broke this build via the dependencies. Downstream links via
        # .pc/cpp_info (-l) and never needs the .la.
        for _pat in ("lib/*.la", "lib/*/*.la"):
            for _la in glob.glob(os.path.join(self.package_folder, _pat)):
                try:
                    os.unlink(_la)
                    self.output.info("removed installed libtool archive: %s" % _la)
                except OSError as exc:
                    self.output.warning("remove %s skipped: %s" % (_la, exc))
        src = os.path.join(self.build_folder, "hmbs_upstream.json")
        if os.path.isfile(src):
            dst_dir = os.path.join(self.package_folder, "res")
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(dst_dir, "hmbs_upstream.json"))
        else:
            self.output.warning("hmbs_upstream.json missing in package()")
        if self.settings.os == "OHOS":
            self._sign_installed_libs()

    def _sign_installed_libs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found, skip OHOS codesign")
            return
        import subprocess
        patterns = [
            os.path.join(self.package_folder, "lib", "*.so*"),
        ]
        cands = []
        for pat in patterns:
            cands.extend(glob.glob(pat))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            clean_env = {
                "PATH": "/data/service/hnp/bin:/system/bin:/usr/bin:/bin",
                "HOME": os.environ.get("HOME", "/data/storage/el2/base"),
                "LD_LIBRARY_PATH": "",
                "TMPDIR": os.environ.get("TMPDIR", "/data/storage/el2/base/temp"),
            }
            result = subprocess.run(
                [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
                env=clean_env, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise ConanInvalidConfiguration(
                    "binary-sign-tool failed for %s: %s %s"
                    % (binary, result.stdout[-500:], result.stderr[-500:]))

    def package_info(self):
        self.cpp_info.libs = ["gfbgraph-0.2"]
        self.cpp_info.includedirs = ["include/gfbgraph-0.2", "include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "gfbgraph")
        self.cpp_info.set_property("cmake_target_name", "gfbgraph::gfbgraph")
        self.cpp_info.set_property("pkg_config_name", "libgfbgraph-0.2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
