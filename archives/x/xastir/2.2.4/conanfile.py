#!/usr/bin/env python3
"""Conan recipe — xastir 2.2.4 (APRS map client, X11/Motif).

xastir is the X Amateur Station Tracking and Information Reporting client:
an autotools-built C application (Xt/Motif GUI) that renders APRS maps from
GeoTIFF/shapefile/TIGER data, queries online maps via libcurl, and talks to
TNCs via the AX.25 stack.  It links a large optional-feature matrix that
configure probes one by one.

OHOS PC (aarch64, os=OHOS) adaptation notes:

Upstream artifact / bootstrap
  The official 2.2.4 release is the GitHub ``Release-2.2.4`` tag tarball and
  it ships NO pre-generated configure: the tree must be bootstrapped with
  aclocal + autoheader + autoconf + automake -a -c (upstream ``bootstrap.sh``
  order).  xastir has no LT_INIT — it uses plain AC_PROG_RANLIB — so no
  libtool/libtoolize is involved at all.

Tool sources on the OHOS worker
  autoconf/autoheader/autom4te 2.72 live in ``/data/service/hnp/bin`` and can
  be executed directly (their perl shebangs point at the working hnp perl);
  aclocal/automake come from the conan ``automake/1.19`` package, whose
  scripts are invoked through explicit interpreters (``sh <wrapper>`` /
  ``perl <pkg>/.aclocal-real``) because script execve fails under HMDFS
  (E232-class).  ``ACLOCAL_AMFLAGS = -I m4`` references an m4/ directory that
  does not exist in the release tree, so one is created before aclocal.

configure under HMDFS
  ``configure`` is executed through an explicit ``sh`` interpreter (E232).
  Cross mode (``--host=aarch64-linux-ohos``) makes autoconf skip its
  run-tests, and ``ac_cv_func_malloc_0_nonnull=yes`` avoids the pessimistic
  ``rpl_malloc`` substitution of AC_FUNC_MALLOC (twclock precedent).

ImageMagick / GraphicsMagick
  xastir's ``XASTIR_CHECK_IMAGEMAGICK`` rejects ``MagickLibVersion >
  0x0700``; the registry's only magick build, imagemagick/7.1.2.29, reports
  0x712 ("way too new"), and GraphicsMagick is not published at all, so both
  are disabled deterministically with --without-graphicsmagick
  --without-imagemagick.  Raster map import remains covered by the
  GeoTIFF/TIFF + shapelib + pcre2 + proj path; only the generic
  "any format via magick" import is unavailable.

Berkeley DB map cache
  ``XASTIR_BERKELEY_DB_CHK_LIB`` runs ``AC_SEARCH_LIBS([db_create],
  [db-18.1 db-18 ... db-5.0 db50])`` — none of those names matches the
  ``libdb.a`` the berkeley-db/4.8.30 package ships.  Putting ``-ldb`` into
  the toolchain LIBS lets the search's "none required" branch succeed (same
  mechanism twclock/libxpm rely on for other probes), so USE_MAP_CACHE is
  defined and map_cache.c compiles against the static archive.

Dependency graph / zlib force
  curl/8.15.0 pins zlib/1.3.1.1 and libax25/0.0.12-rc5 pins zlib/1.3.1; the
  top-level ``zlib/1.3.1.1`` (force=True) requirement is what makes the
  graph converge, and under that graph the published binary tracks of
  libxext/6.4.0.1 and libxpm/3.5.17 do not exist (their libx11/zlib tracks
  differ), so conan rebuilds them from source where a cache entry is absent
  — the same mechanism twclock's CI already exercised for
  libxext eab79208.

Broken symlink nodes in registry packages (E050)
  On this host, tar-extracted symlink nodes in several registry packages
  (libtiff, libjpeg-turbo, libwebp, zstd, libxau, libxdmcp) cannot even be
  stat()ed.  ``-ltiff`` therefore cannot resolve against libtiff.so, and the
  runtime loader cannot satisfy DT_NEEDED sonames like libtiff.so.6 or
  libXau.so.6 from the package dirs.  The recipe builds a private
  "linker view" of the whole host-dependency closure with real-file copies
  (reconstructing broken node names from the highest-version real sibling),
  and keeps it first on -L (via LDFLAGS) and on LD_LIBRARY_PATH (needed by
  ``make check`` test binaries and the autotest driver, which genuinely
  execute on the build host).  On a worker whose symlinks work the view is
  an identical copy of the same files — harmless by construction.

Headless reality
  No X server exists on the target: any run of ``xastir`` itself stops at
  XtVaOpenApplication with the real Xt "Can't open display" error and a
  non-zero exit — the twclock consumer-test precedent uses exactly that
  (plus the ELF DT_NEEDED walk) as the runtime-closure evidence.  The
  callpass helper (pure C, callsign → APRS passcode, no X) provides the
  positive execution path; see test_package/.
"""

import os
import re
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XastirConan(ConanFile):
    name = "xastir"
    version = "2.2.4"
    description = (
        "X Amateur Station Tracking and Information Reporting (APRS client)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://xastir.org"
    url = "https://github.com/Xastir/Xastir/archive/refs/tags/Release-2.2.4.tar.gz"
    topics = ("aprs", "ham-radio", "x11", "motif", "mapping")

    # twclock/dinotrace precedent: an application recipe declares settings
    # (no options of its own, no shipped linkable library).
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: accept both Linux and OHOS, never `== "Linux"` only.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xastir supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # ---- GUI stack ------------------------------------------------
        # Motif (libXm.so.4 + <Xm/*.h>) is the widget toolkit; it carries
        # libxext/libx11/libxt on its forced libx11/1.8.13 track.
        self.requires("motif/2.3.8", transitive_headers=True, transitive_libs=True)
        # xastir itself links -lXt -lXext -lXpm (see configure.ac).
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        # xorgproto owns <X11/X.h>, <X11/Xfuncproto.h> etc.
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # ---- map / vector stack ---------------------------------------
        # libgeotiff pulls libtiff + proj transitively; xtiffio.h is a
        # public xastir include (AC_CHECK_HEADER(xtiffio.h)).
        self.requires("libgeotiff/1.7.4", transitive_headers=True, transitive_libs=True)
        self.requires("shapelib/1.5.0", transitive_headers=True, transitive_libs=True)
        self.requires("pcre2/10.48", transitive_headers=True, transitive_libs=True)
        # ---- APRS integration ------------------------------------------
        self.requires("libax25/0.0.12-rc5", transitive_headers=True, transitive_libs=True)
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)
        self.requires("berkeley-db/4.8.30", transitive_headers=True, transitive_libs=True)
        # ---- geocoding (Nominatim) --------------------------------------
        # The optional Nominatim geocoding support needs libcurl + cJSON.
        # cjson/1.7.19 is published in the registry, so the feature stays
        # enabled together with its upstream tests (the nominatim_tests.at
        # autotest group and the test_nominatim check_PROGRAM), keeping the
        # full upstream test inventory runnable.
        self.requires("cjson/1.7.19", transitive_headers=True, transitive_libs=True)
        # ---- zlib unification -------------------------------------------
        # curl/8.15.0 pins zlib/1.3.1.1, libax25 pins zlib/1.3.1: force the
        # newer one so the graph converges (R36 names all published).
        self.requires("zlib/1.3.1.1", force=True)

    def build_requirements(self):
        # The release tarball has no configure: bootstrap needs aclocal +
        # automake (the hnp system toolchain already provides autoconf 2.72,
        # autoheader and autom4te, which run natively on the worker).
        self.tool_requires("automake/1.19")

    def layout(self):
        # The tree is VPATH-capable (upstream bootstrap + automake), so the
        # build happens in a clean out-of-source build folder.
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source_data = dict(self.conan_data["sources"])
        # These keys document the archive but are not get() arguments.
        source_data.pop("tar_format", None)
        source_data.pop("upstream_version", None)
        get(self, **source_data, strip_root=True)

    # ------------------------------------------------------------------
    # generate()
    # ------------------------------------------------------------------

    def generate(self):
        VirtualBuildEnv(self).generate()
        is_ohos = str(self.settings.os) == "OHOS"

        # E050: private real-file copy of the dependency lib closure, kept
        # first on -L and LD_LIBRARY_PATH (details in the class docstring).
        self._linker_view = self._prepare_linker_view()

        tc = AutotoolsToolchain(self)
        environment = tc.environment()
        if is_ohos:
            shell = self._ohos_shell()
            environment.define_path("SHELL", shell)
            environment.define_path("CONFIG_SHELL", shell)
            environment.define_path("CC", self._compiler_executable("c", "clang"))
            environment.define_path("CXX", self._compiler_executable("cpp", "clang++"))
            environment.define_path("LD", self._tool_executable("ld.lld", "ld"))
            environment.define_path("AR", self._tool_executable("llvm-ar", "ar"))
            environment.define_path(
                "RANLIB", self._tool_executable("llvm-ranlib", "ranlib")
            )
            environment.define_path(
                "STRIP", self._tool_executable("llvm-strip", "strip")
            )
            environment.define_path("NM", self._tool_executable("llvm-nm", "nm"))
            # R49: dependency roots only through the private build folder.
            # PREPEND, not append: the OHOS worker shell presets
            # LDFLAGS=-L<worker>/usr/local/lib and
            # CPPFLAGS=-I<worker>/usr/local/include, and conan's env
            # composition keeps preset values first. That prefix holds an
            # old curl (SONAME libcurl.so.4) and an old shared pcre2 —
            # -lcurl/-lpcre2-8 resolved there instead of against the conan
            # graph, producing a binary whose DT_NEEDED cannot be
            # satisfied at runtime. Prepending puts the conan view and the
            # dependency dirs first; the worker prefix stays as a harmless
            # tail fallback.
            environment.prepend("CPPFLAGS", " ".join(self._dep_cppflags()))
            environment.prepend(
                "LDFLAGS",
                " ".join([f"-L{self._linker_view}"] + self._dep_ldflags()),
            )
            # make-check test binaries and the autotest driver genuinely
            # execute on the worker: the linker view must win the search.
            environment.prepend_path("LD_LIBRARY_PATH", str(self._linker_view))
        # Berkeley DB map cache: XASTIR_BERKELEY_DB_CHK_LIB searches for
        # db_create under names db-18.1 … db50 — none matches libdb.a, so the
        # "none required" branch must find it already on LIBS.
        environment.append("LIBS", "-ldb")

        tc.configure_args.extend(
            [
                # Deterministic optional-feature matrix on OHOS: the only
                # published magick (imagemagick 7.1.2.29, 0x712) is rejected
                # by XASTIR_CHECK_IMAGEMAGICK and GraphicsMagick is not
                # published; festival/gpsman are absent runtime helpers.
                # Nominatim geocoding is NOT disabled: cjson/1.7.19 is
                # published, so configure enables it and the upstream
                # nominatim tests run too.
                "--without-graphicsmagick",
                "--without-imagemagick",
                "--without-festival",
                "--without-gpsman",
            ]
        )
        if is_ohos:
            tc.configure_args.extend(
                [
                    # Explicit build+host triples: config.guess cannot run on
                    # the OHOS worker (HMDFS denies its temp writes and it
                    # does not know HarmonyOS anyway) — aalib precedent.
                    "--build=aarch64-linux-ohos",
                    # Cross mode: configure must not try to run test
                    # programs (E232 host cannot run them, and the libc is
                    # not the build libc anyway).
                    "--host=aarch64-linux-ohos",
                    # AC_FUNC_MALLOC cross default would #define malloc to
                    # rpl_malloc and break the link (twclock precedent).
                    "ac_cv_func_malloc_0_nonnull=yes",
                ]
            )
        tc.generate(env=environment)
        # The build() configure invocation (explicit `sh configure`, E232)
        # needs exactly these args, including the automatic --prefix.
        self._configure_args = list(tc.configure_args)

    # ------------------------------------------------------------------
    # build()
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap()
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            # E011: be defensive about the /bin/sh shebangs of the freshly
            # generated configure and the automake-installed config helpers.
            self._patch_shell_scripts()
            self._run_configure_via_sh()
            # E232: generated make recipes exec scripts directly (the five
            # config/ language generators are perl scripts, the git-stamp
            # rule is a shell script) — HMDFS denies script execve, so the
            # freshly generated Makefiles get explicit interpreters.
            self._patch_generated_makefiles()
        else:
            autotools = Autotools(self)
            autotools.configure()
        # -j1: HMDFS CI workers are memory-constrained; xastir's single
        # compile unit set is not parallel-dependent (abx/motif precedent).
        if is_ohos:
            self.run("make -j1", cwd=self.build_folder, env="conanbuild")
        else:
            autotools = Autotools(self)
            autotools.make(args=["-j1"])
        # === Upstream test step (R51 / docs/TEST_QUALITY_SPEC.md §3.3) ===
        # xastir 2.2.4 ships a real autotest suite (tests/testsuite.at +
        # seven check_PROGRAMS built from the real src/*.c modules); `make
        # check` compiles and runs it verbatim. The raw output is captured
        # into the build log; a failure is *evidence*, recorded loudly, not
        # something the packaging step would hide.
        self._run_upstream_tests()

    # ------------------------------------------------------------------
    # package()
    # ------------------------------------------------------------------

    def package(self):
        # ---- Authoritative staging: mirror the upstream install set ------
        # `make install` is NOT the packaging driver: on the OHOS/HMDFS
        # worker `config/install-sh` cannot be executed (HMDFS ignores
        # chmod) — the defect twclock/dinotrace documented. The real
        # artifacts are staged explicitly with copy() and VERIFIED; an
        # upstream `make install` trace is still captured non-fatally.
        for src_dir in (os.path.join(self.build_folder, "src"),
                       os.path.join(self.source_folder, "src")):
            if os.path.isfile(os.path.join(src_dir, "xastir")):
                copy(self, "xastir", src=src_dir,
                     dst=os.path.join(self.package_folder, "bin"), keep_path=False)
                break
        callpass_src = os.path.join(self.build_folder, "callpass")
        if not os.path.isfile(os.path.join(callpass_src, "callpass")):
            callpass_src = os.path.join(self.source_folder, "callpass")
        copy(self, "callpass", src=callpass_src,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        # Runtime data tree: XASTIR_DATA_BASE points at share/xastir and the
        # app loads config/*.dbfawk, symbols/*, help/*.dat, scripts/*.
        pkgdata = os.path.join(self.package_folder, "share", "xastir")
        source = self.source_folder
        for subdir in ("config", "symbols", "help", "scripts"):
            copy(self, "*", src=os.path.join(source, subdir),
                 dst=os.path.join(pkgdata, subdir), keep_path=False)
        copy(self, "COPYING", src=source,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # man_MANS (top-level Makefile.am) live at the source root.
        for man in ("xastir.1", "callpass.1", "xastir_udp_client.1",
                    "testdbfawk.1"):
            copy(self, man, src=source,
                 dst=os.path.join(self.package_folder, "share", "man", "man1"),
                 keep_path=False)

        # ---- Evidence-only upstream `make install` trace -----------------
        staging = os.path.join(self.build_folder, "install-staging")
        self.output.info("=== upstream `make install` trace (non-authoritative) ===")
        self.run(
            f"make install DESTDIR={shlex.quote(staging)}",
            ignore_errors=True,
            env="conanbuild",
        )
        self.output.info("=== end upstream `make install` trace ===")

        # ---- Loud verification: never silently ship an incomplete package
        expected = {
            "bin/xastir": os.path.join(self.package_folder, "bin", "xastir"),
            "bin/callpass": os.path.join(self.package_folder, "bin", "callpass"),
            "share/xastir/config/language-English.sys": os.path.join(
                self.package_folder, "share", "xastir", "config",
                "language-English.sys",
            ),
            "share/xastir/symbols/symbols.dat": os.path.join(
                self.package_folder, "share", "xastir", "symbols", "symbols.dat",
            ),
            "share/xastir/help/help-English.dat": os.path.join(
                self.package_folder, "share", "xastir", "help",
                "help-English.dat",
            ),
            "licenses/COPYING": os.path.join(
                self.package_folder, "licenses", "COPYING",
            ),
        }
        missing = [rel for rel, path in expected.items() if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                "xastir/2.2.4 packaging incomplete; missing required artifact(s): "
                + ", ".join(missing)
                + f" under {self.package_folder}"
            )

    def package_info(self):
        # CLI/application package: only bin/, no linkable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = [
            "motif::motif",
            "libxt::libxt",
            "libxext::libxext",
            "libxpm::libxpm",
            "xorgproto::xorgproto",
            "libgeotiff::libgeotiff",
            "shapelib::shapelib",
            "pcre2::pcre2",
            "libax25::libax25",
            "curl::curl",
            "cjson::cjson",
            "berkeley-db::berkeley-db",
            "zlib::zlib",
        ]
        self.cpp_info.set_property("cmake_file_name", "xastir")
        self.cpp_info.set_property("cmake_target_name", "xastir::xastir")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------
    # OHOS helpers (mirrors twclock/3.5 + abiword-plugin-gdict/3.0.8)
    # ------------------------------------------------------------------

    def _ohos_shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "/usr/bin/sh",
            "/data/service/hnp/bin/bash",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/system/bin/sh"

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _tool_executable(self, *names):
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return names[0]

    def _dependency_dirs(self, subdir):
        result = []
        for dependency in self.dependencies.host.values():
            path = os.path.join(dependency.package_folder, subdir)
            if os.path.isdir(path) and path not in result:
                result.append(path)
        return result

    def _dep_cppflags(self):
        return [f"-I{path}" for path in self._dependency_dirs("include")]

    def _dep_ldflags(self):
        flags = []
        for path in self._dependency_dirs("lib"):
            flags.append(f"-L{path}")
            flags.append(f"-Wl,-rpath-link,{path}")
        return flags

    # ---- E050 linker view ----------------------------------------------

    def _prepare_linker_view(self):
        """Real-file copy of every dependency lib dir; broken symlink nodes
        (libtiff.so, libXau.so.6, …) are reconstructed from the
        highest-version readable sibling, so both -l resolution and the
        runtime loader are satisfied without touching package folders."""
        linker_view = Path(self.build_folder, "linker-view")
        linker_view.mkdir(parents=True, exist_ok=True)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for entry in sorted(source_dir.iterdir()):
                    name = entry.name
                    if not (name.endswith(".a") or ".so" in name):
                        continue
                    if name.endswith(".la") or name.endswith(".pc"):
                        continue
                    self._mirror_node_into_view(entry, source_dir, linker_view)
        self.output.info(
            f"E050 linker view staged at {linker_view} "
            f"({len(os.listdir(linker_view))} entries)"
        )
        return linker_view

    @staticmethod
    def _mirror_node_into_view(source, source_dir, linker_view):
        destination = linker_view / source.name
        try:
            if source.is_file():
                # Readable (possibly a working symlink): copyfile() follows
                # it, landing a real file in the view.
                shutil.copyfile(source, destination)
                return
        except OSError:
            pass
        if destination.exists() or destination.is_symlink():
            return
        # Unreadable node (EACCES) or dangling link: reconstruct from the
        # highest-version readable sibling with the same libX.so stem.
        match = re.match(r"^(.*\.so)(?:\.\d[\w.]*)?$", source.name)
        if not match:
            return
        stem = match.group(1)
        candidates = []
        for sibling in source_dir.iterdir():
            sibling_match = re.match(
                r"^{stem}\.(\d[\w.]*)$".format(stem=re.escape(stem)),
                sibling.name,
            )
            if not sibling_match:
                continue
            try:
                if sibling.is_file() and not sibling.is_symlink():
                    candidates.append((sibling_match.group(1), sibling))
            except OSError:
                continue
        if candidates:
            candidates.sort(key=lambda item: item[0])
            shutil.copyfile(candidates[-1][1], destination)

    # ---- bootstrap -------------------------------------------------------

    def _bootstrap(self):
        """Regenerate configure/Makefile.in the way upstream bootstrap.sh
        does (aclocal + autoheader + autoconf + automake -a -c), using the
        hnp system autoconf 2.72 and the conan automake/1.19 package.
        Explicit interpreters everywhere: script execve is unreliable under
        HMDFS (E232)."""
        source = self.source_folder
        os.makedirs(os.path.join(source, "m4"), exist_ok=True)
        is_ohos = str(self.settings.os) == "OHOS"

        autoconf = shutil.which("autoconf") or "/data/service/hnp/bin/autoconf"
        autoheader = shutil.which("autoheader") or "/data/service/hnp/bin/autoheader"

        automake_dep = self.dependencies.build["automake"]
        automake_bin = os.path.join(automake_dep.package_folder, "bin")

        if is_ohos:
            # conan automake wrappers are #!/bin/sh scripts — invoke the
            # interpreter explicitly (the wrapper execs `perl` itself,
            # resolved from PATH, which the ohos-aarch64 profile sets to
            # the working hnp perl).
            aclocal_cmd = (
                f'ACLOCAL_PATH="{shlex.quote(os.path.join(source, "m4"))}:$ACLOCAL_PATH" '
                f'sh {shlex.quote(os.path.join(automake_bin, "aclocal"))} --force'
            )
            automake_cmd = (
                f'sh {shlex.quote(os.path.join(automake_bin, "automake"))} '
                "--add-missing --copy --no-force"
            )
        else:
            aclocal_cmd = (
                f'ACLOCAL_PATH="{shlex.quote(os.path.join(source, "m4"))}:$ACLOCAL_PATH" '
                f'"{shutil.which("aclocal") or "aclocal"}" --force'
            )
            automake_cmd = '"automake" --add-missing --copy --no-force'

        for command in (
            aclocal_cmd,
            f'"{autoheader}"',
            f'"{autoconf}"',
            automake_cmd,
        ):
            self.run(command, cwd=source, env="conanbuild")

    def _run_configure_via_sh(self):
        """E232: `sh configure <args>` instead of exec'ing the script."""
        shell = self._ohos_shell()
        configure = os.path.join(self.source_folder, "configure")
        command = " ".join(
            shlex.quote(part)
            for part in [shell, configure] + list(self._configure_args)
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def _patch_shell_scripts(self):
        shell = self._ohos_shell()
        candidates = [os.path.join(self.source_folder, "configure")]
        # automake -a installs the aux helpers into the source root because
        # xastir has no AC_CONFIG_AUX_DIR.
        for name in ("install-sh", "missing", "depcomp", "compile",
                     "config.guess", "config.sub", "ylwrap", "test-driver"):
            candidates.append(os.path.join(self.source_folder, name))
        for path in candidates:
            if not os.path.isfile(path):
                continue
            with open(path, "r+", encoding="utf-8", errors="surrogateescape") as h:
                content = h.read()
            patched = content
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                patched = patched.replace(pattern, f"#!{shell}", 1)
            # E011/HMDFS: `umask 077 && mktemp -d` builds a 0700 directory
            # that HMDFS then refuses to let anyone write into (autoconf's
            # config.status temp machinery dies with "can't create
            # ./confXXXXXX/subs1.awk: Permission denied"). twclock precedent:
            # relax to 022 in the configure script AND the embedded
            # config.status template.
            patched = patched.replace("umask 077", "umask 022")
            if patched != content:
                with open(path, "w", encoding="utf-8",
                          errors="surrogateescape", newline="") as h:
                    h.write(patched)

    def _patch_generated_makefiles(self):
        """E232: rewrite generated make recipes that exec scripts directly
        (config/ language generators are perl scripts, the git-stamp rule
        is a shell script) to invoke them through explicit interpreters."""
        import glob

        for makefile in glob.glob(
            os.path.join(self.build_folder, "**", "Makefile"), recursive=True
        ):
            if os.path.isdir(makefile):
                continue
            content = load(self, makefile)
            patched = re.sub(
                r"(?m)^(\s*)\$\(top_srcdir\)/scripts/(lang\S*\.pl)\b",
                r"\1perl $(top_srcdir)/scripts/\2",
                content,
            )
            patched = patched.replace(
                "`$(top_srcdir)/scripts/XastirGitStamp.sh",
                "`sh $(top_srcdir)/scripts/XastirGitStamp.sh",
            )
            if patched != content:
                save(self, makefile, patched)
                self.output.info(f"E232: recipes re-interpreted in {makefile}")

    def _run_upstream_tests(self):
        # R51: run the upstream test targets verbatim (never fake them).
        # The suite is real (autotest + seven check_PROGRAMS), so a failure is
        # surfaced as a build error; the raw output also goes to the log.
        source = shlex.quote(self.source_folder)
        build = shlex.quote(self.build_folder)
        log_name = os.path.join(self.build_folder, "upstream-test.log")
        log = shlex.quote(log_name)
        script = (
            "{\n"
            '  echo "### upstream test census (xastir 2.2.4) ###"\n'
            f'  echo "check_PROGRAMS: $(grep -hE "^check_PROGRAMS" {source}/tests/Makefile.am)"\n'
            '  echo "### make check verbatim ###"\n'
            f"  ( unset DISPLAY; cd {build} && timeout 900 make check ) 2>&1 ; "
            'echo "CHECK_EXIT=$?"\n'
            f"}} > {log} 2>&1\n"
        )
        self.run(script, ignore_errors=True, env="conanbuild")
        output = load(self, log_name)
        self.output.info("=== xastir 2.2.4 upstream test step (raw output) ===")
        for line in output.splitlines():
            self.output.info(f"[upstream-test] {line}")
        self.output.info("=== end xastir upstream test step ===")
        for line in output.splitlines():
            if "CHECK_EXIT=0" in line:
                return
        raise ConanException(
            "xastir/2.2.4 upstream `make check` failed — see the raw "
            "[upstream-test] output above (R51 requires the failure to be "
            "recorded, not hidden)"
        )
