#!/usr/bin/env python3
"""Conan recipe — gdl 3.40.0 (Autotools).

GNOME Docking Library (GNOME Devtools Libraries) — GTK+3 docking widgets,
artifact libgdl-3 (soname libgdl-3.so.5, libtool -version-info 5:9:0).
HarmonyOS PC (aarch64) adaptation notes:

  - Source: official GNOME dist tarball (download.gnome.org), sha256 verified
    against the official gdl-3.40.0.sha256sum. 3.40.0 is the upstream final
    stable release (no later tag/series exists).
  - Build system: autotools and the tarball SHIPS the fully generated
    configure/Makefile.in set — no autotools regen is needed or wanted
    (the device has no automake/libtoolize). A build-time mtime
    normalization pass keeps every generated file newer than its input so
    make never triggers the `missing automake` regen path (enchant
    precedent: extraction mtime inversion is fatal without automake).
  - intltool: IT_PROG_INTLTOOL([0.40.4]) is expanded into unconditional
    hard-error probes inside the shipped configure (intltool-update/,
    -merge, -extract, gettext msgmerge/xgettext/msgfmt, perl >= 5.8.1 and
    perl XML::Parser — none exist on the OHOS worker and the perl-XML
    toolchain is not provisionable). Patch 0001 relaxes exactly those five
    hard errors into no-op ':' markers, and this recipe passes the
    upstream-supported --disable-nls switch: with USE_NLS=no the intltool
    po/Makefile.in.in evaluates the EMPTY all-no and install-data-no
    targets, so none of the intltool machinery runs at make/install time.
    The library itself never calls gettext entry points (bindtextdomain/
    dgettext count in gdl/*.c is 0), so NLS is inert at runtime too.
  - gtk-doc / introspection: disabled explicitly (--disable-gtk-doc is the
    GTK_DOC_CHECK default; --disable-introspection per E179 — g-ir-scanner
    must dlopen target .so files, impossible under OHOS ELF signing, and
    knowledge dependency-resolution.md:706 records the glib/g-i loop).
  - glib dev tools: libgdltypebuiltins.[ch] (glib-mkenums) and
    libgdlmarshal.[ch] (glib-genmarshal) are generated at make time. The
    shipped configure resolves both tools with
    `$PKG_CONFIG --variable=glib_genmarshal glib-2.0` (resp. glib_mkenums)
    — conan PkgConfigDeps mirrors carry no custom variables, so generate()
    appends the absolute tool paths as glib_genmarshal/glib_mkenums
    variables to the generated glib-2.0.pc mirror. The glib package bin dir
    is also prepended to PATH (scripts use `#!/usr/bin/env python3`).
  - Upstream tests: the tarball has NO tests/ directory and no TESTS /
    check_PROGRAMS anywhere (top Makefile.am SUBDIRS = gdl docs po; the
    only check-like program, gdl/test-dock.c, is a noinst interactive GTK
    demo driving gtk_main() with zero assertions). `make check` is run
    anyway and emits an honest HMBS_UPSTREAM_TEST_RESULT
    (no_upstream_tests) marker; consumer verification lives in
    test_package (real device execution).
  - Explicit link closure (build-chain-pitfalls "shared library link
    closure"): every dependency libdir gets -L/-Wl,-rpath/-Wl,-rpath-link,
    and glib's proxy libintl (unique provider of g_libintl_*) is injected
    as an absolute link input, all appended before the toolchain
    environment snapshot.
  - Artifacts: lib/libgdl-3.so.5(.0.9) + gdl-3.0.pc + headers under
    include/libgdl-3.0/gdl. Installed ELF files are OHOS self-signed in
    package() (glib recipe precedent), and the SONAME name holds real file
    content (HMDFS symlinks unreliable at runtime).
"""
import glob
import os
import re
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GdlConan(ConanFile):
    name = "gdl"
    version = "3.40.0"
    description = (
        "GNOME Docking Library — GTK+3 docking widgets library (libgdl-3)"
    )
    # COPYING ships the LGPL-2.0 text; source headers carry "version
    # 2/2.1 ... or (at your option) any later version" wording.
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/Archive/gdl"
    url = ""  # CI fills this
    topics = ("gtk3", "docking", "gnome", "ide")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Direct dependencies (configure.in: libxml-2.0 >= 2.2.8 unconditional
        # PKG_CHECK_MODULES; gtk+-3.0 >= 3.0.0 unconditional PKG_CHECK_MODULES;
        # gdl-3.0.pc: Requires: gtk+-3.0, Requires.private: libxml-2.0).
        # glib is the gtk baseline and provides the dev tools gdl's make rules
        # invoke. transitive_headers/libs: gdl-3.0.pc publicly Requires
        # gtk+-3.0, so consumers and test_package need the full include/lib
        # closure.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        # Transitive closure alignment (verbatim from the CI-passed
        # libido3/13.10.0 recipe — same gtk/3.24.43 graph; see its conanfile
        # for the per-pin rationale: CCI tool-edge elimination + ohpcd
        # publish identity).
        self.requires(
            "pixman/0.46.4#09f648ede446f6abf85a98da455c7562",
            override=True,
        )
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires(
            "freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19",
            override=True,
        )
        self.requires("zlib/1.3.1.1", override=True)
        self.requires(
            "libpng/1.6.58#d25df07aba0399181f60ee377e83d701",
            override=True,
        )
        self.requires("expat/2.8.2.1", override=True)
        self.requires(
            "libepoxy/1.5.10#92f7e70c459ed2e6a96cd82549e82391",
            override=True,
        )
        self.requires(
            "libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
            override=True,
        )
        self.requires(
            "libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560",
            override=True,
        )
        self.requires(
            "cairo/1.18.4#3894814f2279392f808090c9f3d8f200",
            override=True,
        )
        self.requires(
            "libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf",
            override=True,
        )
        self.requires(
            "libdeflate/1.25#2346ca4f797e19d8d553b6f698dd8982",
            override=True,
        )
        self.requires(
            "zstd/1.5.7#83364ff4f4ab63fae26fbfb89f89fefe",
            override=True,
        )

    def build_requirements(self):
        # The tarball ships generated configure/Makefile.in — no automake/
        # libtool bootstrap needed. pkgconf ships the pkg-config-compatible
        # binary and is the guaranteed fallback in the deterministic
        # pkg-config resolution (pcre2/accountsservice probe precedent).
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gdl %s only supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # generate(): environment assembly.
    # Order matters: buildenv_info mutation must happen BEFORE
    # VirtualBuildEnv(self).generate(), and every tc.* mutation must happen
    # BEFORE tc.generate() (the environment snapshot), else it is silently
    # dropped (build-chain-pitfalls, libgee case).
    # ------------------------------------------------------------------
    def generate(self):
        PkgConfigDeps(self).generate()
        self._synthesize_vendored_pc_files()
        self._augment_glib_tool_variables()

        tc = AutotoolsToolchain(self)
        # OHOS is not recognized by the tarball-era (2021) config.guess/
        # config.sub; pin GNU triplets so configure skips the guess probe
        # (compiler still targets OHOS via the toolchain flags; libido3/
        # ctpl precedent). The explicit values also override the
        # auto-generated *-linux-ohos ones.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Upstream libtool builds shared only for this port; the explicit
        # flags keep the intent visible and stable.
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--enable-shared")
        # E179: introspection needs g-ir-scanner running target binaries
        # (OHOS ELF signing) — disable explicitly (macro default is auto).
        tc.configure_args.append("--disable-introspection")
        # gtk-doc has no doc toolchain on OHOS (default is already no; keep
        # the intent explicit).
        tc.configure_args.append("--disable-gtk-doc")
        # NLS off: the intltool po/ machinery is neutralized (patch 0001)
        # and po/Makefile.in.in evaluates the empty all-no/install-data-no
        # targets. The library code has zero gettext runtime calls.
        tc.configure_args.append("--disable-nls")

        # Explicit link closure (build-chain-pitfalls): every host dep libdir
        # gets -L/-Wl,-rpath/-Wl,-rpath-link; g_libintl_* sole provider
        # (glib lib/libintl.so) becomes an explicit absolute link input.
        # glib >= 2.84 statically vendors pcre2/ffi — those Skipped binaries
        # have package_folder None and must be skipped.
        have_intl_input = False
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for inc in dep.cpp_info.includedirs:
                tc.extra_cflags.append("-I%s" % inc)
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append("-L%s" % libdir)
                tc.extra_ldflags.append("-Wl,-rpath,%s" % libdir)
                tc.extra_ldflags.append("-Wl,-rpath-link,%s" % libdir)
            intl = os.path.join(dep.package_folder, "lib", "libintl.so")
            if os.path.isfile(intl):
                tc.extra_ldflags.append(intl.replace(os.sep, "/"))
                have_intl_input = True
        if not have_intl_input:
            tc.extra_ldflags.append("-lintl")
            self.output.info(
                "linkfix: no absolute libintl.so found, falling back to -lintl"
            )

        env = Environment()

        # Deterministic pkg-config resolution: PKG_PROG_PKG_CONFIG honours
        # the PKG_CONFIG env var; wrap whatever real binary we resolved in a
        # fixed-name shim so configure always finds a runnable one (worker
        # PATH state must not decide the build).
        pkg_bin = self._resolve_pkg_config_binary()
        shim_dir = os.path.join(self.build_folder, "hmbs-pkgconf-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "pkg-config")
        fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write('#!/bin/sh\nexec "%s" "$@"\n' % pkg_bin)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: open mode already grants exec
        env.define("PKG_CONFIG", shim)
        env.prepend_path("PATH", shim_dir)
        self.output.info("using pkg-config via shim: %s -> %s" % (shim, pkg_bin))

        # PKG_CONFIG_PATH order: PkgConfigDeps mirrors FIRST, then the
        # synthesized vendored mirrors, then the real package dirs.
        # Rationale: the ohpcd dependency packages ship their real .pc files
        # with prefix=/ (relocated packaging), so every -I/-L they expand is
        # wrong on the worker. The PkgConfigDeps mirrors carry the true
        # absolute package-folder paths and a complete Requires chain; real
        # dirs remain as fallback for names without a mirror.
        pc_dirs = []
        try:
            gens = self.generators_folder
            if gens and os.path.isdir(gens):
                pc_dirs.append(gens)
        except Exception:
            pass
        vd = getattr(self, "_vendored_pc_dir", None)
        if vd and os.path.isdir(vd) and vd not in pc_dirs:
            pc_dirs.append(vd)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in pc_dirs:
                    pc_dirs.append(d)
        if pc_dirs:
            env.define("PKG_CONFIG_PATH", os.pathsep.join(pc_dirs))

        # glib dev tools live in the glib package bin dir; the make-time
        # enum/marshal rules invoke the paths configure baked from
        # `pkg-config --variable` (see _augment_glib_tool_variables). Put
        # every dep bin dir on the build PATH so the scripts execute, and
        # pin the env names as well (harmless, and guards any AC_PATH_PROG
        # style fallback).
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            b = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(b):
                env.append_path("PATH", b)
        glib_mkenums = self._find_glib_tool("glib-mkenums")
        glib_genmarshal = self._find_glib_tool("glib-genmarshal")
        if glib_mkenums:
            env.define("GLIB_MKENUMS", glib_mkenums)
            self.output.info("GLIB_MKENUMS pinned: %s" % glib_mkenums)
        if glib_genmarshal:
            env.define("GLIB_GENMARSHAL", glib_genmarshal)
            self.output.info("GLIB_GENMARSHAL pinned: %s" % glib_genmarshal)

        # VirtualBuildEnv: puts the tool_requires binaries (pkgconf) and
        # their buildenv on the conanbuild PATH.
        VirtualBuildEnv(self).generate()
        # Merge, don't replace: passing a bare env to generate() would drop
        # the toolchain's own env (CFLAGS/LDFLAGS with the link-closure
        # flags above) — env appended after the snapshot is silently
        # dropped; compose instead.
        tc_env = tc.environment()
        tc_env.compose_env(env)
        tc.generate(env=tc_env)

    def _find_glib_tool(self, tool_name):
        """Locate a glib dev tool inside the glib package (libido3
        precedent). Returns "" when not found."""
        candidates_first = []
        try:
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                if dep.ref.name == "glib":
                    candidates_first.append(dep.package_folder)
        except Exception:
            pass
        try:
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                candidates_first.append(dep.package_folder)
        except Exception:
            pass
        seen = set()
        for pkg in candidates_first:
            if pkg in seen:
                continue
            seen.add(pkg)
            cand = os.path.join(pkg, "bin", tool_name)
            if os.path.isfile(cand):
                return cand
        return ""

    def _augment_glib_tool_variables(self):
        """Make `pkg-config --variable=glib_genmarshal glib-2.0` resolve.

        The shipped configure resolves both dev tools with
        GLIB_GENMARSHAL="`$PKG_CONFIG --variable=glib_genmarshal glib-2.0`"
        (resp. glib_mkenums) at configure time and bakes the values into
        gdl/Makefile. conan's PkgConfigDeps mirror .pc files carry only
        prefix/libdir/cflags/libs — no custom variables — so without this
        step both variables resolve empty and the typebuiltins/marshal
        generation at make time fails. Append the absolute tool paths as
        the corresponding variables to the generated glib-2.0.pc mirror
        (mirrors sit first in PKG_CONFIG_PATH, so they win the lookup).
        """
        gens = getattr(self, "generators_folder", None)
        if not gens or not os.path.isdir(gens):
            return
        mirror = os.path.join(gens, "glib-2.0.pc")
        if not os.path.isfile(mirror):
            self.output.warning(
                "glib-2.0.pc mirror not found in generators folder; "
                "pkg-config --variable lookups may resolve empty"
            )
            return
        with open(mirror, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        additions = []
        for var, tool in (
            ("glib_genmarshal", "glib-genmarshal"),
            ("glib_mkenums", "glib-mkenums"),
        ):
            tool_path = self._find_glib_tool(tool)
            if not tool_path:
                raise ConanException(
                    "%s not found in any dependency package; gdl make rules "
                    "need it for libgdltypebuiltins/libgdlmarshal generation"
                    % tool
                )
            if re.search(r"^%s=" % re.escape(var), content, re.MULTILINE):
                continue
            additions.append("%s=%s" % (var, tool_path.replace(os.sep, "/")))
        if additions:
            if not content.endswith("\n"):
                content += "\n"
            content += "\n".join(additions) + "\n"
            with open(mirror, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info(
                "[ok] glib-2.0.pc mirror augmented with: %s"
                % ", ".join(additions)
            )

    def _synthesize_vendored_pc_files(self):
        """Synthesize .pc mirrors for unresolvable public Requires names.

        The ohpcd binary closures vendor several libraries and declare them
        "Skipped binaries" (graphite2, libffi, pcre2, xz) — those nodes have
        no conan package folder and therefore no real .pc. Real dependency
        .pc files may still reference them in public Requires (gobject-2.0
        -> libffi, glib-2.0 -> libpcre2-8, libtiff-4 -> liblzma), which
        makes a plain pkg-config chain resolution abort ("Package 'libffi'
        required by 'gobject-2.0' not found"). Walk BOTH the real .pc dirs
        and the generators folder — the PkgConfigDeps mirror files in the
        generators folder are exactly where such references hide — and
        include Requires.private edges, because pkg-config 0.29 (the
        worker's /data/service/hnp/bin/pkg-config) demands they be locatable
        even for non-static queries. For every referenced name that cannot
        be resolved write a content-free mirror into a private build-folder
        dir, which sits in PKG_CONFIG_PATH after the PkgConfigDeps mirrors
        and before the real package dirs (real .pc files win whenever they
        exist). Empty Libs/Cflags is the correct content: the vendored
        symbols are exported by the vendoring library, nothing needs
        linking (build-chain-pitfalls). The synthesized Version is the
        highest version constraint observed at the reference site (or the
        graph-skipped version when visible), so sibling ">= x" checks hold.
        A final pkg-config probe on the modules configure needs (gtk+-3.0,
        libxml-2.0, glib-2.0) fails fast with a clear message instead of a
        cryptic configure error three build minutes later.
        """
        try:
            gens = self.generators_folder
        except Exception:
            return
        if not gens or not os.path.isdir(gens):
            return

        real_dirs = []
        skipped_versions = {}
        for dep in self.dependencies.values():
            if not dep.package_folder:
                try:
                    skipped_versions[dep.ref.name] = str(dep.ref.version)
                except Exception:
                    pass
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in real_dirs:
                    real_dirs.append(d)
        # Walk (and probe) in the SAME order as the final PKG_CONFIG_PATH:
        # mirrors first, synthesized vendored mirrors second, real dirs last.
        # Synthesized mirrors live in a PRIVATE build-folder dir, NOT in the
        # generators folder: conan rolls the generators folder back when a
        # generate() exception propagates (libido3 CI round 6).
        vendored_dir = os.path.join(self.build_folder, "hmbs-vendored-pc")
        try:
            os.makedirs(vendored_dir, exist_ok=True)
        except OSError:
            return
        self._vendored_pc_dir = vendored_dir
        search_dirs = []
        try:
            if gens and os.path.isdir(gens):
                search_dirs.append(gens)
        except Exception:
            pass
        search_dirs.append(vendored_dir)
        search_dirs.extend(real_dirs)

        # .pc filename -> conan ref name of the vendored provider, when the
        # names differ (used to read the real version off the graph).
        provider = {"liblzma": "xz", "libpcre2-8": "pcre2", "libpcre2-posix": "pcre2"}

        def find_pc(name):
            for d in search_dirs:
                p = os.path.join(d, name + ".pc")
                if os.path.isfile(p):
                    return p
            return None

        def requires_edges(path):
            # pkg-config 0.29 requires Requires.private packages to be
            # LOCATABLE even for non-static queries. .pc Requires lists come
            # in BOTH spellings: comma-separated ("a, b >= 1.2") and
            # whitespace-separated ("a b >= 1.2") — normalize commas to
            # spaces and parse name/op/version triples sequentially.
            out = []
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.startswith("Requires"):
                            continue
                        toks = line.split(":", 1)[1].replace(",", " ").split()
                        i = 0
                        while i < len(toks):
                            name = toks[i]
                            op = toks[i + 1] if i + 1 < len(toks) else None
                            ver = toks[i + 2] if i + 2 < len(toks) else None
                            if op in (">=", "<=", "==", ">", "<", "="):
                                out.append((name, op, ver))
                                i += 3
                            else:
                                out.append((name, None, None))
                                i += 1
            except OSError:
                pass
            return out

        missing = {}  # name -> version to synthesize
        queue = sorted(
            os.path.basename(p)[:-3]
            for d in search_dirs
            for p in glob.glob(os.path.join(d, "*.pc"))
        )
        seen = set()
        while queue:
            name = queue.pop(0)
            if name in seen:
                continue
            seen.add(name)
            path = find_pc(name)
            if path is None:
                continue
            for dep_name, op, cver in requires_edges(path):
                if find_pc(dep_name) is None:
                    ver = skipped_versions.get(
                        provider.get(dep_name, dep_name), ""
                    )
                    if cver and op in (">=", "==", ">"):
                        if not ver or self._ver_gt(cver, ver):
                            ver = cver
                    missing[dep_name] = ver or "1"
                queue.append(dep_name)

        written = []
        for name in sorted(missing):
            pc = os.path.join(vendored_dir, name + ".pc")
            if os.path.isfile(pc):
                continue
            content = (
                "prefix=/\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: %s\n" % name
                + "Description: Vendored (conan Skipped) binary; symbols are exported by the vendoring library, nothing to link\n"
                "Version: %s\n" % missing[name]
                + "Libs:\n"
                "Cflags:\n"
            )
            with open(pc, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            written.append("%s(%s)" % (name, missing[name]))
        if written:
            self.output.info(
                "[ok] synthesized vendored .pc mirrors: %s" % ", ".join(written)
            )
        self._probe_pkg_config_resolution(search_dirs)

    def _probe_pkg_config_resolution(self, search_dirs):
        """Fail fast when the modules configure needs do not resolve."""
        import subprocess as _sp

        pkg_bin = (
            os.environ.get("PKG_CONFIG_REAL")
            or shutil.which("pkgconf")
            or shutil.which("pkg-config")
        )
        if not pkg_bin:
            self.output.warning(
                "no pkgconf/pkg-config for the resolution probe; skipping"
            )
            return
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.pathsep.join(list(search_dirs))
        try:
            p = _sp.run(
                [pkg_bin, "--exists", "gtk+-3.0", "libxml-2.0", "glib-2.0"],
                stdout=_sp.PIPE,
                stderr=_sp.STDOUT,
                text=True,
                timeout=30,
                env=env,
                check=False,
            )
        except Exception as exc:
            self.output.warning("pkg-config probe failed to run: %r" % exc)
            return
        if p.returncode == 0:
            self.output.info(
                "[ok] pkg-config probe: gtk+-3.0 + libxml-2.0 + glib-2.0 resolve"
            )
        else:
            raise ConanException(
                "pkg-config cannot resolve gtk+-3.0/libxml-2.0/glib-2.0 even "
                "after vendored .pc synthesis (rc=%s, out=%s)"
                % (p.returncode, (p.stdout or "").strip())
            )

    @staticmethod
    def _ver_gt(a, b):
        try:
            ta = tuple(int(x) for x in re.split(r"[.\-_+]", a) if x.isdigit())
            tb = tuple(int(x) for x in re.split(r"[.\-_+]", b) if x.isdigit())
            return ta > tb
        except Exception:
            return False

    def _resolve_pkg_config_binary(self):
        """Find a runnable pkg-config/pkgconf binary (pcre2/accountsservice
        probe precedent). The conan pkgconf tool package is the guaranteed
        last candidate."""
        import subprocess as _sp

        conf_val = None
        try:
            conf_val = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_val = None
        pkgconf_pkg_bin = ""
        try:
            for dep in self.dependencies.build.values():
                if dep.ref.name == "pkgconf" and dep.package_folder:
                    cand = os.path.join(dep.package_folder, "bin", "pkgconf")
                    if os.path.isfile(cand):
                        pkgconf_pkg_bin = cand
                    break
        except Exception:
            pass
        candidates = [
            conf_val,
            os.environ.get("PKG_CONFIG"),
            shutil.which("pkg-config"),
            shutil.which("pkgconf"),
            "/data/service/hnp/bin/pkg-config",
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-pkg-config",
            pkgconf_pkg_bin,
        ]
        for cand in candidates:
            if not cand or not os.path.isfile(str(cand)):
                continue
            try:
                p = _sp.run(
                    [str(cand), "--version"],
                    stdout=_sp.PIPE,
                    stderr=_sp.STDOUT,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except Exception:
                continue
            if p.returncode == 0 and (p.stdout or "").strip():
                return str(cand)
        raise ConanException("no runnable pkg-config/pkgconf binary found")

    # ------------------------------------------------------------------
    # build(): patch + mtime normalization + compile.
    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask()
        self._fix_autotools_mtimes()
        self._strip_dependency_la_files()
        self._prepare_runtime_env()
        shim = self._write_install_shim()
        autotools = Autotools(self)
        autotools.configure()
        self._redirect_install_to_shim(shim)
        autotools.make(args=["-j1"])
        self._run_upstream_check()

    def _fix_autotools_mtimes(self):
        """Keep every generated autotools file newer than its inputs.

        The tarball ships the generated build system and the worker has no
        automake/aclocal — if extraction mtime inversion leaves an input
        (configure.in, Makefile.am, m4/*.m4, gtk-doc.make, ...) newer than
        its generated output, make runs the `missing automake-1.16` regen
        path and dies (enchant precedent). The maintainer-mode regen rules
        list EVERY file that participates in regeneration as a prerequisite
        (e.g. `$(srcdir)/Makefile.in: $(srcdir)/Makefile.am
        $(top_srcdir)/gtk-doc.make $(am__configure_deps)`), and ANY newer
        prerequisite — even one that is not an aclocal input — falls through
        to the automake fallback. The guard therefore touches the WHOLE tree
        first (base = wall clock, so tarball-era mtimes always lose) and
        then re-touches the generated outputs in dependency order, a few
        seconds apart. No regen is desired or attempted.
        """
        src = self.source_folder
        now = time.time()

        def touch(path, when):
            try:
                os.utime(path, (when, when))
            except OSError:
                pass

        # 1. Whole tree to base time T: no file may be newer than the
        #    generated set, whatever rule references it.
        for root, dirs, files in os.walk(src):
            for name in files:
                touch(os.path.join(root, name), now)
            for name in dirs:
                touch(os.path.join(root, name), now)
        # 2. Generated outputs, in dependency order.
        for pattern in ("aclocal.m4", "acconfig.h"):
            for p in glob.glob(os.path.join(src, pattern)):
                touch(p, now + 2)
        for pattern in ("configure", "**/configure"):
            for p in glob.glob(os.path.join(src, pattern), recursive=True):
                touch(p, now + 3)
        for pattern in ("config.h.in", "**/config.h.in"):
            for p in glob.glob(os.path.join(src, pattern), recursive=True):
                touch(p, now + 4)
        for p in glob.glob(os.path.join(src, "**", "Makefile.in"), recursive=True):
            touch(p, now + 5)
        # 3. Auxiliary scripts (no autotools inputs, but keep them newest so
        # no aux rule considers them stale).
        for name in (
            "install-sh", "missing", "depcomp", "compile", "ltmain.sh",
            "config.guess", "config.sub", "ylwrap", "mkinstalldirs",
        ):
            for p in glob.glob(os.path.join(src, "**", name), recursive=True):
                touch(p, now + 6)
        self.output.info("[ok] autotools mtimes normalized (no-regen guard)")

    def _patch_configure_umask(self):
        # E011: configure/config.status use `umask 077 && mktemp -d`, which
        # yields an unwritable dir on HMDFS; relax to 022 (generated file,
        # variable form only, no baked absolute paths).
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("[ok] relaxed umask 077 -> 022 in generated configure")

    def _strip_dependency_la_files(self):
        # E236: dependency packages ship .la files whose libdir was broken by
        # conan relocation ("//lib"), making libtool abort with "is not a
        # valid libtool archive". This build is shared-only, so libtool
        # falls back to .so when no .la exists (libgee/a52dec precedent).
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    try:
                        os.remove(os.path.join(lib_dir, entry))
                        self.output.info(
                            "removed broken libtool archive: %s/%s"
                            % (dep.ref, entry)
                        )
                    except OSError:
                        pass

    def _prepare_runtime_env(self):
        # HMDFS: parent dirs may be unresolvable via getcwd(); preset PWD
        # (cdecl precedent). E002: device /tmp is read-only erofs; point
        # TMPDIR at a writable dir.
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD")
        os.environ["PWD"] = self.build_folder
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            self.build_folder, ".tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _write_install_shim(self):
        # E182/E188: toybox install rejects chmod and the HMBS-provided
        # runtime install shim only accepts single-file two-arg calls, while
        # libtool/automake install rules need mkdir/cp semantics with
        # multi-source support. chmod is best-effort (HMBS_CAP_CHMOD=0).
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
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
            '  mkdir -p "$dest"\n'
            "else\n"
            '  mkdir -p "$(dirname "$dest")"\n'
            "fi\n"
            "i=1\n"
            'for src in "$@"; do\n'
            "  [ $i -gt $count ] && break\n"
            '  cp -f "$src" "$dest"\n'
            '  if [ -n "$mode" ]; then\n'
            '    if [ -d "$dest" ]; then\n'
            '      chmod "$mode" "$dest/${src##*/}" 2>/dev/null || true\n'
            "    else\n"
            '      chmod "$mode" "$dest" 2>/dev/null || true\n'
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable; point it at the cp/mkdir shim
        # (ctpl/xeyes precedent).
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mf = os.path.join(root, "Makefile")
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "INSTALL =" not in content:
                continue
            lines = []
            changed = False
            for line in content.splitlines(True):
                stripped = line.lstrip()
                if stripped.startswith("INSTALL = ") and "/install" in stripped:
                    indent = line[: len(line) - len(stripped)]
                    lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                    changed = True
                else:
                    lines.append(line)
            if changed:
                with open(mf, "w", encoding="utf-8", newline="\n") as f:
                    f.writelines(lines)
                self.output.info("[ok] install shim redirected %s" % mf)

    def _run_upstream_check(self):
        """Run `make check` and emit honest upstream-test evidence.

        Upstream has NO automated test suite in the 3.40.0 dist tarball:
        no tests/ directory, no TESTS/check_PROGRAMS in any Makefile.am
        (SUBDIRS = gdl docs po); gdl/test-dock.c is a noinst interactive
        GTK demo with zero assertions. `make check` therefore has no
        cases to run and in fact exits Error 1: the po/ .pot regen rule
        (not gated by USE_NLS, po/Makefile.in.in:148) runs the intltool
        machinery with empty vars (Error 127) -> check-recursive Error 1,
        captured by the ignore_errors below by design; gdl/ and docs/
        report Nothing to be done. The marker records the true state.
        """
        self.run("make check -j1", env="conanbuild", ignore_errors=True)
        marker = {
            "status": "no_upstream_tests",
            "framework": "automake",
            "command": "make check -j1",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "gdl-3.40.0: no automated tests (no tests/ dir, no TESTS/"
                "check_PROGRAMS; test-dock.c noinst GTK demo, 0 assertions)"
                ". make check runs zero cases and exits 1 only from the po/"
                " .pot intltool regen (not NLS-gated, captured by design)"
            ),
        }
        import json as _json

        _msg = "HMBS_UPSTREAM_TEST_RESULT=" + _json.dumps(
            marker, ensure_ascii=False
        )
        print(_msg, flush=True)
        self.output.info(_msg)

    # ------------------------------------------------------------------
    # package(): install + OHOS artifact post-processing.
    # ------------------------------------------------------------------
    def package(self):
        autotools = Autotools(self)
        autotools.install()
        lib_dir = os.path.join(self.package_folder, "lib")
        # E236: never ship libtool metadata — downstream libtool links would
        # re-read stale dependency_libs paths.
        if os.path.isdir(lib_dir):
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))
                    self.output.info("[ok] removed libtool archive %s" % entry)
        self._make_soname_real_file(lib_dir)
        self._sign_installed_elfs()

    def _make_soname_real_file(self, lib_dir):
        # libtool installs the real file (libgdl-3.so.5.0.9) plus symlinks
        # for the SONAME name. HMDFS symlinks are unreliable at runtime, and
        # consumers load via DT_NEEDED "libgdl-3.so.5", so that name must
        # hold real file content (libido3/ayatana-ido precedent: copy, not
        # symlink).
        real = sorted(glob.glob(os.path.join(lib_dir, "libgdl-3.so.5.*")))
        real = [p for p in real if os.path.isfile(p) and not os.path.islink(p)]
        soname = os.path.join(lib_dir, "libgdl-3.so.5")
        if not real:
            self.output.warning(
                "no real libgdl-3.so.5.* file found; soname copy skipped"
            )
            return
        # libtool created soname as a symlink to the real file: drop it and
        # copy the bytes (copyfile would raise SameFileError through the
        # symlink).
        if os.path.lexists(soname):
            os.remove(soname)
        with open(real[0], "rb") as fsrc:
            data = fsrc.read()
        with open(soname, "wb") as fdst:
            fdst.write(data)
        self.output.info(
            "[ok] soname real file: %s <- %s" % (soname, real[0])
        )

    def _sign_installed_elfs(self):
        # OHOS requires ELF signatures for execution; re-sign after install
        # (glib recipe _sign_shared_libs precedent). binary-sign-tool may be
        # absent in cross/SDK environments — warn and skip there.
        lib_dir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(lib_dir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(lib_dir, "**", "*.so.*"), recursive=True)
        sos = sorted(set(sos))
        if not sos:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skip OHOS codesign (cross/SDK env)"
            )
            return
        objcopy = None
        candidates_objcopy = ["/data/service/hnp/bin/llvm-objcopy"]
        try:
            ce = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = (ce or {}).get("c") or ""
            if cc:
                candidates_objcopy.insert(
                    0, os.path.join(os.path.dirname(cc), "llvm-objcopy")
                )
        except Exception:
            pass
        candidates_objcopy.append(shutil.which("llvm-objcopy") or "")
        for cand in candidates_objcopy:
            if cand and os.path.isfile(cand):
                objcopy = cand
                break
        for so in sos:
            if objcopy:
                self.run(
                    '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                        oc=objcopy, f=so
                    ),
                    ignore_errors=True,
                )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=so
                )
            )
            self.output.info("[ok] signed %s" % so)

    # ------------------------------------------------------------------
    # package_info(): consumer metadata.
    # ------------------------------------------------------------------
    def package_info(self):
        self.cpp_info.libs = ["gdl-3"]
        # Headers install under include/libgdl-3.0/gdl and are included as
        # <gdl/xxx.h> (gdl-3.0.pc Cflags: -I${includedir}/libgdl-3.0).
        self.cpp_info.includedirs = ["include/libgdl-3.0", "include"]
        self.cpp_info.set_property("cmake_file_name", "gdl")
        self.cpp_info.set_property("cmake_target_name", "gdl::gdl")
        self.cpp_info.set_property("pkg_config_name", "gdl-3.0")
        # gdl-3.0.pc Requires: gtk+-3.0 (pulls the glib set);
        # Requires.private: libxml-2.0 (the shared lib carries the DT_NEEDED,
        # listed so static consumers still resolve).
        self.cpp_info.requires = ["gtk::gtk", "glib::glib", "libxml2::libxml2"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
