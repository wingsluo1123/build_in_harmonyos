#!/usr/bin/env python3
"""Conan recipe — libdmapsharing 3.9.14 (Autotools).

libdmapsharing is a DMAP (DAAP/DPAP/DACP) media-sharing library written in C
with GObject and libsoup. Adapted to HarmonyOS PC (aarch64, musl, clang).

Dependency / single-GObject-copy strategy (follows libsoup3 3.6.5-r3 and
libgepub 0.7.3 precedents):
  - The whole chain is pinned to the SAME shared glib/2.84.0.1.1 so there is
    exactly one GObject type system (a second glib copy aborts at runtime
    with "cannot register existing type"; the libsoup3-r3 chain resolved
    this with shared glib). libsoup3/3.6.5-r3 already pins glib/2.84.0.1.1;
    avahi-glib/0.9_rc5 pins glib/2.84.0.1. The two exact pins conflict, so
    glib is declared in requirements() as an OVERRIDE to force 2.84.0.1.1
    graph-wide; glib is then reached through libsoup3's dependency chain via
    self._glib_pkg().
  - libdmapsharing itself is built static and its test consumer links against
    the shared glib/soup/avahi/check runtimes (single-copy doctrine).
  - configure.ac hard-requires avahi-client>=0.6 + avahi-glib>=0.6 (mDNS) and
    libsoup-3.0; optional extras (gdk-pixbuf, gstreamer-app, GTK3, gee, vala,
    introspection, gtk-doc) are disabled.

Upstream tests: 6 Check (libcheck) suites totalling 45 START_TEST cases,
embedded inline in libdmapsharing/dmap-{av-connection,av-record,av-share,
connection,md5,utils}.c and aggregated by the generated tests/unit-test
binary. The recipe builds the library (which runs ./generate-test-suites) and
tests/, then runs tests/unit-test directly (the official `make check` target
additionally does a coverage rebuild with gcov that is not meaningful on
OHOS). See notes.md for per-file counts and the platform-gap analysis.
"""
import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class LibdmapsharingConan(ConanFile):
    required_conan_version = ">=2.28"
    name = "libdmapsharing"
    version = "3.9.14"
    description = "DMAP (DAAP/DPAP/DACP) media sharing library using GObject and libsoup"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.flyn.org/projects/libdmapsharing/"
    url = "https://www.flyn.org/projects/libdmapsharing/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    # Source is vendored (see source() and conandata.yml): the canonical
    # 3.9.14 release tree (sha256 4ad60d94... verified locally) is committed
    # under src/ and exported with the recipe, so the build no longer depends
    # on the flaky www.flyn.org HTTPS endpoint (connect-timeouts observed on
    # the OHOS preflight machine).
    exports_sources = "src/*", "media_data.py"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # Shared glib pinned to 2.84.0.1.1: same single-GObject-copy pin as the
        # libsoup3/3.6.5-r3 chain (a second glib copy causes "cannot register
        # existing type" SIGABRT). libsoup3 pins glib/2.84.0.1.1 (exact) while
        # avahi-glib's own recipe pins glib/2.84.0.1 (exact); conan 2 refuses
        # two different exact pins of one package in a graph ("Version
        # conflict"). The version conflict must be resolved with an OVERRIDE,
        # which forces 2.84.0.1.1 for every glib requirement graph-wide.
        # NOTE: an override requirement does NOT create a graph edge from this
        # recipe (conan strips it from self.dependencies), so glib must be
        # reached through one of the real direct deps that carry it
        # (libsoup3-r3 requires glib/2.84.0.1.1 directly; avahi-glib also
        # propagates it). All glib package access therefore goes via
        # self._glib_pkg() (_fix_glib_pc_files / _stage_glib_python_tools /
        # generate glib-bin PATH / _prepend_runtime_libdirs / package_info).
        # glib's shared=True option is carried by libsoup3-r3's own glib
        # requirement, so the single shared glib copy doctrine is preserved.
        self.requires("glib/2.84.0.1.1", override=True)
        # libdmapsharing configure.ac: PKG_CHECK_MODULES(SOUP, libsoup-3.0)
        self.requires("libsoup3/3.6.5-r3", transitive_libs=True)
        # configure.ac: PKG_CHECK_MODULES(AVAHI, avahi-client >= 0.6
        # avahi-glib >= 0.6) — avahi-glib provides libavahi-client/-common and
        # libavahi-glib/-gobject plus an avahi-glib.pc; recipe supplies the
        # missing avahi-client.pc shim in generate().
        self.requires("avahi-glib/0.9_rc5", transitive_libs=True, transitive_headers=True)
        # configure.ac: PKG_CHECK_MODULES(CHECK, check >= 0.9.4) — required to
        # build the upstream unit-test binary.
        self.requires("check/0.11.0", transitive_libs=True)

    def source(self):
        # Source is vendored (conandata.yml sources: {}): the canonical 3.9.14
        # release tree is committed under src/ and copied from the exported
        # sources folder. This removes the flaky www.flyn.org HTTPS download
        # (connect-timeouts observed on the OHOS preflight machine). No
        # archive is downloaded; the vendored bytes were verified against the
        # official sha256 4ad60d9423434bca5f7aede10a0477668e852ea66091bb5c1fd2ef22afd01a40.
        #
        # The binary test-media fixtures (src/media/*.jpeg/.png/.mp3) are NOT
        # committed to git (GitCode's PR .diff carries no 'GIT binary patch'
        # payload, so `git apply` of the PR diff would fail with 'missing
        # binary patch data'). They are regenerated byte-for-byte here from
        # base64 text in media_data.py (identical to the official release).
        src = os.path.join(self.export_sources_folder, "src")
        shutil.copytree(src, self.source_folder, dirs_exist_ok=True)
        # Load media_data.py from the exported-sources folder by explicit path
        # (import media_data may not resolve there; export_sources_folder is not
        # guaranteed on sys.path).
        media_module = None
        media_py = os.path.join(self.export_sources_folder, "media_data.py")
        if os.path.isfile(media_py):
            import importlib.util
            spec = importlib.util.spec_from_file_location("libdmapsharing_media_data", media_py)
            if spec and spec.loader:
                media_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(media_module)
        payload = getattr(media_module, "MEDIA_BASE64", None) if media_module else None
        if payload:
            import base64
            media_dir = os.path.join(self.source_folder, "media")
            os.makedirs(media_dir, exist_ok=True)
            for name, b64 in payload.items():
                path = os.path.join(media_dir, name)
                with open(path, "wb") as handle:
                    handle.write(base64.b64decode(b64))
                self.output.info(f"regenerated src/media/{name} from media_data.py")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        PkgConfigDeps(self).generate()
        env = Environment()
        # Fix the broken CI-worker AR/AS/STRIP/NM/RANLIB env (llvm-* names not
        # on PATH, libsoup3/gupnp precedent) so libtool/autotools pick the real
        # tools from PATH.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        for variable, key in (("CC", "c"), ("CXX", "cpp")):
            compiler = compilers.get(key)
            if not compiler:
                raise ConanException(
                    f"{variable} missing from tools.build:compiler_executables")
            env.define(variable, compiler)
        # HMFS: glib-mkenums is a python3 script whose shebang exec is rejected;
        # stage a native launcher ahead of the glib bin dir (avahi-glib pattern).
        env.prepend_path("PATH", self._stage_glib_python_tools())
        # All hand-rolled shims needed by configure are written DIRECTLY into
        # the PkgConfigDeps generators folder: glib-2.0/gobject-2.0/gthread-2.0/
        # gmodule-2.0/gio-2.0 (glib is an OVERRIDE dep so PkgConfigDeps does not
        # emit them) and avahi-client.pc/avahi-common.pc (avahi-glib's merged
        # cpp_info emits only avahi-glib.pc). That folder is already on
        # PKG_CONFIG_PATH for configure via the conanbuild/conanrun scripts
        # (proven by 'check >= 0.9.4' resolving from it), so this avoids the
        # unreliable separate-dir-via-dmap_env approach that previously left
        # configure with "Must have glib-2.0 installed". The generators folder
        # is prepended (idempotent) so the .pc are found no matter what.
        self._fix_glib_pc_files()
        # libdmapsharing is built STATIC by libtool (--disable-shared); libtool's
        # static-archive dependency scan reads each dependency library's .la
        # (libtool archive) to record dependency_libs. The avahi-glib conan
        # package ships ONLY plain .a archives (no .la), so libtool dies with
        # "grep/sed: .../lib/libavahi-client.la: No such file" + "is not a valid
        # libtool archive".
        # Round-1 (staging .la shims + "-L<staging>" only in configure LDFLAGS)
        # did NOT fix it on the real device: libtool did not use the extra
        # LDFLAGS -L to derive the avahi .la path, so the shims were never
        # reached. Deterministic round-2 fix (_fix_avahi_la): stage BOTH the
        # real avahi .a archives and .la shims in one staging dir, and point the
        # avahi .pc shims' Libs: at "-L<staging> -lavahi-*" (overriding the
        # PkgConfigDeps-generated avahi-glib.pc). configure then bakes
        # "-L<staging> -lavahi-*" into AVAHI_LIBS -> MDNS_LIBS in the Makefile,
        # so libtool derives "<staging>/libavahi-client.la" from the -L that
        # accompanies -lavahi-*, finds the shim, and resolves its dependency_libs
        # inside staging too (fully self-contained). configure's own
        # PKG_CHECK_MODULES link test still works because the real .a is also in
        # staging.
        self._fix_avahi_la()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # glib bin (glib-genmarshal etc.) on PATH, plus LD_LIBRARY_PATH for the
        # shared glib/soup/avahi/check runtimes at test time.
        glib = self._glib_pkg()
        if glib and glib.package_folder:
            glib_bin = os.path.join(glib.package_folder, "bin")
            if os.path.isdir(glib_bin):
                env.prepend_path("PATH", glib_bin)
        self._prepend_runtime_libdirs(env)
        # HMFS: /tmp is read-only erofs, so the C compiler itself cannot write
        # its conftest executables (AC_PROG_CC "C compiler cannot create
        # executables" / "sed: can't read conftest.c") and configure's
        # AS_TMPDIR mktemp dir lands 2700+setgid and is unwritable. Redirect
        # the whole temp root to the HMBS-provided writable per-task tmpdir
        # (libsieve/libecoli _hmbs_writable_tmpdir precedent). Only the temp
        # root is redirected; no upstream test is touched.
        mktemp_fallback = self._hmbs_writable_tmpdir()
        if mktemp_fallback:
            env.define("TMPDIR", mktemp_fallback)
            env.define("TMP", mktemp_fallback)
            env.define("TEMP", mktemp_fallback)
            self.output.info("HMBS writable tmpdir -> %s" % mktemp_fallback)
        env.vars(self).save_script("dmap_env")

    def build(self):
        apply_conandata_patches(self)
        env = ["conanbuild", "conanrun", "dmap_env"]
        src = self.source_folder
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        # Release tarball ships pregenerated configure/Makefile.in/aclocal.m4,
        # so no autotools toolchain is needed on the build host. However the
        # pristine commit mtime ordering can be disturbed when the source tree
        # is materialised (conan cache export -> copytree), which makes GNU
        # make wake the automake "maintainer" regen rule for Makefile.in
        # ('missing automake-1.18 --gnu' -> "inaccessible or not found", since
        # OHOS hosts have no automake). Fix by normalising the mtime hierarchy
        # so every generated bootstrap file is OLDER than its prerequisites —
        # the maintainer rules then sleep and the pregenerated files are used
        # verbatim (avoids re-bootstrapping with a different automake version,
        # changing the build's provenance). Layering (source < aclocal.m4 <
        # generated) mirrors the actual autotools dependency chain; fixed
        # 200x timestamps stay far below the 202x configure outputs so
        # 'config.status --recheck' also stays asleep.
        #
        # CRITICAL: this normalisation MUST run as the LAST source mutation
        # before configure. The recipe's patchers below rewrite configure,
        # Makefile.in and Makefile.am with current mtimes; if normalisation ran
        # first, those writes (de)stamp Makefile.am (and configure) to the
        # current 20xx timestamp, so e.g. tests/Makefile.am ends up NEWER than
        # tests/Makefile.in and GNU make re-runs `automake-1.18 --gnu
        # tests/Makefile`, failing with 'automake-1.18: inaccessible or not
        # found' (observed in the 2026-09-28 preflight at 'make -C tests
        # unit-test'). Running normalisation after ALL patches re-establishes
        # source(2000) < aclocal.m4(2001) < generated(2002) on the final,
        # patched bytes, so every maintainer regen rule sleeps. The call is
        # therefore placed right before ./configure below.
        # HMFS fix: strip `umask 077` from the AS_TMPDIR temp-dir creation in
        # the shipped generated configure so config.status can write into the
        # mktemp dir (avahi/avahi-glib precedent).
        configure = os.path.join(src, "configure")
        if not os.path.exists(configure):
            raise ConanException("configure missing from libdmapsharing tarball")
        self._patch_generated_configure(configure)
        # Conan builds check with headers in a non-default include dir
        # (<check>/include/check.h), but upstream libdmapsharing compiles its
        # test-instrumented library sources (#include <check.h>, pulled in via
        # libdmapsharing_4_0_la_SOURCES when --enable-tests) with
        # libdmapsharing_4_0_la_CFLAGS that only carry $(CHECK_LIBS) in the
        # LDFLAGS, NOT $(CHECK_CFLAGS) in the CFLAGS — upstream relies on
        # check.h living in the system default include dir. On OHOS/conan that
        # include path is not on the compiler's default search path, so
        # `make -C libdmapsharing` dies with `check.h file not found`.
        # Add $(CHECK_CFLAGS) to the library CFLAGS (upstream-consistent;
        # with a system check it expands to -I/usr/include and is harmless).
        # Patch the GENERATED Makefile.in (make consumes config.status's output
        # of it) AND the Makefile.am (source-of-truth provenance); the mtime
        # normalisation above keeps Makefile.in newer than Makefile.am so the
        # automake regen rule stays asleep.
        self._patch_check_cflags(src)
        # Fix the same "check.h file not found" for the upstream tests:
        # tests/unit-test.c includes <check.h>, but upstream tests/AM_CPPFLAGS
        # carries only the GDKPIXBUF/GEE/GLIB/GOBJECT/GSTREAMERAPP/GTHREAD/
        # GTK/IMAGEMAGICK/MDNS/SOUP CFLAGS, NOT $(CHECK_CFLAGS) — it relies on
        # check.h being in the compiler default include dir, which is not the
        # case on conan/OHOS (<check>/include). Insert $(CHECK_CFLAGS) into
        # tests/AM_CPPFLAGS too (harmless -I with a system check).
        self._patch_tests_check_cflags(src)
        # Normalise autotools bootstrap mtimes AFTER every patch rewrote
        # configure / Makefile.in / Makefile.am (see CRITICAL comment above).
        # This is the single point that guarantees the maintainer regen rules
        # sleep on the final patched tree; it must stay after all self._patch_*
        # source edits and before ./configure.
        self._normalize_bootstrap_timestamps(src)
        self.run(
            f"CONFIG_SHELL={shell} SHELL={shell} {shell} configure "
            + " ".join(self._configure_args()),
            cwd=src, env=env)
        # Build library (runs generate-test-suites -> *-suite.c/h + tests/unit-test.c).
        self.run("make -C libdmapsharing -j1", cwd=src, env=env)
        # Patch the generated tests/unit-test.c so a failing suite does NOT abort
        # the whole process (upstream run_suite() exits EXIT_FAILURE on the first
        # failing suite). Without this, a single failing suite prevents the
        # remaining suites from ever running, so the recipe could never report
        # full upstream coverage (the 45 START_TEST cases); each srunner_run_all
        # still runs every test in its suite, so no assertion is removed, no test
        # is skipped, and every failure is still printed in the Check summary
        # lines. This is the Check analog of ctest continuing after a failure.
        self._patch_unit_test_no_early_abort(src)
        # Build the upstream unit-test binary only (avoids the extra client/
        # server test programs which link optional, OHOS-unavailable modules).
        self.run("make -C tests unit-test -j1", cwd=src, env=env)
        # Run the upstream Check unit-test suite and emit evidence.
        self._run_upstream_unit_test(env)

    def _configure_args(self):
        args = [
            f"--prefix={self.package_folder}",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--enable-tests",
            "--with-mdns=avahi",
            "--disable-gtk-doc",
            "--disable-introspection",
        ]
        if not self.options.shared:
            args.extend(["--disable-shared", "--enable-static"])
        else:
            args.extend(["--enable-shared", "--disable-static"])
        # Bake "-L<la-staging>" into the configure-time LDFLAGS as a harmless
        # belt-and-suspenders fallback for the static libtool archive dependency
        # scan (see generate()). The primary mechanism is the avahi .pc shims'
        # Libs: = "-L<staging> -lavahi-*" (baked into MDNS_LIBS); this extra
        # LDFLAGS -L ensures make sees the staging dir no matter how the -L/-l
        # pairs are ordered, and staging also holds the real .a copies so plain
        # "-L<staging> -lavahi-*" resolves either way.
        ldflags = []
        staging = getattr(self, "_avahi_la_staging", None)
        if staging:
            ldflags.append(f"-L{staging}")
        # The avahi mdns publisher (dmap-mdns-publisher-avahi.c) calls _() via
        # <glib/gi18n.h>; the OHOS glib package's headers map gettext to the
        # glib-mangled symbol g_libintl_gettext, which lives in the libintl that
        # ships alongside glib (NOT in libglib-2.0 itself). Without it the
        # unit-test link fails with "undefined symbol: g_libintl_gettext"
        # (referenced by libdmapsharing_4_0_la-dmap-mdns-publisher-avahi.o).
        # Link "-L<glib libdir> -lintl" (libgtop-tools/2.41.3 verified pattern)
        # so g_libintl_gettext resolves across every link this configure's
        # Makefile LDFLAGS drives (library + unit-test + test_package).
        glib = self._glib_pkg()
        if glib and glib.package_folder:
            glib_lib = os.path.join(glib.package_folder, "lib")
            if os.path.isdir(glib_lib):
                ldflags.append(f"-L{glib_lib} -lintl")
        if ldflags:
            args.append("LDFLAGS=\"" + " ".join(ldflags) + "\"")
        return args

    def _normalize_bootstrap_timestamps(self, root):
        """Force the autotools bootstrap mtime hierarchy so GNU make's
        "maintainer" regeneration rules stay asleep.

        libdmapsharing's release tarball already contains pregenerated
        configure / aclocal.m4 / config.h.in / Makefile.in, so a build needs
        NO autotools toolchain. But if the pristine commit mtime ordering is
        lost during source materialisation (conan cache export -> copytree),
        GNU make sees e.g. configure.ac/aclocal.m4 newer than Makefile.in and
        re-runs the automake rule (`missing automake-1.18 --gnu`), which fails
        because OHOS hosts have no automake.

        Base the regen rules on the autotools dependency chain:
          source/control  (configure.ac, *.am, m4/*.m4, gtk-doc.make .make)
                          <- T0 (2000)
          aclocal.m4 (generated by aclocal from T0)         <- T1 (2001)
          generated       (configure, config.h.in, *.in)    <- T2 (2002)
        Any real fixed timestamp copys this ordering works; 200x values are
        chosen because the later configure outputs (real Makefile, config.status)
        are created in the current 20xx year and are therefore always newer,
        which also keeps 'config.status --recheck' asleep (no configure re-run).

        gtk-doc.make is critical: doc/Makefile.in's automake regen rule declares
        it as a prerequisite (''$(srcdir)/Makefile.in: $(srcdir)/Makefile.am
        $(top_srcdir)/gtk-doc.make $(am__configure_deps)''). Unless gtk-doc.make
        is pinned to the T0 source layer, its real (20xx) mtime stays NEWER
        than the pinned doc/Makefile.in (2002), so on `make install` the doc
        maintainer rule re-runs `automake-1.18 --gnu doc/Makefile` and fails on
        OHOS hosts that have no automake. Treating every '*.make' as T0 keeps
        that rule asleep alongside the others.
        """
        import datetime

        def _set_times(path, epoch):
            try:
                ts = datetime.datetime(epoch, 1, 1, 0, 0, 0).timestamp()
            except OSError:
                return
            try:
                os.utime(path, (ts, ts))
            except OSError:
                self.output.warning("could not set mtime on %s" % path)

        gens = ["Makefile.in", "config.h.in", "configure"]
        try:
            for dirpath, _dirs, files in os.walk(root):
                for fn in files:
                    p = os.path.join(dirpath, fn)
                    if fn.endswith(".m4") or fn == "configure.ac" \
                            or fn.endswith(".am") or fn.endswith(".make"):
                        _set_times(p, 2000)
                    elif fn == "aclocal.m4":
                        _set_times(p, 2001)
                    elif fn in gens or fn.endswith(".in"):
                        _set_times(p, 2002)
        except OSError:
            pass
        self.output.info("normalised autotools bootstrap mtimes "
                         "(T0 source / T1 aclocal.m4 / T2 generated)")

    def _patch_generated_configure(self, configure):
        with open(configure, "r", encoding="utf-8") as handle:
            text = handle.read()
        patched, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
        patched, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
        if n_mktemp == 0 and n_mkdir == 0:
            self.output.warning(
                "generated configure has no AS_TMPDIR 'umask 077' pattern; "
                "HMFS workaround not applied")
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info(
            "patched generated configure AS_TMPDIR: removed 'umask 077 && ' "
            f"(mktemp:{n_mktemp}, mkdir:{n_mkdir})")

    def _patch_check_cflags(self, src):
        """Add $(CHECK_CFLAGS) to libdmapsharing_4_0_la_CFLAGS.

        Upstream compiles its test-instrumented library sources (#include
        <check.h>, in libdmapsharing_4_0_la_SOURCES when --enable-tests) with
        a CFLAGS that lacks $(CHECK_CFLAGS) — it only puts $(CHECK_LIBS) in the
        LDFLAGS, relying on check.h being in the system default include dir.
        On conan, check.h lives in <check>/include (not on the default search
        path), so `make -C libdmapsharing` fails with `check.h file not found`.
        Insert `$(CHECK_CFLAGS)` into the library CFLAGS. With a system check
        holding headers in /usr/include the flag is harmless (-I/usr/include).
        Patch the GENERATED Makefile.in (which config.status turns into the
        Makefile make actually uses) AND the Makefile.am (provenance); the mtime
        normalisation runs earlier so Makefile.in stays newer than Makefile.am
        and the automake regen rule sleeps.
        """
        anchor = "\t$(GDKPIXBUF_CFLAGS) \\\n"
        add = "\t$(CHECK_CFLAGS) \\\n"
        for rel in ("Makefile.in", "Makefile.am"):
            path = os.path.join(src, "libdmapsharing", rel)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except OSError:
                self.output.warning("_patch_check_cflags: cannot read %s" % path)
                continue
            if add in text:
                self.output.info("_patch_check_cflags: %s already patched" % rel)
                continue
            if anchor not in text:
                self.output.warning(
                    "_patch_check_cflags: CFLAGS anchor not found in %s" % path)
                continue
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace(anchor, add + anchor, 1))
            self.output.info(
                "_patch_check_cflags: added $(CHECK_CFLAGS) to %s" % path)

    def _patch_tests_check_cflags(self, src):
        """Add $(CHECK_CFLAGS) to tests/AM_CPPFLAGS.

        tests/unit-test.c includes <check.h>, but upstream tests/Makefile.am's
        AM_CPPFLAGS carries only the GDKPIXBUF/GEE/GLIB/GOBJECT/GSTREAMERAPP/
        GTHREAD/GTK/IMAGEMAGICK/MDNS/SOUP CFLAGS, NOT $(CHECK_CFLAGS) — it
        relies on check.h being in the compiler default include dir. On
        conan/OHOS check.h lives in <check>/include (not on the default search
        path), so `make -C tests unit-test` fails with `check.h file not found`
        (the library CFLAGS were already fixed by _patch_check_cflags; the
        tests AM_CPPFLAGS were not). Insert $(CHECK_CFLAGS) as the last entry
        of AM_CPPFLAGS (right before the final $(SOUP_CFLAGS) line). With a
        system check (headers in /usr/include) the -I is harmless.
        Patch both the GENERATED Makefile.in (which config.status turns into
        the Makefile make uses) AND Makefile.am (provenance); the mtime
        normalisation keeps Makefile.in newer than Makefile.am so the automake
        regen rule sleeps. The compiler-command line build of the library
        already succeeded with $(CHECK_CFLAGS) resolved from check.pc in the
        generators folder, so the same flag is guaranteed to resolve here.
        """
        # Anchor on the unique two-line tail of AM_CPPFLAGS: the $(MDNS_CFLAGS)
        # continuation line immediately followed by the final $(SOUP_CFLAGS)
        # line (the last AM_CPPFLAGS entry has no trailing backslash). Both
        # Makefile variations are handled: Makefile.am has unprefixed lines,
        # Makefile.in has a conditional (@TESTS_ENABLED_TRUE@) prefix per line.
        pattern = re.compile(
            r"^((?:@\w+@)?\s*\$\(MDNS_CFLAGS\)\s*\\)\n"
            r"^((?:@\w+@)?\s*\$\(SOUP_CFLAGS\)\s*)$",
            re.M)
        already = re.compile(
            r"\(MDNS_CFLAGS\)\s*\\\n(?:@\w+@)?\s*\$\(CHECK_CFLAGS\)")
        for rel in ("Makefile.in", "Makefile.am"):
            path = os.path.join(src, "tests", rel)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except OSError:
                self.output.warning(
                    "_patch_tests_check_cflags: cannot read %s" % path)
                continue
            if already.search(text):
                self.output.info(
                    "_patch_tests_check_cflags: %s already patched" % rel)
                continue
            m = pattern.search(text)
            if not m:
                self.output.warning(
                    "_patch_tests_check_cflags: AM_CPPFLAGS anchor not found "
                    "in %s" % path)
                continue
            # Reuse the MDNS line's own prefix style for the inserted line so
            # Makefile.in (@TESTS_ENABLED_TRUE@) keeps each line prefixed.
            source = m.group(2)
            idx = source.find("$(")
            head = source[:idx] if idx != -1 else ""
            inserted = m.group(1) + "\n" + head + "$(CHECK_CFLAGS) \\\n" + source
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text[:m.start()] + inserted + text[m.end():])
            self.output.info(
                "_patch_tests_check_cflags: added $(CHECK_CFLAGS) to %s" % path)

    def _patch_unit_test_no_early_abort(self, src):
        """Remove the first-failing-suite early-exit from the generated
        tests/unit-test.c so every Check suite runs and reports.

        Upstream unit-test.c (machine-generated by ./generate-test-suites)
        contains a run_suite() that, after srunner_run_all(), calls
        exit(EXIT_FAILURE) when a suite has any failure. Because the suites run
        in a fixed order (av-connection, av-record, av-share, connection,
        md5, utils), a single failure in an early suite (e.g. _read_test in
        dmap-av-record.c, which calls mkstemp on the hardcoded /tmp path
        literal -- read-only erofs on OHOS) causes the process to abort before
        the remaining suites ever execute. The recipe would then only ever
        capture evidence for the first 10 of 45 START_TEST cases, understating
        upstream_test_total and leaving 35 tests without evidence.

        Patch: delete the `if (nf != 0) { exit (EXIT_FAILURE); }` block. This
        does NOT remove any assertion and does NOT skip any test: each
        srunner_run_all() still runs every test in its suite and still prints
        the per-suite 'N%: Checks: X, Failures: Y' summary, so every failure
        remains visible to the count parser. It is the Check analog of ctest
        continuing after one test fails, and is required to obtain full
        upstream coverage evidence (45 discovered). Patched at build time in
        the build tree only -- never committed to upstream source, no patches/.
        """
        path = os.path.join(src, "tests", "unit-test.c")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as ex:
            self.output.warning(
                "_patch_unit_test_no_early_abort: cannot read %s (%s)"
                % (path, ex))
            return
        pattern = re.compile(
            r"if \(nf != 0\) \{\s*exit \(EXIT_FAILURE\);\s*\}")
        patched, n = pattern.subn("", text)
        if n == 0:
            self.output.warning(
                "_patch_unit_test_no_early_abort: early-exit block not found "
                "in %s; leaving as-is" % path)
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)
        self.output.info(
            "_patch_unit_test_no_early_abort: removed %d early-exit block(s) "
            "from %s so all 6 Check suites run and report" % (n, path))

    def _run_upstream_unit_test(self, env):
        # The 6 Check suites total 45 cases. unit-test is (re)linked by
        # libtool. When libtool decides a wrapper is needed (need_relink=yes +
        # build_libtool_libs=yes, which is the case here: the static
        # libdmapsharing links against shared glib/soup/avahi/check), the REAL
        # ELF is always placed at tests/.libs/unit-test and a SHELL wrapper is
        # written at tests/unit-test that only sets up LD_LIBRARY_PATH before
        # exec-ing that ELF (ltmain.sh 2.5.4 func_mode_link:
        # link_command ... s%@OUTPUT@%$output_objdir/$outputname%g; then
        # func_emit_wrapper no > $output).
        #
        # Real-machine failure (hmbs-preflight 2026-09-28): the recipe used to
        # fall back to executing the libtool wrapper script via /bin/sh when
        # tests/.libs/unit-test was not found, and the OHOS /bin/sh rejected
        # the generated wrapper with "tests/unit-test[506]: syntax error:
        # unexpected ')'" (the wrapper is not parseable by that shell), which
        # then produced an empty unit-test.log and the "could not parse any
        # Check summary line" error.
        #
        # Fix: ALWAYS run the real ELF directly (never the shell wrapper), so
        # no shell must parse libtool's generated script and the shared
        # glib/soup/avahi/check runtimes are found via the LD_LIBRARY_PATH that
        # dmap_env already prepends (_prepend_runtime_libdirs). We detect the
        # ELF magic (\x7fELF) so a leftover wrapper script (leading shebang line,
        # not ELF) is never mistaken for a runnable binary.
        def _is_elf(path):
            try:
                with open(path, "rb") as handle:
                    return handle.read(4) == b"\x7fELF"
            except OSError:
                return False

        candidates = [
            os.path.join(self.source_folder, "tests", ".libs", "unit-test"),
            os.path.join(self.source_folder, "tests", ".libs", "lt-unit-test"),
            os.path.join(self.source_folder, "tests", "unit-test"),
        ]
        binary = next((p for p in candidates if _is_elf(p)), None)
        if binary is None:
            detail = []
            for p in candidates:
                d = os.path.dirname(p)
                if os.path.isdir(d):
                    try:
                        detail.append(f"{d}: " + ", ".join(sorted(os.listdir(d))))
                    except OSError as ex:
                        detail.append(f"{d}: <list failed: {ex}>")
                else:
                    detail.append(f"{d}: <no such dir>")
            raise ConanException(
                "upstream unit-test real ELF not found (libtool may have only "
                "written a shell wrapper, which OHOS /bin/sh cannot parse). "
                "Searched for an ELF at: " + "; ".join(candidates)
                + " | listing: " + " | ".join(detail))
        log = os.path.join(self.build_folder, "unit-test.log")
        try:
            self.run(
                f'{binary} > {log} 2>&1; rc=$?; cat {log}; exit $rc',
                env=env,
            )
        except ConanException:
            pass  # capture partial output below for accurate counts
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        # The Check framework prints one N%: Checks: X, Failures: Y, Errors: Z
        # summary line per srunner_run_all(). unit-test.c calls run_suite()
        # once per suite (6 suites, 45 tests total), so the log contains 6
        # summary lines — one per suite. Aggregate ALL of them (sum Checks =
        # total discovered/executed; sum Failures+Errors = total failed) so the
        # marker reflects the full upstream suite, not just the last suite's
        # line. libcheck total Checks = passed + failed + errors.
        total_checks = total_failures = total_errors = 0
        summary_lines = 0
        for line in text.splitlines():
            m = re.search(r"Checks:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)", line)
            if m:
                total_checks += int(m.group(1))
                total_failures += int(m.group(2))
                total_errors += int(m.group(3))
                summary_lines += 1
        if summary_lines == 0:
            raise ConanException(
                "could not parse any Check summary line from unit-test log; log head:\n"
                + text[:2000])
        discovered = total_checks
        executed = total_checks
        failed = total_failures + total_errors
        passed = executed - failed
        skipped = 0
        # Identity self-checks before emitting the marker (no arithmetic fudging).
        if passed + failed != executed or executed + skipped > discovered or executed > discovered:
            raise ConanException(
                f"check identity violated: discovered={discovered} executed={executed} "
                f"passed={passed} failed={failed} skipped={skipped}")
        # Attribute upstream failures to OHOS platform gaps by classifying each
        # deterministic 'file:line:F:...: Failed' failure line the Check
        # framework prints. All 13 real-machine failures are OHOS platform gaps
        # (no test-logic bug): 10 dmap-av-share cases abort at line 1032 because
        # _build_share_test() stats /etc/services & /etc/group which do not
        # exist on OHOS; 2 _serve_publish* cases fail because dmap_share_publish
        # needs a running avahi mDNS daemon; 1 _read_test (dmap-av-record.c)
        # fails because mkstemp('/tmp/...') cannot write the read-only /tmp
        # erofs. Counts come only from these failure-line signatures (no
        # arithmetic on totals), so the gap sum equals declared_total - passed.
        gaps = []

        def _count(pattern):
            return len(re.findall(pattern, text))

        # 10 x _build_share_test stat() of absent /etc/services + /etc/group.
        no_etc = _count(
            r"dmap-av-share\.c:1032:F:[^:]+:[^:]+:\d+: Failed")
        if no_etc > 0:
            gaps.append({
                "count": no_etc,
                "category": "ohos_feature",
                "detail": "dmap-av-share _build_share_test() stats /etc/services "
                          "and /etc/group (ck_abort at dmap-av-share.c:1032); "
                          "both files are absent on OHOS, so the 10 dependent "
                          "av-share cases abort before exercising their logic",
                "evidence": "unit-test.log: dmap-av-share.c:1032:F:<test>: Failed (x%d)"
                            % no_etc,
            })
        # 2 x mDNS publish (no running avahi daemon on OHOS). These fail with a
        # ck_assert(ok) on dmap_share_publish, so the Check line ends in
        # "Assertion 'ok' failed" rather than ": Failed".
        mds = _count(
            r"dmap-av-share\.c:(?:1153|1193):F:_serve_publish[^:\n]*:")
        if mds > 0:
            gaps.append({
                "count": mds,
                "category": "ohos_feature",
                "detail": "_serve_publish_test/_serve_publish_collision_test call "
                          "dmap_share_publish(), which needs a running avahi "
                          "mDNS daemon ('Unable to initialize mDNS: Daemon not "
                          "running'); none runs on OHOS, so publish returns "
                          "false and ck_assert(ok) at dmap-av-share.c:1153/1193 fails",
                "evidence": "unit-test.log: dmap-av-share.c:1153/1193:F:_serve_publish*: "
                            "Assertion 'ok' failed; 'Unable to initialize mDNS: "
                            "Daemon not running'",
            })
        # 1 x _read_test mkstemp on read-only /tmp.
        tmp_fail = _count(
            r"dmap-av-record\.c:\d+:F:_read_test:_read_test:\d+: Failed")
        if tmp_fail > 0:
            gaps.append({
                "count": tmp_fail,
                "category": "ohos_feature",
                "detail": "_read_test calls mkstemp('/tmp/libdmapsharing-test-XXXXXX') "
                          "on the read-only /tmp erofs mount; mkstemp fails -> "
                          "ck_abort (TMPDIR redirect cannot apply to the literal /tmp)",
                "evidence": "unit-test.log: dmap-av-record.c:281:F:_read_test: Failed",
            })
        # Any residual failure lines that we could not attribute to a known
        # platform gap are reported transparently as test_failure rather than
        # being silently dropped or mis-attributed.
        known = no_etc + mds + tmp_fail
        if failed > known:
            gaps.append({
                "count": failed - known,
                "category": "test_failure",
                "detail": "unclassified Check failure lines not matching a known "
                          "OHOS/AVAHI/tmp platform signature; see unit-test.log "
                          "for the exact failing case(s)",
                "evidence": "unit-test.log residual '...:F:...: Failed' lines",
            })
        upstream = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "check (libcheck unit-test)",
            "command": f"{binary}",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if gaps:
            upstream["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if failed > 0:
            self.output.warning(
                f"upstream unit-test: {passed} passed / {failed} failed of {executed}; "
                "see unit-test.log for per-suite detail")

    # ------------------------------------------------------------------ #
    # helpers (patterns follow avahi-glib / libgepub / libsoup3 recipes)   #
    # ------------------------------------------------------------------ #

    def _hmbs_writable_tmpdir(self):
        """Pick a truly writable per-task tmpdir (HMBS readonly-/tmp fix).

        HMBS preflight/CI hosts mount /tmp read-only (erofs), so the C
        compiler's conftest executables (AC_PROG_CC) and configure's
        AS_TMPDIR mktemp dir fail to be created. HMBS injects a writable
        per-task tmpdir; discover it and verify with a real write probe
        (HMDFS ignores chmod/os.access, so permission probing is not
        reliable). Priority (libsieve/libecoli precedent): HMBS_TMPDIR >
        HMBS_PLATFORM_CAPABILITIES.tmpdir > TMPDIR/TMP/TEMP (non-/tmp) >
        HMBS_AUTOCONF_MKTEMP_FALLBACK > ~/tmp > build_folder/.tmp.
        Only the temp root is redirected; no test is skipped or removed.
        """
        cands = []
        v = os.environ.get("HMBS_TMPDIR")
        if v:
            cands.append(v)
        cap = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                cands.append(json.loads(cap).get("tmpdir", ""))
            except Exception:
                pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            v = os.environ.get(k)
            if v and v != "/tmp":
                cands.append(v)
        v = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if v:
            cands.append(v)
        try:
            cands.append(os.path.join(os.path.expanduser("~"), "tmp"))
        except Exception:
            pass
        try:
            cands.append(os.path.join(self.build_folder, ".tmp"))
        except Exception:
            pass
        for c in cands:
            if not c:
                continue
            try:
                os.makedirs(c, exist_ok=True)
                import tempfile
                fd, probe = tempfile.mkstemp(dir=c, prefix=".hmbs-probe-")
            except Exception:
                continue
            try:
                os.close(fd)
                with open(probe, "w") as _pf:
                    _pf.write("ok")
            except Exception:
                continue
            try:
                os.remove(probe)
            except OSError:
                pass
            return c
        return None

    def _glib_pkg(self):
        """glib is declared in requirements() as an OVERRIDE (to resolve the
        avahi-glib glib/2.84.0.1 vs libsoup3 glib/2.84.0.1.1 exact-pin
        conflict), so it does NOT appear in this recipe's self.dependencies
        as a direct edge. It is however a real transitive node in the graph
        (libsoup3-r3 requires glib/2.84.0.1.1 directly; avahi-glib also
        requires glib). A fixed two-hop lookup through one specific parent
        (libsoup3/avahi-glib -> glib) proved unreliable: across conan 2.x
        the OVERRIDE edge is stripped from the declaring recipe's
        dependency view, and the `dependencies` attribute of a child
        ConanFileInterface is not guaranteed to expose the overridden
        package either, so the lookup returned None and configure then
        failed with "Must have glib-2.0 installed" (no glib-2.0.pc shim was
        generated).

        Robust fix: perform an explicit breadth-first walk of the ENTIRE
        reachable dependency graph and return the first node whose package
        name is glib and that has a non-empty package_folder. glib is
        guaranteed to be present and built (it is a hard requirement of the
        libsoup3-r3 chain), so this finds it at whatever depth it actually
        appears regardless of the override stripping. Returns the glib
        ConanFileInterface or None (callers must guard)."""
        from collections import deque

        def _name(node):
            ref = getattr(node, "ref", None)
            return getattr(ref, "name", None)

        def _key(node):
            return str(getattr(node, "ref", None))

        seen = set()
        seen_names = set()
        queue = deque()
        for dep in self.dependencies.values():
            if dep is not None:
                queue.append(dep)
        while queue:
            node = queue.popleft()
            k = _key(node)
            if k in seen:
                continue
            seen.add(k)
            seen_names.add(_name(node))
            if _name(node) == "glib":
                folder = getattr(node, "package_folder", None)
                if folder:
                    return node
            subdeps = getattr(node, "dependencies", None)
            if subdeps:
                for sub in subdeps.values():
                    if sub is not None and _key(sub) not in seen:
                        queue.append(sub)
        # Record what the walk actually saw so callers failing on a missing
        # glib can emit a precise diagnostic instead of a generic guess.
        self._glib_bfs_seen = sorted(n for n in seen_names if n)
        return None

    def _find_pkg_by_name(self, target):
        """Generic breadth-first lookup of a reachable dependency node by
        package name, returning the ConanFileInterface with a non-empty
        package_folder or None. dbus is NOT a direct requirement of this
        recipe (it is pulled in transitively by avahi-glib,
        self.requires('dbus/1.14.10')), so `self.dependencies['dbus']` is not
        reliable; the same full-graph walk _glib_pkg() uses finds it at
        whatever depth it actually appears."""
        from collections import deque

        def _name(node):
            ref = getattr(node, "ref", None)
            return getattr(ref, "name", None)

        def _key(node):
            return str(getattr(node, "ref", None))

        seen = set()
        queue = deque()
        for dep in self.dependencies.values():
            if dep is not None:
                queue.append(dep)
        while queue:
            node = queue.popleft()
            k = _key(node)
            if k in seen:
                continue
            seen.add(k)
            if _name(node) == target:
                folder = getattr(node, "package_folder", None)
                if folder:
                    return node
            subdeps = getattr(node, "dependencies", None)
            if subdeps:
                for sub in subdeps.values():
                    if sub is not None and _key(sub) not in seen:
                        queue.append(sub)
        self.output.warning(
            f"_find_pkg_by_name: package '{target}' not reachable in graph")
        return None

    def _dbus_pkg(self):
        """Reach the dbus package (transitive dep via avahi-glib) that the
        libavahi-client static archive links against. Returns None if it is
        not in the graph (callers must guard)."""
        return self._find_pkg_by_name("dbus")

    def _fix_glib_pc_files(self):
        """Make glib-2.0.pc (and gobject/gio/gmodule/gthread) findable for
        configure's PKG_CHECK_MODULES(glib-2.0 >= 2.66).

        glib is declared as an OVERRIDE requirement (to resolve the avahi-glib
        glib/2.84.0.1 vs libsoup3 glib/2.84.0.1.1 exact-pin conflict), so conan
        strips it from this recipe's self.dependencies and PkgConfigDeps does
        NOT generate a glib-2.0.pc for it. We therefore must supply the .pc
        ourselves.

        PREVIOUS APPROACH (rejected after a real preflight that still reached
        "glib-2.0 >= 2.66... no"): writing the shims into a SEPARATE
        glib-pc-fix dir in the build folder and prepending that dir to
        PKG_CONFIG_PATH via the custom dmap_env script. The preflight proved
        that the dir added through dmap_env was NOT searched by pkg-config,
        while the generators_folder (serving check.pc for the earlier
        PKG_CHECK_MODULES 'check >= 0.9.4') WAS searched. So the reliable
        PKG_CONFIG_PATH entry is the PkgConfigDeps generators folder.

        THIS APPROACH: write the hand-rolled core shims directly into
        self.generators_folder — the same folder PkgConfigDeps uses for the
        check/libusoup3/avahi-glib .pc and which configure demonstrably
        resolves from (check >= 0.9.4 passed before glib was reached).
        Avoiding a separate dir removes the fragile dmap_env dependence.
        core shims are deterministic from glib's package layout; glib's own
        meson-installed .pc are NOT used to overwrite the core shims (they
        could be arch/path-incomplete), but extra non-core .pc are copied in
        prefix-fixed as a bonus. Returns self.generators_folder."""
        glib_pkg = self._glib_pkg()
        if not glib_pkg:
            # Fail loudly with the actual reachable graph so the next preflight
            # gives definitive evidence. Without glib-2.0.pc, configure dies at
            # "Must have glib-2.0 installed"; a clear error here beats silence.
            seen = getattr(self, "_glib_bfs_seen", None) or []
            raise ConanException(
                "glib package not reachable in dependency graph (BFS saw: %s, "
                "direct deps: %s); cannot generate glib-2.0.pc shim"
                % (", ".join(seen) if seen else "<none>",
                   ", ".join(str(getattr(d, "ref", d)) for d in self.dependencies.values())))
        glib_pkg = glib_pkg.package_folder
        target_dir = self.generators_folder
        os.makedirs(target_dir, exist_ok=True)
        _write = self._write_pc_shim
        gver = "2.84.0"
        _write(target_dir, "glib-2.0", gver, "GLib Utility Library",
               requires="", libs="-lglib-2.0", ginc=True, glib_pkg=glib_pkg)
        _write(target_dir, "gobject-2.0", gver, "GLib Type, Object and class system",
               requires="glib-2.0", libs="-lgobject-2.0", ginc=True, glib_pkg=glib_pkg)
        _write(target_dir, "gthread-2.0", gver, "GLib Threads",
               requires="glib-2.0", libs="-lgthread-2.0", ginc=True, glib_pkg=glib_pkg)
        _write(target_dir, "gmodule-2.0", gver, "Dynamic module loader for GLib",
               requires="glib-2.0", libs="-lgmodule-2.0", ginc=True, glib_pkg=glib_pkg)
        _write(target_dir, "gio-2.0", gver, "GLib Input, Output and Streaming Library",
               requires="glib-2.0 gobject-2.0 gmodule-2.0",
               libs="-lgio-2.0 -lgobject-2.0 -lglib-2.0",
               ginc=True, glib_pkg=glib_pkg, gio_unix=True)
        # Bonus: copy glib's extra installed .pc (gio-unix-2.0, ...) that the
        # hand-rolled set does not cover, but NEVER overwrite a core shim.
        core = {"glib-2.0", "gobject-2.0", "gthread-2.0", "gmodule-2.0", "gio-2.0"}
        src_dir = os.path.join(glib_pkg, "lib", "pkgconfig")
        copied = 0
        if os.path.isdir(src_dir):
            for pc in os.listdir(src_dir):
                if not pc.endswith(".pc") or pc[:-3] in core:
                    continue
                target = os.path.join(target_dir, pc)
                with open(os.path.join(src_dir, pc), "r",
                          encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                with open(target, "w", encoding="utf-8") as fh:
                    fh.write(text)
                copied += 1
        self.output.info(
            "glib .pc shims written into generators_folder=%s (5 core shims"
            " + %d extra glib .pc copied)" % (target_dir, copied))
        # Integrity: glib-2.0.pc MUST exist after this.
        if not os.path.isfile(os.path.join(target_dir, "glib-2.0.pc")):
            raise ConanException("failed to produce glib-2.0.pc in %s" % target_dir)
        return target_dir

    def _write_pc_shim(self, fix_dir, name, version, desc, requires, libs,
                       glib_pkg, ginc=False, gio_unix=False):
        """Write a minimal, self-complete .pc for a package whose prefix is the
        real package_folder (same shape as the avahi-client shim)."""
        cflags = "-I${includedir}/glib-2.0 -I${libdir}/glib-2.0/include"
        if gio_unix:
            cflags += " -I${includedir}/gio-unix-2.0"
        req = ("Requires: " + requires) if requires else ""
        path = os.path.join(fix_dir, f"{name}.pc")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("# hand-rolled shim (glib is an OVERRIDE dep, so PkgConfigDeps\n")
            fh.write("# does not emit it; this guarantees configure finds %s)\n" % name)
            fh.write("prefix=%s\n" % glib_pkg)
            fh.write("exec_prefix=${prefix}\n")
            fh.write("libdir=${prefix}/lib\n")
            fh.write("includedir=${prefix}/include\n")
            fh.write("Name: %s\n" % name)
            fh.write("Description: %s\n" % desc)
            fh.write("Version: %s\n" % version)
            if req:
                fh.write(req + "\n")
            fh.write("Libs: -L${libdir} %s\n" % libs)
            fh.write("Cflags: %s\n" % cflags)

    def _fix_avahi_la(self):
        """Make the static libtool link of libdmapsharing-4.0.la succeed by
        staging REAL avahi .a archives + their .la shims, and pointing the
        avahi .pc shims at that staging dir.

        libdmapsharing is built STATIC by libtool (--disable-shared). libtool's
        static-archive dependency scan reads each dependent library's .la
        (libtool archive) via grep/sed to record dependency_libs. For the avahi
        libs it derives the .la path from the -L that accompanies -lavahi-* on
        the link line; the avahi-glib conan package ships ONLY plain .a (no
        .la), so that read fails:

            grep: .../p/lib/libavahi-client.la: No such file or directory
            sed: can't read .../p/lib/libavahi-client.la: No such file or dir
            libtool: error: '.../libavahi-client.la' is not a valid libtool archive

        ROUND-1 (staging .la shims + `-L<staging>` only in configure LDFLAGS)
        was verified on the real device and did NOT fix the error: libtool did
        not use the extra LDFLAGS -L to derive the .la path, so the shims were
        never reached. ROUND-2 (this): put BOTH the real avahi .a archives and
        the .la shims in one staging dir, and force the avahi .pc shims'
        `Libs:` to `-L<staging> -lavahi-*` (overriding avahi-glib.pc too), so
        configure bakes `-L<staging> -lavahi-*` into AVAHI_LIBS->MDNS_LIBS in
        the Makefile. Then (a) configure's PKG_CHECK_MODULES link test finds the
        real .a in staging, and (b) libtool's static scan derives
        `<staging>/libavahi-client.la` from the -L that accompanies -lavahi-*,
        finds the shim, and its dependency_libs (`-L<staging> -lavahi-*`) also
        resolve inside staging -- fully self-contained, no reliance on LDFLAGS
        propagation.
        """
        avahi = self.dependencies["avahi-glib"]
        pkg = avahi.package_folder
        pkg_lib = os.path.join(pkg, "lib")
        staging = os.path.join(self.build_folder, "ohos-avahi-la")
        os.makedirs(staging, exist_ok=True)
        self._avahi_la_staging = staging

        bases = ["avahi-common", "avahi-client", "avahi-glib", "avahi-gobject"]
        # 1) Copy the REAL avahi static archives into staging so -L<staging>
        #    resolves the symbols for configure's link test and the real link.
        copied = 0
        for b in bases:
            real = os.path.join(pkg_lib, f"lib{b}.a")
            if os.path.isfile(real):
                shutil.copy2(real, os.path.join(staging, f"lib{b}.a"))
                copied += 1
            elif os.path.isfile(os.path.join(pkg_lib, f"lib{b}.so")):
                # fall back to shared object if present
                shutil.copy2(os.path.join(pkg_lib, f"lib{b}.so"),
                             os.path.join(staging, f"lib{b}.so"))
                copied += 1

        # 2) .la shims referencing only -L<staging> -lavahi-* (all resolvable
        #    inside staging; no glib/dbus -l so no extra .la lookups leak out).
        chain = {
            "avahi-common": [],
            "avahi-client": ["avahi-common"],
            "avahi-glib": ["avahi-client", "avahi-common"],
            "avahi-gobject": ["avahi-glib", "avahi-client", "avahi-common"],
        }
        # libavahi-client.a talks to the avahi daemon over D-Bus, so its real
        # link needs -ldbus-1 (dbus/1.14.10 pulled in transitively by
        # avahi-glib). Without it the unit-test link fails with hundreds of
        # "undefined symbol: dbus_*" errors (avahi_client_new / filter_func /
        # dbus-watch-glue ... all in libavahi-client.a). Every lib that links
        # avahi-client (client itself, glib, gobject) must carry the dbus flag
        # on its dependency_libs so libtool places it after the archive on the
        # link line in the correct (deps after user) order.
        dbus_pkg = self._dbus_pkg()
        if dbus_pkg and dbus_pkg.package_folder:
            dbus_lib = os.path.join(dbus_pkg.package_folder, "lib")
            dbus_flag = f"-L{dbus_lib} -ldbus-1" if os.path.isdir(dbus_lib) else "-ldbus-1"
            self.output.info(
                f"avahi .la shims: adding dbus link flag '{dbus_flag}'")
        else:
            dbus_flag = None
        dbus_required = {
            "avahi-common": False,
            "avahi-client": True,
            "avahi-glib": True,
            "avahi-gobject": True,
        }
        for b in bases:
            # chain[b] holds full lib names already including the 'avahi-'
            # prefix (e.g. 'avahi-common', 'avahi-client'); the linker flag is
            # -l<name> = -lavahi-common, NOT "-lavahi-" + name (which would
            # double the prefix to the nonexistent -lavahi-avahi-common /
            # -lavahi-avahi-client that broke the tests link).
            deps = [f"-l{d}" for d in chain[b] or []]
            if dbus_flag and dbus_required.get(b):
                deps.append(dbus_flag)
            dl = " ".join(["-L%s" % staging] + deps)
            with open(os.path.join(staging, f"lib{b}.la"),
                      "w", encoding="utf-8", newline="\n") as fh:
                # libtool's func_lalib_unsafe_p (ltmain.sh) only accepts a .la
                # archive if one of the FIRST 4 LINES matches the case glob
                # `# Generated by <PACKAGE>*` where PACKAGE is the literal
                # string used by libtool ('libtool'). The round-2 shim used
                # `# Generated by libdmapsharing ...`, which does NOT begin
                # with `# Generated by libtool`, so libtool rejected it with
                # "is not a valid libtool archive" at CCLD even though the
                # -L<staging> path was correctly derived. Line 1 must be the
                # exact libtool magic marker (same text libtool writes into
                # every .la it creates).
                fh.write("# lib{0}.la - a libtool library file\n".format(b))
                fh.write("# Generated by libtool (shim for avahi-glib, which ships no .la)\n")
                fh.write("dlname=''\n")
                fh.write("library_names=''\n")
                fh.write("name='lib{0}.la'\n".format(b))
                fh.write("old_library='lib{0}.a'\n".format(b))
                fh.write("dependency_libs=' {0}'\n".format(dl))
                fh.write("current=0\nage=0\nrevision=0\n")
                fh.write("installed=yes\nshouldnotlink=no\n")
                fh.write("libdir='{0}'\n".format(staging))
        # 3) avahi .pc shims (incl. override of PkgConfigDeps' avahi-glib.pc)
        #    whose Libs: = -L<staging> -lavahi-* so configure bakes the correct
        #    -L into MDNS_LIBS / AVAHI_LIBS.
        pc_libs = {
            "avahi-common": ["-lavahi-common"],
            "avahi-client": ["-lavahi-client", "-lavahi-common"],
            "avahi-glib": ["-lavahi-glib", "-lavahi-client", "-lavahi-common"],
            "avahi-gobject": ["-lavahi-gobject", "-lavahi-glib",
                              "-lavahi-client", "-lavahi-common"],
        }
        shim_dir = self.generators_folder
        os.makedirs(shim_dir, exist_ok=True)
        for b in bases:
            libs = "-L%s %s" % (staging, " ".join(pc_libs[b]))
            with open(os.path.join(shim_dir, f"{b}.pc"),
                      "w", encoding="utf-8", newline="\n") as fh:
                fh.write("prefix={0}\n".format(pkg))
                fh.write("exec_prefix=${prefix}\n")
                fh.write("libdir={0}\n".format(pkg_lib))
                fh.write("includedir={0}/include\n".format(pkg))
                fh.write("Name: {0}\n".format(b))
                fh.write("Description: Avahi {0} library\n".format(b))
                fh.write("Version: 0.9\n")
                fh.write("Libs: {0}\n".format(libs))
                fh.write("Cflags: -I${includedir}\n")

        self.output.info(
            "libdmapsharing: staged %d avahi .a + .la in %s and pointed "
            "avahi .pc Libs at `-L%s -lavahi-*`" % (copied, staging, staging))
        return staging

    def _stage_glib_python_tools(self):
        """Native launchers for glib's python3 scripts (glib-mkenums) so make
        can run them on HMFS (shebang exec rejected)."""
        glib_pkg = self._glib_pkg()
        if not glib_pkg:
            self.output.warning("glib not reachable; skipping python tool launchers")
            return self.build_folder  # empty dir, harmless on PATH
        tools_dir = os.path.join(self.build_folder, ".glib-tools")
        scripts_dir = os.path.join(tools_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException("C compiler not found in tools.build:compiler_executables")
        # Use the conan interpreter (guaranteed present) to run glib's python
        # helper scripts (avahi-glib precedent).
        python = os.path.realpath(sys.executable)
        for name in ("glib-mkenums", "glib-genmarshal"):
            source = os.path.join(glib_bin, name)
            if not os.path.isfile(source):
                continue
            script = os.path.join(scripts_dir, name)
            shutil.copy2(source, script)
            os.chmod(script, 0o755)
            if str(self.settings.os) == "OHOS" and python:
                launcher = os.path.join(tools_dir, name)
                self._build_python_tool_launcher(launcher, script, python, compiler)
            else:
                shutil.copy2(script, os.path.join(tools_dir, name))
                os.chmod(os.path.join(tools_dir, name), 0o755)
        return tools_dir

    def _build_python_tool_launcher(self, launcher, script, python, compiler):
        source = f"{launcher}-runner.c"
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <unistd.h>\n"
                f"static const char *python_path = {json.dumps(python)};\n"
                f"static const char *script_path = {json.dumps(script)};\n"
                "int main(int argc, char **argv) {\n"
                "    char **args = (char **)calloc((size_t)argc + 2, sizeof(char *));\n"
                "    if (!args) return 126;\n"
                "    args[0] = (char *)python_path;\n"
                "    args[1] = (char *)script_path;\n"
                "    for (int i = 1; i < argc; ++i) args[i + 1] = argv[i];\n"
                "    args[argc + 1] = NULL;\n"
                "    execv(python_path, args);\n"
                "    perror(\"execv\");\n"
                "    return 127;\n"
                "}\n"
            )
        self.run(f'"{compiler}" "{source}" -o "{launcher}"')
        os.chmod(launcher, 0o755)

    def _prepend_runtime_libdirs(self, env):
        for name in ("glib", "libsoup3", "avahi-glib", "check"):
            dep = self._glib_pkg() if name == "glib" else self.dependencies.get(name)
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                env.prepend_path("LD_LIBRARY_PATH", libdir)

    def _write_install_shim(self):
        """HMBS install shim only accepts single-file two-arg calls; automake
        batch header installs (install -c -m 644 f1..fN dir/) exit 64. Write a
        cp/mkdir shim and redirect the Makefile INSTALL variable to it."""
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
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
        except Exception:  # noqa: BLE001
            os.close(fd)
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        for _root, _, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(f"{_indent}INSTALL = {shim_install}\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))

    def package(self):
        env = ["conanbuild", "conanrun", "dmap_env"]
        shim = self._write_install_shim()
        self._redirect_install_to_shim(self.source_folder, shim)
        self.run("make install", cwd=self.source_folder, env=env)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Static by default; the shared glib/soup/avahi runtimes are the single
        # GObject copy. Public pkg-config name is libdmapsharing-4.0.
        self.cpp_info.libs = ["dmapsharing-4.0"]
        self.cpp_info.includedirs = ["include", "include/libdmapsharing-4.0"]
        self.cpp_info.set_property("pkg_config_name", "libdmapsharing-4.0")
        self.cpp_info.set_property("cmake_file_name", "libdmapsharing-4.0")
        self.cpp_info.set_property("cmake_target_name", "libdmapsharing-4.0::libdmapsharing-4.0")
        # libdmapsharing is static: consumers must also link the shared glib
        # (single-copy runtime), libsoup3, avahi and check. Forward them via
        # cpp_info.requires so CMakeDeps/PkgConfigDeps pull the transitive
        # link/include info (conan 2 static-lib dep forwarding). glib is NOT
        # listed here: it is an override requirement (not a real direct dep),
        # and conan 2 rejects override deps in cpp_info.requires ("not a
        # direct requirement"); glib's link info is forwarded to consumers via
        # libsoup3-r3 (which adds glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/
        # gthread-2.0 to its own cpp_info.libs) and avahi-glib's
        # transitive_libs, so it still reaches the link line.
        self.cpp_info.requires = [
            "libsoup3::libsoup3", "avahi-glib::avahi-glib", "check::check",
        ]
        # Public headers include glib/gobject/gio and libsoup headers; expose
        # the transitive include dirs (conan 2.29 CMakeDeps empty-data caveat,
        # libsoup3/libgepub pattern) so consumers can compile. Prefer each
        # dependency's OWN published include layout (e.g. libsoup3 declares
        # include/libsoup-3.0 so <libsoup/soup.h> resolves) plus glib's extra
        # subdirs. This guarantees the consumer sees the same -I paths the
        # dependency publishes even if CMakeDeps transitive propagation of the
        # static lib's cpp_info.requires does not reach it (real-machine
        # test_package compile failed with "libsoup/soup.h file not found").
        for name in ("glib", "libsoup3", "avahi-glib", "check"):
            dep = self._glib_pkg() if name == "glib" else self.dependencies.get(name)
            if not (dep and dep.package_folder):
                continue
            subs = ["include"]
            try:
                own = list(getattr(dep.cpp_info, "includedirs", None) or [])
            except Exception:
                own = []
            for sub in own:
                if sub and not sub.startswith("/"):
                    subs.append(sub)
            subs += ["include/glib-2.0", "lib/glib-2.0/include"]
            for sub in subs:
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in self.cpp_info.includedirs:
                    self.cpp_info.includedirs.append(d)
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                self.cpp_info.libdirs.append(libdir)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
