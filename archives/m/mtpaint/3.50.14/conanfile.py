#!/usr/bin/env python3
"""Conan recipe — mtpaint 3.50.14 (custom mini-configure + hand-written Makefile).

mtPaint is Mark Tyler's GTK+ painting program for pixel art and icons
(https://github.com/wjaguar/mtPaint). Upstream uses a bespoke
``configure`` shell script (not GNU Autotools: no configure.ac,
no config.guess/sub) that probes GTK+/libpng/libjpeg/libtiff via
pkg-config and direct link tests, then drives hand-written Makefiles
(top-level Makefile + src/Makefile [+ po/ + doc/ when enabled]).

OHOS adaptations:
    - Configure for GTK+3 (``gtk3``): the registry provides gtk/3.24.43
      (broadway backend, no X11/Wayland) with OHOS binaries.
    - Enable widely-available image codecs explicitly
      (``jpeg tiff lcms2`` + freetype auto-detect); disable JPEG-2000
      and WebP (``nojp2 nowebp``) to keep the first adaptation scoped
      to published/built registry codecs (path A, base adaptation).
    - Disable i18n/man (``MAKE_DIRS=src`` only): gettext tooling and
      man translation are not needed for the binary package.
    - ``--prefix=/`` so ``make install DESTDIR=<package>`` lands the
      binary at ``bin/mtpaint``.
    - Never pass --build/--host (R15): the mini-configure only uses
      --host to detect MinGW; passing it on OHOS would mislabel the OS.
    - pkg-config based probing: $PKG_CONFIG points at the pkgconf/3.0.5
      tool_requires binary (the device has no system pkg-config and the
      in-repo pkgconf installs no pkg-config alias); PkgConfigDeps
      metadata is exposed via an explicit PKG_CONFIG_PATH (generators
      folder + each host dep's lib/pkgconfig and share/pkgconfig),
      resolved at build() time.
    - Shell/TMPDIR/compiler hardening (bwm-ng/0.6.3 precedent): the repo
      profile pins SHELL/CONFIG_SHELL to /data/service/hnp/bin/bash and
      CC to the HNP clang, which may not exist on every HMBS host; the
      recipe prefers /bin/sh, a task-writable TMPDIR, and a compiler
      that passes an isfile probe, keeping CI workers unchanged.
    - Upstream ships no test suite (audited: no tests/ or test/ dir, no
      check/test target in any Makefile, no gtest/ctest/pytest
      registration — see test_package/MANIFEST.yml upstream_test_audit).
      build() therefore does NOT invoke make check
      (upstream_test_in_build: false); HMBS_UPSTREAM_TEST_RESULT
      status=no_tests is emitted by test_package/test.sh every run
      (re-emitted by test_package/conanfile.py on cache hits).
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.layout import basic_layout


class MtpaintConan(ConanFile):
    name = "mtpaint"
    version = "3.50.14"
    description = "mtPaint — simple GTK+ painting program for icons and pixel art"
    license = "GPL-3.0-only"
    homepage = "https://github.com/wjaguar/mtPaint"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mtpaint is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def configure(self):
        # Provide-conflict unification (ayatana-ido/0.10.4-v2 precedent,
        # same fingerprint: Both 'libjpeg/9f' and 'libjpeg-turbo/3.2.0'
        # provide '[libjpeg]'): gdk-pixbuf/direct requires
        # libjpeg-turbo/3.2.0 while conancenter libtiff/4.7.2 defaults to
        # jpeg="libjpeg" (options jpeg=[False,"libjpeg","libjpeg-turbo",
        # "mozjpeg"], default "libjpeg"), pulling libjpeg/9f into the same
        # graph. Same-name override cannot unify two different providers of
        # one virtual; align the flavor option so libtiff uses turbo too.
        try:
            self.options["libtiff"].jpeg = "libjpeg-turbo"
        except Exception:
            pass
        # Compression-feature closure alignment (ayatana-ido/0.10.4-v2
        # precedent): freetype/2.14.3 exists in both remotes and the
        # conancenter recipe wins remote order with with_brotli/with_bzip2/
        # with_png/with_harfbuzz/with_zlib defaulting True, pulling cmake
        # leaves (brotli/1.1.0, bzip2/1.0.8) whose source builds fail on OHOS
        # with "System is unknown to cmake" + CMAKE_C_COMPILER sanity failure.
        # The OHOS freetype/2.14.3 recipe builds --with-zlib=no --with-bzip2=no
        # --with-png=no --with-harfbuzz=no --with-brotli=no (zero-dependency
        # leaf), so align the FULL conancenter compression set in ONE edit
        # instead of chasing one leaf per round. try/except per option: OHOS
        # freetype has none of these options (shared/fPIC only), no-op there.
        for _opt in ("with_brotli", "with_bzip2", "with_png", "with_harfbuzz", "with_zlib"):
            try:
                setattr(self.options["freetype"], _opt, False)
            except Exception:
                pass

    def requirements(self):
        # GTK+3 toolkit (broadway backend on OHOS) — mandatory UI.
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # Core image codecs used by the enabled configure options.
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58#d25df07aba0399181f60ee377e83d701", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560", transitive_headers=True, transitive_libs=True)
        # libtiff/4.7.2: converge on ohpcd gdk-pixbuf/2.44.6.1's own pin.
        # The published gdk-pixbuf/2.44.6.1 binary was built against
        # libtiff/4.7.2; requiring the newer local 4.7.2.2 (even with
        # force=True) changes gdk-pixbuf's dependency package_id, so its
        # OHOS binary is reported missing ("Main binary package missing"
        # + "No compatible configuration found") and the whole image-codec
        # stack falls back to single-job source rebuilds until the preflight
        # SSH session drops ("Connection closed by remote host"). A plain
        # (unforced) require of the exact pinned 4.7.2 keeps the graph
        # conflict-free and reuses the published binary.
        self.requires("libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf", transitive_headers=True, transitive_libs=True)
        # giflib: intentionally NOT required. Upstream replaced its
        # giflib-based GIF load/save with standalone builtin routines in
        # 3.50.03 (commit 40bde45, NEWS: "GIF file format support now is
        # builtin (does not use giflib anymore)"); 3.50.14's configure has
        # no gif probe/option and src links no -lgif. A bare giflib ref
        # only pulls a competing non-hardened recipe into the graph whose
        # source build fails on OHOS, so it is dropped, not pinned.
        self.requires("freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19", transitive_headers=True, transitive_libs=True)
        self.requires("lcms2/2.19", transitive_headers=True, transitive_libs=True)
        # Transitive unification (gtk/3.24.38 precedent, appstream/nymphcast
        # override=True correction, marco/1.26.2 merged precedent):
        # conancenter's cairo/1.18.4 pulls pixman/0.43.4 while ohpcd's
        # cairo-gobject/1.18.4.2 (and local cairo/1.18.4) pin pixman/0.46.4.
        # override=True (not force=True: these are transitive-only, not
        # direct requirements) keeps the OHOS-pinned 0.46.4 winning the graph.
        self.requires("pixman/0.46.4#09f648ede446f6abf85a98da455c7562", override=True)
        # CCI-tool-edge elimination (ayatana-ido/0.10.4-v2 precedent):
        # preflight checks conancenter first, so bare libpng/1.6.58,
        # libjpeg-turbo/3.2.0, freetype/2.14.3, cairo/1.18.4 resolve to CCI
        # recipes whose tool_requires pull CCI cmake/4.4.x (KeyError 'OHOS'
        # on this worker). Pin the ohpcd-published recipe revisions at the
        # SAME versions (package_id-preserving) so the hardened in-repo
        # recipes (bare cmake + ohos.toolchain, zero tool_requires) win.
        # NOTE: direct deps above already carry the same RREVs, so no
        # duplicate override lines for turbo/png/freetype/libtiff here
        # (Conan2 raises Duplicated requirement otherwise).
        self.requires("cairo/1.18.4#3894814f2279392f808090c9f3d8f200", override=True)
        # TIFF-subtree RREV closure (same precedent): libtiff/4.7.2 + its
        # compression leaves exist on both remotes; bare refs resolve to CCI
        # and reintroduce the cmake-tool node. Same versions, ohpcd RREVs.
        self.requires("libdeflate/1.25#2346ca4f797e19d8d553b6f698dd8982", override=True)
        self.requires("zstd/1.5.7#83364ff4f4ab63fae26fbfb89f89fefe", override=True)
        self.requires("libwebp/1.6.0#8b273a5128ee70c508671933b61288ec", override=True)
        self.requires("lerc/4.1.1#9c8297567326e560407157395590b2f8", override=True)
        self.requires("jbigkit/2.1#872f3b26b5921c9156cb3aa4675b20c5", override=True)
        self.requires("xz/5.6.2#66ce4bbd966830b5a11768474be4b259", override=True)
        # Fontconfig/expat unification (cogl/1.22.8.1 + clutter/1.26.4
        # override precedent; klavaro/3.14 coupled expat pin; marco/1.26.2
        # merged precedent): preflight graph fails with "Conflict between
        # fontconfig/2.18.1.1 and fontconfig/2.17.1 ... originates from
        # cairo-gobject/1.18.4.2". cairo-gobject/1.18.4.2, local
        # cairo/1.18.4 and pango/1.50.14.1.1 all pin fontconfig/2.18.1.1,
        # while a conancenter branch pulls fontconfig/2.17.1. override=True
        # converges the graph on the OHOS published 2.18.1.1; its coupled
        # expat pin 2.8.2.1 is overridden together to avoid the follow-on
        # expat conflict.
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("expat/2.8.2.1", override=True)
        # libffi/libepoxy RREV closure (ayatana-ido/0.10.4-v2 precedent,
        # RREVs quoted verbatim from that in-repo recipe, server-verified
        # ohpcd values): preflight resolves glib's bare libffi/3.4.4 to the
        # CCI recipe (it applies CCI patch
        # 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the hardened
        # in-repo recipe) whose configure dies with
        # "/data/service/hnp/bin/bash: inaccessible or not found"
        # (Error 127); gtk's bare libepoxy/1.5.10 likewise exists on both
        # remotes and the CCI one drags a meson->ninja tool edge that fails
        # with "System is unknown to cmake". Same versions, ohpcd RREVs, so
        # gtk/glib package_id is preserved and their OHOS binaries keep
        # hitting; override=True (transitive-only, not direct requirements).
        self.requires(
            "libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
            override=True,
        )
        self.requires(
            "libepoxy/1.5.10#92f7e70c459ed2e6a96cd82549e82391",
            override=True,
        )

    def build_requirements(self):
        # pkg-config executable provider (xmlsec/1.3.12, ctpl/0.3.5,
        # burp2/2.1.0 precedent): HMBS injects only cmake/make/ninja/
        # python3, so no system pkg-config exists on the device; the
        # mini-configure probes GTK+/libpng via $PKG_CONFIG (default
        # pkg-config) and hard-fails with "Failed to find required GTK+3
        # libraries" without it. The in-repo pkgconf recipe installs only
        # bin/pkgconf (its package() rejects a pkg-config alias), so the
        # recipe exports PKG_CONFIG=<absolute pkgconf path> (which the
        # mini-configure honours) instead of relying on PATH lookup.
        self.tool_requires("pkgconf/3.0.5")

    def _resolve_pkgconf(self):
        """Return absolute path of a runnable pkgconf binary, or "".

        ``isfile`` alone is untrusted on this worker (profile-clang
        precedent), so each candidate must pass ``--version`` with rc==0
        and non-empty stdout (pcre2/10.47 + xmlsec/1.3.12 precedent).
        Preference order: pkgconf tool package bindir, PATH, then the HNP
        preinstalled absolute path. The mini-configure honours an
        absolute $PKG_CONFIG outright, so no pkg-config name shim is
        needed (unlike qconf-style hardcoders).
        """
        cands = []
        try:
            pkg_folder = self.dependencies.build["pkgconf"].package_folder
            cands.append(os.path.join(pkg_folder, "bin", "pkgconf"))
        except Exception:
            pass
        try:
            cands.append(shutil.which("pkgconf") or "")
        except Exception:
            pass
        cands.append(
            "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/bin/pkg-config"
        )
        for cand in cands:
            if cand and self._is_runnable_pkgconf(cand):
                return cand
        return ""

    @staticmethod
    def _is_runnable_pkgconf(candidate):
        if not candidate or not os.path.isfile(candidate):
            return False
        try:
            proc = subprocess.run(
                [candidate, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return False
        return proc.returncode == 0 and bool((proc.stdout or "").strip())

    def _host_search_paths(self):
        """Collect include/lib dirs of all host deps (yudit/3.1.0 precedent).

        The mini-configure handles lcms2/png/jpeg/tiff/z with plain
        ``LIB_NAME <lib>`` (only ``-l<lib>``, no ``pkg-config --cflags``),
        so their headers are found only via $CPPFLAGS and their libs only
        via $LDFLAGS. GTK+/freetype use pkg-config cflags and already work,
        but lcms2 is outside gtk's Requires closure, hence
        ``png.c:58: lcms2.h file not found`` while gtk/png probes pass.
        Aggregate every host dep's includedirs/libdirs (absolute, dedup,
        existing dirs only) instead of hardcoding one package.
        """
        includes, libdirs = [], []
        try:
            hosts = self.dependencies.host.values()
        except Exception:
            hosts = []
        for dep in hosts:
            try:
                pkg_folder = dep.package_folder
            except Exception:
                continue
            if not pkg_folder:
                continue
            try:
                agg = dep.cpp_info.aggregated_components()
            except Exception:
                continue
            try:
                inc_dirs = agg.includedirs
            except Exception:
                inc_dirs = []
            try:
                lib_dirs = agg.libdirs
            except Exception:
                lib_dirs = []
            for folder in inc_dirs:
                path = folder if os.path.isabs(folder) else os.path.join(pkg_folder, folder)
                if os.path.isdir(path) and path not in includes:
                    includes.append(path)
            for folder in lib_dirs:
                path = folder if os.path.isabs(folder) else os.path.join(pkg_folder, folder)
                if os.path.isdir(path) and path not in libdirs:
                    libdirs.append(path)
        return includes, libdirs

    def layout(self):
        basic_layout(self)

    def source(self):
        src = dict(self.conan_data["sources"])
        src.setdefault("filename", "mtpaint_3.50.14.orig.tar.gz")
        get(self, **src, strip_root=True)

    def generate(self):
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        PkgConfigDeps(self).generate()
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        cc, cxx, _label = self._resolve_compiler()
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        # Expose PkgConfigDeps .pc files (generators folder) plus every
        # host dependency's pkgconfig dirs so the mini-configure's
        # `pkg-config gtk+-3.0/libpng/...` probes resolve Conan packages.
        pc_dirs = [self.generators_folder]
        try:
            hosts = self.dependencies.host.values()
        except Exception:
            hosts = []
        for dep in hosts:
            try:
                pkg_folder = dep.package_folder
            except Exception:
                continue
            for sub in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                cand = os.path.join(pkg_folder, *sub)
                if os.path.isdir(cand) and cand not in pc_dirs:
                    pc_dirs.append(cand)
        env.define_path("PKG_CONFIG_PATH", os.pathsep.join(pc_dirs))
        # CPPFLAGS/LDFLAGS for non-pkg-config libs (lcms2/png/jpeg/tiff/z):
        # the mini-configure adds only -l<lib> for them (configure lines
        # `LIB_NAME lcms2/png/...`), and writes
        # `CFLAG = $DEFS $INCLUDES $CPPFLAGS $CFLAGS` /
        # `LDFLAG = ... $LIBS $LDFLAGS`, so Conan include/lib dirs must
        # arrive via $CPPFLAGS/$LDFLAGS. lcms2 is outside gtk's Requires
        # closure, so without this png.c dies with `lcms2.h file not found`.
        includes, libdirs = self._host_search_paths()
        if includes:
            env.define("CPPFLAGS", " ".join("-I%s" % p for p in includes))
        if libdirs:
            env.define("LDFLAGS", " ".join("-L%s" % p for p in libdirs))
        # PKG_CONFIG tool variable (see build_requirements): the
        # mini-configure honours $PKG_CONFIG and defaults to the
        # non-existent `pkg-config` name otherwise. Point it at the
        # pkgconf binary outright (absolute path, no PATH dependence).
        pkgconf = self._resolve_pkgconf()
        if pkgconf:
            env.define("PKG_CONFIG", pkgconf)
        else:
            self.output.warning(
                "mtpaint_hmos_fix: pkgconf binary unresolved; "
                "mini-configure pkg probes will fail"
            )
        env.vars(self, scope="build").save_script("mtpaint_hmos_fix")
        self.output.info(
            "mtpaint_hmos_fix: SHELL=%s TMPDIR=%s CC=%s PKG_CONFIG=%s PKG_CONFIG_PATH entries=%d CPPFLAGS includes=%d LDFLAGS libdirs=%d"
            % (shell, tmpdir, cc, pkgconf, len(pc_dirs), len(includes), len(libdirs))
        )

    def build(self):
        apply_conandata_patches(self)
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        cc, cxx, label = self._resolve_compiler()
        self.output.info(
            "mtpaint build shell=%s tmpdir=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, label, cc, cxx)
        )
        prefix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
            % (shell, shell, tmpdir, tmpdir, tmpdir)
        )
        if cc:
            prefix += 'export CC="%s" && ' % cc
            os.environ["CC"] = cc
        if cxx:
            prefix += 'export CXX="%s" && ' % cxx
            os.environ["CXX"] = cxx
        pc_dirs = [self.generators_folder]
        try:
            hosts = self.dependencies.host.values()
        except Exception:
            hosts = []
        for dep in hosts:
            try:
                pkg_folder = dep.package_folder
            except Exception:
                continue
            for sub in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                cand = os.path.join(pkg_folder, *sub)
                if os.path.isdir(cand) and cand not in pc_dirs:
                    pc_dirs.append(cand)
        pc_path = os.pathsep.join(pc_dirs)
        prefix += 'export PKG_CONFIG_PATH="%s" && ' % pc_path
        os.environ["PKG_CONFIG_PATH"] = pc_path
        # Same CPPFLAGS/LDFLAGS as generate(): manual Makefile path needs
        # them in the shell prefix AND os.environ (configure's MT_TESTCOMP
        # uses $CPPFLAGS/$LDFLAGS for -llcms2/-lpng probes and bakes them
        # into CFLAG/LDFLAG; without them lcms2.h is not found).
        includes, libdirs = self._host_search_paths()
        if includes:
            cppflags = " ".join("-I%s" % p for p in includes)
            prefix += 'export CPPFLAGS="%s" && ' % cppflags
            prev = os.environ.get("CPPFLAGS", "")
            os.environ["CPPFLAGS"] = " ".join(p for p in (prev, cppflags) if p).strip()
        if libdirs:
            ldflags = " ".join("-L%s" % p for p in libdirs)
            prefix += 'export LDFLAGS="%s" && ' % ldflags
            prev = os.environ.get("LDFLAGS", "")
            os.environ["LDFLAGS"] = " ".join(p for p in (prev, ldflags) if p).strip()
        self.output.info(
            "mtpaint build CPPFLAGS includes=%d LDFLAGS libdirs=%d"
            % (len(includes), len(libdirs)))
        pkgconf = self._resolve_pkgconf()
        if pkgconf:
            prefix += 'export PKG_CONFIG="%s" && ' % pkgconf
            os.environ["PKG_CONFIG"] = pkgconf
            self.output.info("mtpaint build PKG_CONFIG=%s" % pkgconf)
        else:
            self.output.warning(
                "mtpaint build: pkgconf binary unresolved; "
                "mini-configure pkg probes will fail"
            )
        self._probe_toolchain(self.source_folder, prefix, shell)
        # Mini-configure options: GTK+3 + release opts; enable jpeg/tiff/
        # lcms2 image support; disable JPEG-2000/WebP (registry scope);
        # no intl/man (binary-only package). R15: no --build/--host.
        conf_cmd = (
            prefix + '"%s" ./configure gtk3 release jpeg tiff lcms2 '
            'nojp2 nowebp --prefix=/' % shell
        )
        self.run(conf_cmd, cwd=self.source_folder, env="conanbuild")
        self.run(prefix + "make -j1", cwd=self.source_folder, env="conanbuild")
        # Upstream has no test suite (audited: no tests/ dir, no check or
        # test target in Makefile/src/Makefile, no test framework
        # registration — see test_package/MANIFEST.yml upstream_test_audit).
        # build() therefore does NOT invoke make check
        # (upstream_test_in_build: false); the HMBS_UPSTREAM_TEST_RESULT
        # status=no_tests evidence is produced by test_package/test.sh in
        # the test phase (re-emitted by test_package/conanfile.py on
        # cache-hit runs).

    def package(self):
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
            % (shell, shell, tmpdir, tmpdir, tmpdir)
        )
        self.run(
            fix + 'make install DESTDIR="%s"' % self.package_folder,
            cwd=self.source_folder,
            env="conanbuild",
        )
        bin_path = os.path.join(self.package_folder, "bin", "mtpaint")
        if not os.path.isfile(bin_path):
            # Fallback: copy the just-linked binary straight from src/.
            cand = os.path.join(self.source_folder, "src", "mtpaint")
            if os.path.isfile(cand):
                os.makedirs(os.path.dirname(bin_path), exist_ok=True)
                shutil.copyfile(cand, bin_path)
                self.output.info("mtpaint package fallback: copied %s" % cand)
        try:
            if os.path.isfile(bin_path):
                os.chmod(bin_path, 0o755)
        except OSError:
            pass
        try:
            self.run('ls -l "%s" 2>&1 || true' % os.path.join(self.package_folder, "bin"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    def _probe_toolchain(self, work_dir, prefix, shell):
        # Best-effort diagnostics only; never fail the build here.
        try:
            try:
                conf_cc = self.conf.get("tools.build:compiler_executables:c", check_type=str) or ""
            except Exception:
                conf_cc = ""
            self.output.info("mtpaint probe: conf CC=%r SHELL=%s" % (conf_cc, shell))
            probe = (
                prefix
                + 'echo "mtpaint probe: CC=$CC PKG_CONFIG=$PKG_CONFIG PKG_CONFIG_PATH=$PKG_CONFIG_PATH"; '
                + 'command -v "$PKG_CONFIG" 2>&1 || command -v pkgconf 2>&1 || true; '
                + '"$PKG_CONFIG" --modversion gtk+-3.0 2>&1 || echo "mtpaint probe: gtk+-3.0 pc NOT found"; '
                + '"$PKG_CONFIG" --modversion libpng 2>&1 || echo "mtpaint probe: libpng pc NOT found"; '
                + '"$CC" --version 2>&1 | head -3 || true'
            )
            self.run(probe, cwd=work_dir, env="conanbuild")
        except Exception as exc:
            self.output.warning("mtpaint probe failed (non-fatal): %s" % exc)

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Keep the profile conf value when the file exists (CI worker
        unchanged); otherwise search PATH plus SDK/harmonybrew candidate
        dirs. Pure isfile probing, no X_OK probing per R49.
        """

        def _ok(path):
            try:
                return bool(path) and os.path.isfile(path)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        if _ok(conf_cc) and not conf_cxx:
            sib = conf_cc + "++" if conf_cc.endswith("clang") else ""
            if _ok(sib):
                return conf_cc, sib, "profile-cxx-sibling"

        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = []
        for cand in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if cand and cand not in cand_dirs:
                cand_dirs.append(cand)
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib_dir = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
                    if sib_dir not in cand_dirs:
                        cand_dirs.append(sib_dir)
        except Exception:
            pass

        found_cc, found_cxx = "", ""
        for name in cc_names:
            which = shutil.which(name)
            if _ok(which):
                found_cc = which
                break
        for name in cxx_names:
            which = shutil.which(name)
            if _ok(which):
                found_cxx = which
                break
        if not found_cc or not found_cxx:
            for cand_dir in cand_dirs:
                try:
                    if not os.path.isdir(cand_dir):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for name in cc_names:
                        cand = os.path.join(cand_dir, name)
                        if _ok(cand):
                            found_cc = cand
                            break
                if not found_cxx:
                    for name in cxx_names:
                        cand = os.path.join(cand_dir, name)
                        if _ok(cand):
                            found_cxx = cand
                            break
                if found_cc and found_cxx:
                    break
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            sib = cc + "++"
            if _ok(sib):
                cxx = sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _usable_shell(self):
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd
