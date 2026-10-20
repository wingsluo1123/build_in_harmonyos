#!/usr/bin/env python3
"""Conan recipe -- profanity 0.18.2 (Meson application).

Profanity is a console based XMPP client written in C (ncurses text UI,
libstrophe for the XMPP wire protocol). Upstream removed Autotools support
in 0.18.0, so Meson is the only build system. All optional features
(notifications, python/c plugins, OTR, PGP, OMEMO, icons, spellcheck)
stay disabled: minimal TUI client using only the required dependencies.

libstrophe 0.14.0 is VENDORED (not `requires`): the upstream `make dist`
release tarball (which ships a pre-generated `configure`, so no autotools
are needed) is downloaded, fixed by pure-Python tls_free ->
strophe_tls_free text replacement (same 6 sites as the in-repo libstrophe
recipe's 5 portability patches, whose copies stay under
patches-libstrophe/ as audit trail), configured
`--disable-shared --enable-static` and statically linked into
bin/profanity. Reason: the libstrophe conan package has no OHOS binary on
the remotes, and its remote recipe dies at `autoreconf -fi` on真机; the
obvious fix (declaring autoconf tool_requires) pulls conancenter m4 whose
configure dies on真机 (`/data/service/hnp/bin/bash: inaccessible or not
found`). The release tarball sidesteps the entire autotools chain.

Upstream tests (meson.build): `meson test` registers two entries,
"unit tests" (cmocka binary `unittests`, built with `-Dtests=true`) and
"functional tests" (`functionaltests` binary, additionally requires the
stabber XMPP stub server plus libutil -- neither exists on OHOS, so that
entry is reported as skipped with evidence in the result marker).
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class ProfanityConan(ConanFile):
    name = "profanity"
    version = "0.18.2"
    description = "Console based XMPP client written in C using ncurses and libstrophe"
    license = "GPL-3.0-or-later"
    homepage = "https://profanity-im.github.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"
    exports_sources = "patches-libstrophe/*"

    # Vendored libstrophe 0.14.0 portability fix: rename tls_free ->
    # strophe_tls_free (avoids the clash with OpenSSL's symbol). Applied by
    # pure-Python text replacement (see _apply_libstrophe_portability_fix),
    # NOT by conan patch(): the git-style a/b headers need strip handling
    # that the conan helper resolves inconsistently across versions, and the
    # 2026-10-19 preflight died with "source/target file does not exist:
    # --- b'a/src/auth.c'". The copies under patches-libstrophe/ are kept
    # as audit trail only.
    _libstrophe_renames = (
        ("src/auth.c", 1),
        ("src/conn.c", 2),
        ("src/tls.h", 1),
        ("src/tls_dummy.c", 1),
        ("src/tls_openssl.c", 1),
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"profanity supports Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        # NOTE: no `self.requires("libstrophe/...")` on purpose -- libstrophe
        # 0.14.0 is vendored (see module docstring): the remote libstrophe
        # package has no OHOS binary and its recipe fails at `autoreconf -fi`
        # on真机. Its build-time deps below stay as regular conan requirements
        # so the vendored configure finds them through PkgConfigDeps:
        # - expat: XML parser backend (same hardened version the in-repo
        #   libstrophe/0.14.0 recipe uses).
        self.requires("expat/2.8.2.1.1")
        self.requires("ncurses/6.6")
        self.requires("readline/8.3")
        # CCI-shadow guard (gfbgraph/0.2.5 + bzrtp/5.3.105 + kyua precedent,
        # same fingerprint as this preflight): bare sqlite3/3.49.1 exists on
        # BOTH remotes (ohpcd manual amalgamation recipe + conancenter CMake
        # recipe) and preflight checks conancenter first, so the conancenter
        # CMake recipe wins and dies in build() with
        # "System is unknown to cmake ... CMAKE_C_COMPILER:
        # /data/service/hnp/bin/clang ... Configuring incomplete".
        # Pin the ohpcd-published RREV of the hardened in-repo recipe
        # (direct clang amalgamation build, HMDFS-safe). Same version, so
        # consumers' package_id is untouched.
        # curl/8.15.0 has no OHOS binary on ohpcd (preflight checks 11
        # cppstd configs, none found) and both the CCI and in-repo 8.15.0
        # recipes die in CMake configure with the same "System is unknown
        # to cmake" fingerprint. Switch to the in-repo hardened 8.15.0.1
        # (zurl/1.12.0 + cairo-dock/3.5.0 + curlcpp/3.1 precedent, ohpcd-only
        # version so no CCI shadow; declares the same zlib/1.3.1.1 +
        # openssl/3.5.6.1 so the overrides below still converge).
        self.requires("curl/8.15.0.1")
        self.requires("sqlite3/3.49.1#669361066cc2c76e0ed897e6b6a27e38")
        # Graph convergence -- curl binary-reuse strategy (3rd strategy cycle):
        # curl/8.15.0.1 declares zlib/1.3.1.1 + openssl/3.5.6.1 (both on
        # ohpcd, matching its published binary manifest) and any rebuild of
        # curl dies in vanilla-CMake configure with "System is unknown to
        # cmake". So converge the whole graph to curl's native deps instead
        # (zlib/1.3.1.1 + openssl/3.5.6.1, both on ohpcd): curl then reuses
        # its binary. The vendored libstrophe below is configured against
        # this same converged set (openssl + expat + zlib via pkg-config),
        # so no second copy of either library enters the link.
        # openssl/3.5.6.1 already carries the narrow FD_SET portability fix.
        # Direct (non-override) requires on purpose: PkgConfigDeps emits
        # .pc files for direct host deps, and the vendored libstrophe
        # configure probes openssl/zlib via pkg-config. Previous rounds kept
        # them as override-only (transitive via curl) and then tried to
        # bypass pkg-config with pre-set _CFLAGS/_LIBS; the generators
        # folder then contained no openssl.pc/zlib.pc, so --exists could
        # never pass. Direct requires keep version convergence (same
        # versions curl declares) while giving the .pc path a chance; the
        # synthesis below covers the case where PkgConfigDeps still skips
        # them (e.g. component-only package_info).
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6.1")
        # CCI-leaf replacement (libtiger/0.3.4 + ayatana-ido/0.10.4-v2 +
        # xwrited/3 precedent, same fingerprint): glib's bare libffi/3.4.4
        # resolves to the CCI recipe on preflight (log applies the CCI-only
        # patch 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the
        # in-repo recipe), whose configure dies with
        # "/data/service/hnp/bin/bash: inaccessible or not found" (Error 127).
        # Pin the ohpcd-published RREV of the hardened in-repo recipe.
        # Same version, so glib's package_id is untouched (a 3.5.2 swap
        # would force a glib source rebuild).
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
                      override=True)

    def build_requirements(self):
        # meson is pure-Python (no compilation). ninja is NOT declared here
        # on purpose: declaring tool_requires("ninja/...") forces conan to
        # build ninja from source for the OHOS context, whose vanilla CMake
        # configure dies with "System is unknown to cmake" for
        # CMAKE_SYSTEM_NAME=HarmonyOS (preflight 2026-10-19, both 1.12.1 and
        # 1.13.2). Precedent archives/q/qdl/2.7 + archives/v/vali/0.1.1 +
        # archives/c/cairo/1.18.4.2: meson-only tool_requires, ninja comes
        # from the HMBS-provided system toolchain (HMBS_BUILD_TOOLS.ninja
        # prepended to PATH + /data/service/hnp/bin/ninja).
        self.tool_requires("meson/1.11.0")
        # pkgconf via the build context (zurl/1.12.0 notes #36 precedent):
        # HMBS injects only cmake/make/ninja/python3 -- there is NO system
        # pkg-config on真机 (proven 2026-10-19: which/conf/compiler-bindir +
        # well-known dirs all missed). The vendored libstrophe ./configure
        # (PKG_PROG_PKG_CONFIG + PKG_CHECK_MODULES openssl/expat/zlib, the
        # latter with no fallback) and meson setup both need a real
        # pkg-config binary. pkgconf/3.0.5 is Meson-built plain C and resolves
        # on真机 (same version zurl uses); it ships bin/pkgconf only, so the
        # recipe resolves its absolute path and exports PKG_CONFIG + injects
        # it into the meson native/cross files (never relies on a bare name).
        self.tool_requires("pkgconf/3.0.5")
        # cmocka only builds the upstream `unittests` binary, never ships.
        self.test_requires("cmocka/2.0.2")
        # NOTE: deliberately NO autoconf/automake/libtool here. The vendored
        # libstrophe comes from the upstream `make dist` release tarball
        # whose `configure` is pre-generated. (Previous round declared
        # autoconf/2.72: its conancenter m4 dependency dies on真机 with
        # `/data/service/hnp/bin/bash: inaccessible or not found`, Error 127.)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored libstrophe 0.14.0 release tarball (ships pre-generated
        # `configure`). Patched right after download so every later build()
        # run starts from an already-portable tree.
        ls_dest = os.path.join(self.source_folder, "libstrophe-src")
        get(self, **self.conan_data["libstrophe_sources"],
            destination=ls_dest, strip_root=True)
        ls_src = self._locate_libstrophe_src(ls_dest)
        self._apply_libstrophe_portability_fix(ls_src)

    def _apply_libstrophe_portability_fix(self, ls_src):
        """Rename tls_free -> strophe_tls_free by text replacement.

        Same semantic as the in-repo libstrophe/0.14.0 patches/0001~0005
        (verified byte-identical intent: 6 call/definition sites across 5
        files), but immune to unified-diff strip-level/CRLF/fuzz issues:
        the 2026-10-19 preflight failed inside conan patch() with
        "source/target file does not exist: --- b'a/src/auth.c'" even
        though the marker locator had already found the correct source
        root. Word-boundary regex avoids touching an already-patched tree
        (idempotent: re-running source() over a cached tree is a no-op).
        Raises on missing file or unexpected occurrence count instead of
        silently continuing.
        """
        for _rel, _expected in self._libstrophe_renames:
            _path = os.path.join(ls_src, _rel)
            if not os.path.isfile(_path):
                raise RuntimeError(
                    "vendored libstrophe: expected file missing: %s "
                    "(source root %s)" % (_rel, ls_src))
            with open(_path, "rb") as _handle:
                _raw = _handle.read()
            _text = _raw.decode("utf-8", errors="strict")
            _done, _n = re.subn(r"\btls_free\b", "strophe_tls_free", _text)
            if _n == 0:
                # Already patched (e.g. source() re-run over cached tree):
                # the new symbol must be present, otherwise the tree is
                # unexpected -- refuse to silently continue.
                if "strophe_tls_free" not in _text:
                    raise RuntimeError(
                        "vendored libstrophe: no tls_free occurrence in "
                        "%s, and strophe_tls_free absent too" % _rel)
                self.output.info(
                    "vendored libstrophe: %s already patched, skipping" % _rel)
                continue
            if _n != _expected:
                raise RuntimeError(
                    "vendored libstrophe: %s: replaced %d tls_free "
                    "occurrences, expected %d -- tree differs from 0.14.0, "
                    "refusing to guess" % (_rel, _n, _expected))
            with open(_path, "w", encoding="utf-8", newline="") as _handle:
                # newline="" disables translation: _done already carries
                # the original CRLF/LF bytes, written back verbatim.
                _handle.write(_done)
            self.output.info(
                "vendored libstrophe: %s: tls_free -> strophe_tls_free x%d"
                % (_rel, _n))

    def _locate_libstrophe_src(self, dest):
        """Locate the real libstrophe source root by marker files.

        Do not assume the `get(destination=..., strip_root=True)` layout:
        locate the directory containing both `configure` and `src/auth.c`
        (search dest itself, then 1-2 levels of subdirectories). Raises with
        a directory listing when the markers are nowhere to be found.
        """
        markers = ("configure", os.path.join("src", "auth.c"))
        candidates = [dest]
        try:
            entries = sorted(os.listdir(dest))
        except OSError:
            entries = []
        for _entry in entries:
            _full = os.path.join(dest, _entry)
            if os.path.isdir(_full):
                candidates.append(_full)
                try:
                    _sub = sorted(os.listdir(_full))
                except OSError:
                    continue
                for _s in _sub:
                    _sfull = os.path.join(_full, _s)
                    if os.path.isdir(_sfull):
                        candidates.append(_sfull)
        for _cand in candidates:
            if all(os.path.isfile(os.path.join(_cand, _m)) for _m in markers):
                if os.path.realpath(_cand) != os.path.realpath(dest):
                    self.output.info(
                        "vendored libstrophe source root: %s" % _cand)
                return _cand
        raise RuntimeError(
            "vendored libstrophe: markers %s not found under %s "
            "(top entries: %s)" % (markers, dest, entries))

    def generate(self):
        # CI/worker may export AR/AS/STRIP/NM/RANLIB as bare llvm-* names
        # (see ci/conan/build_and_test.sh conf_map). Those names live in
        # /data/service/hnp/bin, not on the default PATH; if MesonToolchain
        # copies them verbatim into conan_meson_native.ini [binaries], meson
        # reports "Program 'llvm-ar' not found". Clear first, rewrite below
        # with absolute paths (qdl/2.7 precedent).
        for var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(var, None)
        self._fix_meson_launcher()
        tc = MesonToolchain(self)
        # Minimal client: upstream optional features default to disabled.
        # Boolean option `tests` builds the cmocka `unittests` binary.
        tc.project_options["tests"] = "true"
        # ar/ranlib via official tc.binaries API (qdl/2.7 + vali/0.1.1 +
        # aml/1.0.0 + cairo/1.18.4 precedent): MesonToolchain omits them from
        # the native file and meson falls back to bare-name probing, while
        # the OHOS toolchain names them llvm-ar/llvm-ranlib.
        compiler_exes = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compiler_exes.get("c", "")
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        import shutil as _shutil
        for meson_name, candidates in (("ar", ("llvm-ar", "ar")),
                                       ("ranlib", ("llvm-ranlib", "ranlib"))):
            found = None
            if bindir and os.path.isdir(bindir):
                for name in candidates:
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        found = cand
                        break
            if not found:
                for name in candidates:
                    found = _shutil.which(name)
                    if found:
                        break
            if found:
                tc.binaries[meson_name] = found
        # True device migrated clang from /data/service/hnp/bin to
        # ~/usr/local/bin (zydis/4.1.1 precedent): the shared profile still
        # points at the old path, so meson setup dies with
        # "Unknown compiler(s): [['/data/service/hnp/bin/clang']]".
        # Resolve the real compiler tool-specifically and pin via the
        # official tc.binaries API (pax-utils/1.3.10 precedent); only
        # override when the configured path is missing and the resolved
        # one exists (CI workers untouched).
        def _resolve_comp(_configured, _names):
            if _configured and os.path.isfile(_configured):
                return _configured
            for _n in _names:
                _w = _shutil.which(_n)
                if _w:
                    return _w
            _home_bin = os.path.join(os.path.expanduser("~"), "usr",
                                     "local", "bin")
            for _n in _names:
                _cand = os.path.join(_home_bin, _n)
                if os.path.isfile(_cand):
                    return _cand
            return None
        _c = _resolve_comp(compiler_exes.get("c", ""),
                           ("clang", "cc", "gcc"))
        _cxx = _resolve_comp(compiler_exes.get("cpp", ""),
                             ("clang++", "c++", "g++"))
        if _c:
            tc.binaries["c"] = _c
            self.output.info("meson ini: c = '%s'" % _c)
        else:
            self.output.warning(
                "meson c compiler not resolved; leaving profile default")
        if _cxx:
            tc.binaries["cpp"] = _cxx
            self.output.info("meson ini: cpp = '%s'" % _cxx)
        tc.generate()
        self._inject_pkg_config_into_meson_ini()
        # Post-generate guard: MesonToolchain may still have baked the stale
        # profile path into the ini files (zydis _fix_generated_toolchain
        # precedent for CMake). Rewrite any missing absolute compiler path
        # with the resolved one so `meson setup` never sees a dead clang.
        self._fix_meson_compilers(_c, _cxx)

    def _resolve_pkg_config(self):
        """Resolve an absolute pkg-config/pkgconf binary (never bare name).

        Order: pkgconf build-context package (tool_requires below) -> conf
        tools.gnu:pkg_config -> PATH -> well-known absolute dirs. The
        2026-10-19 preflight proved there is NO system pkg-config on真机
        (bare `pkg-config` died with "inaccessible or not found", Error 127,
        and every system probe missed), so the primary source is the
        pkgconf/3.0.5 tool_requires (zurl/1.12.0 notes #36 precedent), which
        ships bin/pkgconf only -- hence the absolute path is exported via
        $PKG_CONFIG and injected into the meson ini files.
        """
        import shutil as _shutil
        try:
            _build_deps = self.dependencies.build
        except Exception:
            _build_deps = {}
        try:
            _pkgconf = _build_deps.get("pkgconf") if _build_deps else None
        except Exception:
            _pkgconf = None
        _folder = getattr(_pkgconf, "package_folder", None) if _pkgconf else None
        if _folder:
            for _name in ("pkgconf", "pkg-config"):
                _cand = os.path.join(_folder, "bin", _name)
                if os.path.isfile(_cand):
                    return _cand
        try:
            _conf = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            _conf = None
        if _conf and os.path.isfile(str(_conf)):
            return str(_conf)
        for _name in ("pkg-config", "pkgconf"):
            _w = _shutil.which(_name)
            if _w:
                return _w
        try:
            _cex = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            _cex = {}
        _cc = _cex.get("c", "") if isinstance(_cex, dict) else ""
        _bindir = os.path.dirname(_cc) if os.path.sep in str(_cc) else ""
        _dirs = ([_bindir] if _bindir else []) + [
            "/data/service/hnp/bin",
            "/storage/Users/currentUser/usr/local/bin",
            "/usr/local/bin",
            "/usr/bin",
        ]
        for _d in _dirs:
            for _name in ("pkg-config", "pkgconf"):
                _cand = os.path.join(_d, _name)
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    return _cand
        return None

    def _inject_pkg_config_into_meson_ini(self):
        """Write the absolute pkg-config path into meson native/cross files.

        MesonToolchain omits pkg-config for cross builds, so meson reports
        "Found pkg-config: NO" and cannot see the PkgConfigDeps .pc files
        (glib/2.84.0.1 _inject_meson_binaries precedent). Resolved once here
        via _resolve_pkg_config; warn-only when absent (the vendored
        libstrophe build below fails fast with the searched paths instead).
        """
        pkg_config = self._resolve_pkg_config()
        if not pkg_config:
            self.output.warning(
                "pkg-config/pkgconf not found on PATH; meson may report "
                "'Found pkg-config: NO'")
            return
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            try:
                with open(nf, encoding="utf-8") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "[binaries]" not in content:
                continue
            if "\npkg-config =" in content or "\npkgconfig =" in content:
                continue
            content = content.replace(
                "[binaries]\n",
                "[binaries]\npkg-config = '%s'\n" % pkg_config, 1)
            try:
                with open(nf, "w", encoding="utf-8") as handle:
                    handle.write(content)
            except OSError as exc:
                self.output.warning(
                    "meson ini pkg-config injection failed for %s: %s"
                    % (nf_name, exc))
                continue
            self.output.info(
                "meson ini %s: pkg-config = '%s'" % (nf_name, pkg_config))

    def _fix_meson_compilers(self, c, cxx):
        """Rewrite stale absolute clang paths baked into meson ini files.

        MesonToolchain copies tools.build:compiler_executables verbatim
        into conan_meson_native/cross.ini [binaries] c/cpp. When the
        profile still points at /data/service/hnp/bin/clang but the true
        device migrated clang to ~/usr/local/bin, meson setup dies with
        "Unknown compiler(s)" (this round's evidence). Only rewrites when
        the baked path is missing and the resolved one exists.
        """
        try:
            _cex = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            _cex = {}
        pairs = []
        for _old, _new in ((_cex.get("c", ""), c),
                           (_cex.get("cpp", ""), cxx)):
            if _old and _new and _old != _new \
                    and not os.path.isfile(_old) \
                    and os.path.isfile(_new):
                pairs.append((_old, _new))
        if not pairs:
            return
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            try:
                with open(nf, encoding="utf-8") as handle:
                    content = handle.read()
            except OSError:
                continue
            orig = content
            for _old, _new in pairs:
                content = content.replace(_old, _new)
            if content != orig:
                try:
                    with open(nf, "w", encoding="utf-8") as handle:
                        handle.write(content)
                except OSError as exc:
                    self.output.warning(
                        "meson ini compiler fix failed for %s: %s"
                        % (nf_name, exc))
                    continue
                self.output.info(
                    "meson ini %s: compiler path fix %s" % (nf_name, pairs))

    def _fix_meson_launcher(self):
        """Rewrite the conan meson launcher shebang-free (qdl/2.7 precedent).

        On OHOS, conan run() goes through Python subprocess and execve of a
        sandboxed `#!` script fails with EACCES ("bad interpreter: Permission
        denied", Error 126). meson/1.11.0 bin/meson is exactly such a script.
        Dropping the shebang line lets POSIX shells fall back to interpreting
        it as a shell script (conan run() uses /bin/sh -c). Idempotent: if
        the first line is already not `#!`, touch nothing.
        """
        launcher = self._locate_meson_launcher()
        if not launcher:
            self.output.warning("meson launcher not found; skipping shebang fix")
            return
        try:
            with open(launcher, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            self.output.warning("meson launcher unreadable: %s (%s)" % (launcher, exc))
            return
        if not raw.startswith(b"#!"):
            self.output.info("meson launcher already shebang-free: %s" % launcher)
            return
        body = raw.split(b"\n", 1)[1] if b"\n" in raw else b""
        if not body.strip():
            self.output.warning("meson launcher has an empty body, not touching it")
            return
        backup = launcher + ".conan-orig"
        if not os.path.exists(backup):
            try:
                with open(backup, "wb") as handle:
                    handle.write(raw)
            except OSError as exc:
                self.output.warning("meson launcher backup failed: %s" % exc)
        tmp = launcher + ".conan-tmp"
        try:
            with open(tmp, "wb") as handle:
                handle.write(body)
            os.chmod(tmp, 0o775)
            os.replace(tmp, launcher)
        except OSError as exc:
            self.output.warning("meson launcher rewrite failed: %s (%s)" % (launcher, exc))
            try:
                os.remove(tmp)
            except OSError:
                pass

    def _locate_meson_launcher(self):
        import shutil as _shutil
        import glob as _glob
        try:
            dep = self.dependencies.build.get("meson")
        except Exception:
            dep = None
        if dep is not None and getattr(dep, "package_folder", None):
            candidate = os.path.join(dep.package_folder, "bin", "meson")
            if os.path.isfile(candidate):
                return candidate
        which = _shutil.which("meson")
        if which:
            return which
        pattern = os.path.join(
            os.environ.get("CONAN_HOME") or os.path.join(
                os.path.expanduser("~"), ".conan2"),
            "p", "*", "p", "bin", "meson")
        hits = sorted(_glob.glob(pattern))
        return hits[0] if hits else None

    def build(self):
        apply_conandata_patches(self)
        self._build_vendored_libstrophe()
        meson = Meson(self)
        meson.configure()
        # NOTE: Conan 2.x Meson helper exposes build(), not compile()
        # (compile() is the CMake helper name; ADAPTATION_GUIDE §4.4 template
        # still shows the Conan 1.x spelling -- unudhcpd/0.2.1-r2 + turnstile
        # precedent). Using compile() dies with
        # "AttributeError: 'Meson' object has no attribute 'compile'".
        self._fix_profanity_config_h()
        # 2026-10-19 preflight dropped SSH at [69/79] with no compiler
        # error ("Connection closed by remote host"): force serial ninja
        # (--jobs 1, gfbgraph/0.2.5 serial-make precedent extended to
        # meson) plus --verbose so every TU prints (SSH keepalive, avoids
        # idle-timeout kills on the slow single-job device).
        self._meson_build_serial(meson)
        self._build_unittests_target(meson)
        self._run_upstream_tests()

    def _meson_build_serial(self, meson):
        """Serial `meson compile` with keepalive output.

        Prefers the Meson helper (it already honours HMBS
        tools.build:jobs=1); when the helper signature offers no
        target/jobs knob, falls back to the resolved launcher with
        explicit `--jobs 1 --verbose`. No source/test change, only the
        build invocation shape.
        """
        _launcher = self._locate_meson_launcher()
        if _launcher:
            self.run('"%s" compile -C "%s" --jobs 1 --verbose'
                     % (_launcher, self.build_folder), env="conanbuild")
            return
        meson.build()

    def _build_unittests_target(self, meson):
        """Explicitly build the `unittests` target (build_by_default:false).

        Upstream meson.build declares both `unittests` and
        `functionaltests` with `build_by_default: false`, so a plain
        `meson.build()` (ninja default targets, 79 targets: only
        profanity.p objects) never produces the test binary and
        `_run_upstream_tests()` died with "not found in build tree".
        Try the Meson helper target API first, fall back to
        `meson compile -C <build> unittests` with the resolved launcher.
        """
        import inspect as _inspect
        try:
            _sig = _inspect.signature(meson.build)
            if "target" in _sig.parameters:
                meson.build(target="unittests")
                return
        except Exception as exc:
            self.output.info(
                "unittests target build: helper-target probe failed (%s), "
                "falling back to meson compile" % exc)
        _launcher = self._locate_meson_launcher()
        if not _launcher:
            raise RuntimeError(
                "upstream unittests: meson launcher not found, cannot build "
                "the non-default 'unittests' target")
        self.run('"%s" compile -C "%s" --jobs 1 --verbose unittests'
                 % (_launcher, self.build_folder), env="conanbuild")

    def _fix_profanity_config_h(self):
        """Force ncurses header macro when meson has_header probes miss.

        Upstream meson.build probes ncurses via bare
        cc.has_header('ncursesw/ncurses.h') / ('ncurses.h') with NO
        dependencies argument, so the conan ncurses include dir is invisible
        to the probe on OHOS cross builds (on Linux the headers live in
        /usr/include and the probe passes). When both probes fail, generated
        config.h defines neither HAVE_NCURSESW_NCURSES_H nor HAVE_NCURSES_H,
        win_types.h then includes NO curses header at all -> 'unknown type
        name WINDOW'. The missing curses header also removes the transitive
        <stdbool.h> (ncurses curses.h includes it), so xmpp.h's bare `bool`
        fails with 'unknown type name bool' in the same TU (calcurse/4.6.0
        same fingerprint precedent: force HAVE_NCURSES_H). Compile already
        has -I ncurses/include via pkg-config deps (see preflight ninja
        line), so defining the macro is sufficient -- no include-path change
        needed. Probes the real ncurses package layout to pick which macro
        to define; refuses to guess when no header exists on disk.
        """
        try:
            ncurses_dep = self.dependencies["ncurses"]
            ncurses_root = str(getattr(ncurses_dep, "package_folder", "") or "")
        except Exception:
            ncurses_root = ""
        inc = os.path.join(ncurses_root, "include") if ncurses_root else ""
        has_wsub = os.path.isfile(os.path.join(inc, "ncursesw", "ncurses.h")) if inc else False
        has_top = os.path.isfile(os.path.join(inc, "ncurses.h")) if inc else False
        has_curses = os.path.isfile(os.path.join(inc, "curses.h")) if inc else False
        if has_wsub:
            macro = "HAVE_NCURSESW_NCURSES_H"
        elif has_top:
            macro = "HAVE_NCURSES_H"
        elif has_curses:
            macro = "HAVE_CURSES_H"
        else:
            raise RuntimeError(
                "profanity config.h fix: no ncurses header found under '%s' "
                "(probed ncursesw/ncurses.h, ncurses.h, curses.h)" % inc)
        hits = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "config.h" in files:
                hits.append(os.path.join(root, "config.h"))
        hits = sorted(hits)
        if not hits:
            raise RuntimeError(
                "profanity config.h fix: no config.h found under build_folder "
                "'%s' after meson.configure()" % self.build_folder)
        target = None
        for cand in hits:
            try:
                with open(cand, encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            if "PACKAGE_NAME" in text and "profanity" in text:
                target = cand
                break
        if target is None:
            target = hits[0]
        with open(target, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        if ("#define HAVE_NCURSESW_NCURSES_H" in text
                or "#define HAVE_NCURSES_H" in text
                or "#define HAVE_CURSES_H" in text):
            self.output.info(
                "profanity config.h already defines a curses macro, leaving %s"
                % target)
            return
        undef_line = "#undef %s" % macro
        define_line = "#define %s 1" % macro
        if undef_line in text:
            text = text.replace(undef_line, define_line, 1)
        elif "/* #undef %s */" % macro in text:
            text = text.replace("/* #undef %s */" % macro, define_line, 1)
        else:
            text = text.rstrip("\n") + "\n%s\n" % define_line
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        self.output.info(
            "profanity config.h fix: defined %s in %s (ncurses include %s)"
            % (macro, target, inc))

    def _dep_package_folder(self, dep_name):
        try:
            dep = self.dependencies[dep_name]
        except Exception as exc:
            raise RuntimeError(
                "vendored libstrophe: dependency '%s' missing from graph (%s)"
                % (dep_name, exc))
        folder = str(getattr(dep, "package_folder", "") or "")
        if not folder or not os.path.isdir(folder):
            raise RuntimeError(
                "vendored libstrophe: package_folder for '%s' not found "
                "(got '%s')" % (dep_name, folder))
        return dep, folder

    def _find_header_includedir(self, package_folder, header_rel, dep_name):
        """Locate header under package_folder; return (includedir, hit).

        includedir is the directory to pass as -I: for 'openssl/ssl.h' it
        is the parent of the 'openssl/' dir; for flat headers ('zlib.h')
        it is the containing dir. Recursive walk, deterministic (sorted).
        """
        target = header_rel.replace("/", os.sep)
        hits = []
        for root, _dirs, files in os.walk(package_folder):
            _dirs.sort()
            for _f in sorted(files):
                full = os.path.join(root, _f)
                try:
                    rel = os.path.relpath(full, package_folder)
                except ValueError:
                    continue
                if rel.replace(os.sep, "/") == header_rel:
                    hits.append(full)
                    break
            if hits:
                break
        if not hits:
            searched = package_folder
            raise RuntimeError(
                "vendored libstrophe: header '%s' for dep '%s' not found "
                "under package_folder '%s'" % (header_rel, dep_name,
                                               searched))
        hit = hits[0]
        if "/" in header_rel:
            top = header_rel.split("/")[0]
            # hit = <includedir>/<top>/...; strip back to <includedir>.
            idx = hit.replace(os.sep, "/").rfind("/" + top + "/")
            if idx >= 0:
                incdir = hit[:idx].replace("/", os.sep)
            else:
                incdir = os.path.dirname(hit)
        else:
            incdir = os.path.dirname(hit)
        return incdir, hit

    def _find_libdir_with(self, package_folder, lib_basenames, dep_name):
        """Return libdir containing one of lib_basenames (sorted walk)."""
        wanted = set(lib_basenames)
        for root, _dirs, files in os.walk(package_folder):
            _dirs.sort()
            sfiles = set(files)
            for _w in sorted(wanted):
                if _w in sfiles:
                    return root
        raise RuntimeError(
            "vendored libstrophe: none of %s for dep '%s' found under "
            "package_folder '%s'" % (sorted(wanted), dep_name,
                                     package_folder))

    def _ensure_dep_pcs(self):
        """Synthesize the missing openssl.pc / zlib.pc in generators_folder.

        Strategy-cycle-8 different route: rounds 5-7 all kept the same
        assumption (feed configure via pre-set openssl/zlib/expat
        _CFLAGS/_LIBS bypass) and iterated only on how to compute those
        flags from cpp_info (bare lookup -> absolute pkgconf ->
        aggregated_components + package_folder/include fallback). All
        three failed at flag computation: cpp_info.includedirs holds
        relative 'include' entries dropped by the isabs filter, and
        aggregated_components() merges only component fields (openssl
        components set libs only, no includes), so the probe list stayed
        empty and raised 'header not found (includedirs=[])'.
        This round abandons the bypass entirely: write real .pc files so
        the stock PKG_CHECK_MODULES path in configure works unchanged.
        Sources are deterministic (package_folder recursive header/lib
        search); no stdout counting, no arithmetic.
        """
        import glob as _glob
        specs = (
            ("openssl", "openssl/ssl.h",
             ("libssl.a", "libssl.so", "ssl.lib"),
             ("libcrypto.a", "libcrypto.so", "crypto.lib"),
             ("ssl", "crypto"), ("dl", "pthread"), "3.5.6.1",
             "OpenSSL TLS library (conan vendored)"),
            ("zlib", "zlib.h",
             ("libz.a", "libz.so", "z.lib"), (),
             ("z",), (), "1.3.1.1",
             "zlib compression (conan vendored)"),
        )
        for (dep_name, header, libs_a, libs_b, link_names,
                sys_names, version, descr) in specs:
            pc_path = os.path.join(self.generators_folder,
                                   "%s.pc" % dep_name)
            if os.path.isfile(pc_path):
                self.output.info(
                    "vendored libstrophe: %s.pc already present, "
                    "leaving untouched" % dep_name)
                continue
            _dep, pf = self._dep_package_folder(dep_name)
            incdir, hit = self._find_header_includedir(
                pf, header, dep_name)
            libdir = None
            for _want in (libs_a, libs_b):
                if not _want:
                    continue
                try:
                    libdir = self._find_libdir_with(pf, _want, dep_name)
                    break
                except RuntimeError:
                    continue
            if libdir is None:
                # Fall back to package lib dir if archive names differ.
                cand = os.path.join(pf, "lib")
                if os.path.isdir(cand):
                    libdir = cand
                else:
                    raise RuntimeError(
                        "vendored libstrophe: libdir for '%s' not found "
                        "under '%s'" % (dep_name, pf))
            cflags = "-I%s" % incdir
            linklibs = "-L%s %s %s" % (
                libdir,
                " ".join("-l%s" % _n for _n in link_names),
                " ".join("-l%s" % _n for _n in sys_names))
            linklibs = " ".join(linklibs.split())
            pc = (
                "prefix=%s\n"
                "libdir=%s\n"
                "includedir=%s\n"
                "\n"
                "Name: %s\n"
                "Description: %s\n"
                "Version: %s\n"
                "Libs: %s\n"
                "Cflags: %s\n"
            ) % (pf, libdir, incdir, dep_name, descr, version,
                 linklibs, cflags)
            with open(pc_path, "w", encoding="utf-8") as handle:
                handle.write(pc)
            self.output.info(
                "vendored libstrophe: wrote %s (header %s, libdir %s)"
                % (pc_path, hit, libdir))
        # Inventory for the next preflight to distinguish
        # 'not generated' from 'not on path'.
        try:
            pcs = sorted(_glob.glob(os.path.join(
                self.generators_folder, "*.pc")))
            self.output.info(
                "vendored libstrophe: generators .pc inventory: %s"
                % [_p and os.path.basename(_p) for _p in pcs])
        except Exception:
            pass

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        arch_triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        if arch not in arch_triplets:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return arch_triplets[arch]

    def _prepare_libstrophe_env(self):
        """Shared tmpdir + accessible shell (in-repo libstrophe pattern).

        CONFIG_SHELL/SHELL are pinned to /bin/sh: HMBS guarantees
        shell=/bin/sh (see HMBS_PLATFORM_CAPABILITIES) while the stock
        autotools default (`/data/service/hnp/bin/bash`) is inaccessible
        inside the真机 sandbox (m4/1.4.19 precedent, Error 127). The local
        `which bash` probe is meaningless (it probes the Windows dev
        machine, not真机), so pin unconditionally. NOTE: os.environ alone
        does NOT survive `self.run(..., env="conanbuild")` -- the conanbuild
        aggregation re-injects the profile SHELL -- so callers must also
        pass CONFIG_SHELL/SHELL as `./configure` VAR=value assignments
        (see _build_vendored_libstrophe).
        """
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        # Static archive linked into a (possibly PIE) executable: PIC objects.
        cflags = os.environ.get("CFLAGS", "")
        if "-fPIC" not in cflags and "-fpic" not in cflags:
            os.environ["CFLAGS"] = (cflags + " -fPIC").strip()
        return "/bin/sh"

    def _build_vendored_libstrophe(self):
        """Configure, build and install libstrophe 0.14.0 into build prefix.

        The release tarball already contains `configure`, so this runs the
        stock autotools configure directly (no autoreconf, no autotools
        packages needed) with an accessible CONFIG_SHELL.

        Static-only (`--disable-shared --enable-static`): libstrophe.a is
        linked into bin/profanity, so the app package ships no extra .so and
        needs no runtime search path. A hand-written `libstrophe.pc` is
        dropped into the generators folder so Meson's
        `dependency('libstrophe')` resolves via the PkgConfigDeps
        PKG_CONFIG_PATH that is already active during `meson setup`.
        """
        import shutil as _shutil
        import glob as _glob
        ls_src = self._locate_libstrophe_src(
            os.path.join(self.source_folder, "libstrophe-src"))
        ls_prefix = os.path.join(self.build_folder, "ls-prefix")
        os.makedirs(ls_prefix, exist_ok=True)
        self._prepare_libstrophe_env()
        # The `make dist` release tarball ships a pre-generated `configure`:
        # assert its presence instead of bootstrapping (no autotools chain).
        _cfg = os.path.join(ls_src, "configure")
        if not os.path.isfile(_cfg):
            raise RuntimeError(
                "vendored libstrophe: pre-generated configure missing in "
                f"{ls_src}; refusing to bootstrap (autotools chain is "
                "unavailable on真机)")
        # umask 077 breaks config.status tempdir creation under HMDFS
        # permission semantics (same fix as the in-repo libstrophe recipe).
        try:
            with open(_cfg, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as handle:
                    handle.write(text.replace("umask 077", "umask 007"))
        except OSError:
            pass
        host_triplet = self._gnu_triplet()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        # Stock pkg-config path (no _CFLAGS/_LIBS bypass): the vendored
        # configure probes openssl/expat/zlib via PKG_CHECK_MODULES.
        # 2026-10-19 preflight evidence: absolute pkgconf runs, but
        # generators_folder contained NO openssl.pc / zlib.pc (visible
        # .pc: cmocka,expat,glib,...,libcurl,ncursesw,readline,sqlite3).
        # Rounds 5-7 kept feeding pre-set _CFLAGS/_LIBS computed from
        # cpp_info and failed at flag computation (relative 'include'
        # dropped by isabs filter; aggregated_components merges only
        # component libs, no includes -> includedirs=[]). This round
        # synthesizes the two missing .pc files from package_folder disk
        # search (see _ensure_dep_pcs), then lets configure use pkg-config
        # normally. expat.pc already exists via PkgConfigDeps and is left
        # untouched.
        self._ensure_dep_pcs()
        # Wire PKG_CONFIG_PATH explicitly: generators_folder first, so the
        # synthesized openssl.pc/zlib.pc plus PkgConfigDeps expat.pc are
        # all visible to the absolute pkgconf binary resolved below.
        _pkgconf_bin = self._resolve_pkg_config()
        if not _pkgconf_bin:
            raise RuntimeError(
                "vendored libstrophe: no pkg-config/pkgconf binary found "
                "(searched pkgconf tool_requires, conf, PATH, "
                "/data/service/hnp/bin)")
        _pc_path = self.generators_folder + os.pathsep + os.environ.get(
            "PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = _pc_path
        os.environ["PKG_CONFIG"] = _pkgconf_bin
        self.output.info(
            "vendored libstrophe: PKG_CONFIG=%s PKG_CONFIG_PATH=%s"
            % (_pkgconf_bin, _pc_path))
        # Fail fast with evidence (not silently TLS-less): verify the
        # three modules resolve before running the 1000-line configure.
        _probe = subprocess.run(
            [_pkgconf_bin, "--exists", "--print-errors",
             "openssl", "expat", "zlib"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=dict(os.environ))
        self.output.info(
            "vendored libstrophe: pkgconf --exists openssl expat zlib "
            "exit=%s output=%s" % (_probe.returncode,
                                   (_probe.stdout or "").strip()[-2000:]))
        if _probe.returncode != 0:
            raise RuntimeError(
                "vendored libstrophe: pkgconf --exists openssl expat zlib "
                "failed (exit %s): %s" % (_probe.returncode,
                                          (_probe.stdout or "").strip()))
        # LDFLAGS: keep conan dep libdirs ahead of ambient -L entries (same
        # lcalc-style reasoning as the in-repo recipe) via configure argument.
        _lp = " ".join("-L{}".format(_d)
                       for _ref, _dep in self.dependencies.items()
                       for _d in (_dep.cpp_info.libdirs or [])
                       if os.path.isabs(_d))
        # `make` needs AR/RANLIB: bare `ar` may not exist on PATH (OHOS
        # toolchain names are llvm-ar/llvm-ranlib), so resolve absolute
        # paths the same way generate() does and pass them to configure.
        _ar = _ranlib = None
        _cex = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        _cc = _cex.get("c", "")
        _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
        for _var, _names in (("_ar", ("llvm-ar", "ar")),
                             ("_ranlib", ("llvm-ranlib", "ranlib"))):
            if _bindir:
                for _n in _names:
                    _cand = os.path.join(_bindir, _n)
                    if os.path.isfile(_cand):
                        if _var == "_ar":
                            _ar = _cand
                        else:
                            _ranlib = _cand
                        break
            if ((_var == "_ar" and _ar is None)
                    or (_var == "_ranlib" and _ranlib is None)):
                for _n in _names:
                    _w = _shutil.which(_n)
                    if _w:
                        if _var == "_ar":
                            _ar = _w
                        else:
                            _ranlib = _w
                        break
        configure_cmd = (
            'CONFIG_SHELL="/bin/sh" SHELL="/bin/sh" '
            'PKG_CONFIG="%s" PKG_CONFIG_PATH="%s" ' % (_pkgconf_bin, _pc_path) +
            "./configure "
            f"--prefix={ls_prefix} "
            f"--build={build_triplet} --host={host_triplet} "
            "--disable-examples --disable-fuzzing "
            "--disable-shared --enable-static"
        )
        if _lp:
            configure_cmd += f' LDFLAGS="{_lp} $LDFLAGS"'
        # No _CFLAGS/_LIBS bypass: configure resolves openssl/expat/zlib
        # via the (now complete) .pc set through PKG_CONFIG/PKG_CONFIG_PATH
        # (both os.environ and the VAR=value prefix above, so they survive
        # env="conanbuild" aggregation which otherwise re-injects the
        # inaccessible /data/service/hnp/bin/bash as SHELL).
        if _ar:
            configure_cmd += f' AR="{_ar}"'
        if _ranlib:
            configure_cmd += f' RANLIB="{_ranlib}"'
        self.run(configure_cmd, cwd=ls_src, env="conanbuild")
        self.run('CONFIG_SHELL="/bin/sh" SHELL="/bin/sh" make -j1',
                 cwd=ls_src, env="conanbuild")
        self.run('CONFIG_SHELL="/bin/sh" SHELL="/bin/sh" make install -j1',
                 cwd=ls_src, env="conanbuild")
        hits = sorted(_glob.glob(os.path.join(ls_prefix, "**", "libstrophe.a"),
                                 recursive=True))
        if not hits:
            raise RuntimeError(
                "vendored libstrophe: libstrophe.a missing after make install "
                f"(prefix {ls_prefix})")
        self.output.info("vendored libstrophe static lib: %s" % hits[0])
        # Anti-silent-degradation: the archive must reference the OpenSSL
        # backend (SSL_CTX_new undefined ref from tls_openssl.o). A dummy-
        # backend build would link but leave profanity TLS-less.
        _nm = _shutil.which("llvm-nm") or _shutil.which("nm")
        if _nm:
            _out = subprocess.run(
                [_nm, hits[0]], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True).stdout
            if "SSL_CTX_new" not in _out:
                raise RuntimeError(
                    "vendored libstrophe: no SSL_CTX_new reference in "
                    "libstrophe.a -- openssl backend missing, refusing "
                    "TLS-less build")
            self.output.info("vendored libstrophe: openssl backend confirmed")
        else:
            self.output.warning(
                "vendored libstrophe: nm not found, skipping backend check")
        self._write_libstrophe_pc(os.path.dirname(hits[0]),
                                  ls_prefix)

    def _write_libstrophe_pc(self, libdir, prefix):
        """Write libstrophe.pc next to the PkgConfigDeps files.

        Meson resolves `dependency('libstrophe')` through pkg-config; the
        vendored static lib has no conan package_info, so the .pc is
        synthesized from the real dependency graph (openssl/expat/zlib
        include/lib dirs, libs, system libs, defines). Static linking needs
        the full transitive set on the link line, hence no `Requires:` line.
        """
        includedirs, libdirs, libs, syslibs, defines = [], [], [], [], []
        for _ref, _dep in self.dependencies.items():
            cpp = _dep.cpp_info
            for _d in (cpp.includedirs or []):
                if os.path.isabs(_d) and _d not in includedirs:
                    includedirs.append(_d)
            for _d in (cpp.libdirs or []):
                if os.path.isabs(_d) and _d not in libdirs:
                    libdirs.append(_d)
            for _l in (cpp.libs or []):
                if _l not in libs:
                    libs.append(_l)
            for _l in (cpp.system_libs or []):
                if _l not in syslibs:
                    syslibs.append(_l)
            for _d in (cpp.defines or []):
                if _d not in defines:
                    defines.append(_d)
        incdir = os.path.join(prefix, "include")
        cflags = " ".join(["-I{}".format(incdir)] +
                          ["-I{}".format(_d) for _d in includedirs] +
                          ["-D{}".format(_d) for _d in defines])
        linklibs = " ".join(["-L{}".format(libdir)] +
                            ["-L{}".format(_d) for _d in libdirs if _d != libdir] +
                            ["-lstrophe"] +
                            ["-l{}".format(_l) for _l in libs] +
                            ["-l{}".format(_l) for _l in syslibs])
        pc = (
            "prefix={prefix}\n"
            "libdir={libdir}\n"
            "includedir={prefix}/include\n"
            "\n"
            "Name: libstrophe\n"
            "Description: Vendored libstrophe 0.14.0 (static, profanity build)\n"
            "Version: 0.14.0\n"
            "Libs: {linklibs}\n"
            "Cflags: {cflags}\n"
        ).format(prefix=prefix, libdir=libdir,
                 linklibs=linklibs, cflags=cflags)
        pc_path = os.path.join(self.generators_folder, "libstrophe.pc")
        with open(pc_path, "w", encoding="utf-8") as handle:
            handle.write(pc)
        self.output.info("wrote vendored libstrophe.pc: %s" % pc_path)

    def _run_upstream_tests(self):
        """Run the cmocka `unittests` binary and emit HMBS_UPSTREAM_TEST_RESULT.

        HMBS hard gate (radcli/1.2.11 R6, python3-cairo precedent) rejects
        skipped>0: status passed requires skipped==0 and
        executed==discovered. The counted harness is therefore the single
        offline `unittests` entry only (discovered=1/executed=1 on pass).
        The `functional tests` meson entry (needs stabber XMPP stub server
        + libutil, neither on OHOS) is reported via excluded_cases (not
        counted in discovered) with total_upstream_cases=2 so
        discovered(1)+excluded(1)==total, plus a gaps entry. Per-case
        `[ OK ]`/`[ FAILED ]` counts come from the single cmocka stdout
        source and decide the entry pass/fail; they are logged as evidence,
        not mixed into the entry-level marker.
        """
        unit_bin = self._find_test_binary("unittests")
        if unit_bin is None:
            raise RuntimeError("upstream test binary `unittests` not found in build tree")
        proc = subprocess.run(
            [unit_bin], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=3600)
        output = proc.stdout or ""
        case_passed = len(re.findall(r"\[\s+OK\s+\]", output))
        case_failed = len(re.findall(r"\[\s+FAILED\s+\]", output))
        case_failed += len(re.findall(r"\[\s+ERROR", output))
        case_executed = case_passed + case_failed
        if case_executed == 0:
            raise RuntimeError(
                "upstream `unittests` produced no test cases (exit=%s)" % proc.returncode)
        self.output.info("unittests exit=%s cases=%d passed=%d failed=%d"
                         % (proc.returncode, case_executed, case_passed, case_failed))
        # Counted harness is exactly the offline `unit tests` entry; the
        # `functional tests` entry (stabber+libutil) is excluded, never
        # reported as skipped (HMBS no-skipped gate). Probe the build tree
        # only to sharpen the evidence string; the count shape is fixed.
        _func_present = self._find_test_binary("functionaltests") is not None
        _func_evidence = (
            "meson.build builds functionaltests only when "
            "stabber_dep.found() and util_dep.found(); "
            + ("unexpected functionaltests binary present in build tree, "
               "still excluded: needs live XMPP server on OHOS"
               if _func_present else
               "no functionaltests binary in build tree")
        )
        gaps = [{
            "count": 1,
            "category": "environment",
            "detail": "meson test entry 'functional tests' excluded: "
                      "needs stabber XMPP stub server and libutil, "
                      "neither is available on OHOS",
            "evidence": _func_evidence,
        }]
        entry_failed = 0 if (case_failed == 0 and proc.returncode == 0) else 1
        entry_passed = 1 - entry_failed
        status = "passed" if entry_failed == 0 else "failed"
        upstream = {
            "status": status,
            "framework": "cmocka",
            "command": "./unittests (counted meson entry 'unit tests'; "
                       "cmocka cases=%d; functional tests excluded: "
                       "needs stabber+libutil)" % case_executed,
            "discovered": 1,
            "executed": 1,
            "passed": entry_passed,
            "failed": entry_failed,
            "skipped": 0,
            "reason": "N=2 audit (meson.build test() x2): offline "
                      "'unit tests' (cmocka unittests binary) executed; "
                      "'functional tests' excluded (stabber+libutil "
                      "absent); cmocka cases=%d logged as evidence" % case_executed,
            "gaps": gaps,
            "excluded_cases": ["functional tests"],
            "excluded_count": 1,
            "total_upstream_cases": 2,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if status != "passed":
            self.output.error("=== unittests tail ===\n%s" % output[-2000:])
            raise RuntimeError("upstream unit tests failed")

    def _find_test_binary(self, name):
        # NOTE: no os.access(X_OK) check: HMBS reports chmod=0 on this
        # device, so the exec bit is unreliable as a presence test. The
        # ninja-built ELF already carries its creation mode; presence +
        # non-empty size is the deterministic signal.
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                cand = os.path.join(root, name)
                try:
                    if os.path.isfile(cand) and os.path.getsize(cand) > 0:
                        return cand
                except OSError:
                    continue
        return None

    def package(self):
        # Meson installs bin/profanity plus themes/icons/man pages.
        # No shared libraries are produced (c-plugins stay disabled),
        # and Meson never emits libtool archives, so no cleanup needed.
        meson = Meson(self)
        meson.install()
        # Best-effort exec bit on the installed binary (HMBS reports
        # chmod=0, so failure is ignored; the mode from the ninja-built
        # ELF is what matters, test_package re-copies to build_folder).
        try:
            _bin = os.path.join(self.package_folder, "bin", "profanity")
            if os.path.isfile(_bin):
                os.chmod(_bin, 0o755)
        except Exception:
            pass

    def package_info(self):
        # Console application: only the bin dir matters to consumers.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
