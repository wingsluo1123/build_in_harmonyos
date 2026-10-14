#!/usr/bin/env python3
"""Conan recipe — unscd 0.54 (Makefile)"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UnscdConan(ConanFile):
    name = "unscd"
    version = "0.54"
    description = "unscd — a lightweight single-file nscd replacement (Name Service Cache Daemon)"
    license = "GPL-2.0-only"
    homepage = "https://busybox.net/~vda/unscd/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "unscd supports Linux/OHOS native builds, got %s" % self.settings.os
            )

    def source(self):
        src = self.conan_data["sources"]
        # Support both flat {url, sha256} and version-keyed {"0.54": {...}} layouts.
        if isinstance(src, dict) and self.version in src:
            src = src[self.version]
        get(self, **src, strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # OHOS libc compat: __nss_disable_nscd is a glibc-internal symbol
        # (declared + unconditionally called in nscd-0.54.c). OHOS/musl
        # libc does not provide it, so clang/lld fails with
        # "undefined symbol: __nss_disable_nscd". Declare it weak and
        # guard the call so glibc still disables nscd recursion while
        # non-glibc libc safely skips it. No platform macro: portable
        # weak-symbol idiom, idempotent across rebuilds.
        import re as _re

        src = self.source_folder
        _patched = []
        try:
            _cands = [os.path.join(src, f) for f in os.listdir(src)
                      if f.endswith(".c")]
        except OSError:
            _cands = []
        for _cfile in _cands:
            try:
                with open(_cfile, "r", encoding="utf-8", errors="replace") as _fh:
                    _txt = _fh.read()
            except OSError:
                continue
            if "__nss_disable_nscd" not in _txt:
                continue
            _orig = _txt
            if "__attribute__((weak))" not in _txt:
                _txt = _re.sub(
                    r"void\s+__nss_disable_nscd\s*\(\s*void\s*\(\s*\*\s*hell\s*\)\s*\(\s*size_t\s*,\s*struct\s+traced_file\s*\*\s*\)\s*\)\s*;",
                    "void __nss_disable_nscd(void (*hell)(size_t, struct traced_file*)) __attribute__((weak));",
                    _txt,
                )
            if "if (__nss_disable_nscd)" not in _txt:
                _txt = _txt.replace(
                    "__nss_disable_nscd(do_nothing);",
                    "if (__nss_disable_nscd)\n\t__nss_disable_nscd(do_nothing);",
                )
            if _txt != _orig:
                with open(_cfile, "w", encoding="utf-8", newline="\n") as _fh:
                    _fh.write(_txt)
                _patched.append(os.path.basename(_cfile))
        self.output.info("unscd __nss_disable_nscd weak-patch files: %s" % (_patched or "none needed"))

        # R33: prefer the compiler from Conan conf, but the conf absolute
        # path has been observed inaccessible on the true machine
        # (/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found).
        # Probe: conf value first (if executable), else PATH-resolved
        # clang/cc (hmbs prepends tool dirs to buildenv PATH). Never fail
        # blindly on a stale absolute path.
        import shutil as _shutil

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc_conf = compilers.get("c") if compilers else None
        make_conf = (os.environ.get("HMBS_MAKE") or "").strip() or None

        def _executable(cand):
            if not cand:
                return False
            try:
                if os.path.isabs(cand):
                    return os.path.isfile(cand) and os.access(cand, os.X_OK)
                return _shutil.which(cand) is not None
            except Exception:
                return False

        cc = None
        for cand in (cc_conf, _shutil.which("clang"), _shutil.which("cc"), "clang", "cc"):
            if _executable(cand):
                cc = cand
                break
        if cc is None:
            cc = cc_conf or "clang"
        make_cmd = None
        for cand in (make_conf, _shutil.which("make"), "make"):
            if _executable(cand):
                make_cmd = cand
                break
        if make_cmd is None:
            make_cmd = "make"
        self.output.info("unscd toolchain: conf_cc=%s selected_cc=%s make=%s PATH=%s"
                         % (cc_conf, cc, make_cmd, os.environ.get("PATH", "")))
        src = self.source_folder
        try:
            self.run("%s --version" % cc, cwd=src)
        except Exception as exc:
            self.output.warning("compiler --version probe failed for %s: %s" % (cc, exc))
        try:
            entries = sorted(os.listdir(src))
        except OSError:
            entries = []
        self.output.info("unscd source entries: %s" % entries)

        built = None
        makefile = None
        for cand in ("Makefile", "makefile", "GNUmakefile"):
            if os.path.isfile(os.path.join(src, cand)):
                makefile = cand
                break

        if makefile is not None:
            # Upstream Makefile uses GNU-ld-only flags in its default CFLAGS
            # (-Wl,--sort-section -Wl,alignment -Wl,--sort-common); override
            # CFLAGS on the command line (wins over file assignments) so the
            # OHOS clang/lld toolchain builds cleanly. R9: always -j1.
            self.run("%s CC=%s CFLAGS=\"-Wall -Os\" -j1" % (make_cmd, cc), cwd=src)
            for cand in ("nscd", "unscd"):
                if os.path.isfile(os.path.join(src, cand)):
                    built = os.path.join(src, cand)
                    break
        else:
            # Fallback: Debian orig layout without a top-level Makefile —
            # compile the single upstream source file directly.
            origin = None
            for cand in ("nscd.c", "unscd.c"):
                if os.path.isfile(os.path.join(src, cand)):
                    origin = cand
                    break
            if origin is None:
                for entry in entries:
                    if entry.startswith("nscd-") and entry.endswith(".c"):
                        origin = entry
                        break
            if origin is None:
                raise ConanException("unscd source not found (no Makefile, nscd.c or nscd-*.c)")
            self.run("%s -Wall -Os -o nscd %s" % (cc, origin), cwd=src)
            built = os.path.join(src, "nscd")

        if built is None or not os.path.isfile(built):
            raise ConanException("unscd binary not found after build")
        if os.path.getsize(built) == 0:
            raise ConanException("unscd binary is empty after build")
        self.output.info("unscd built: %s (%d bytes)" % (built, os.path.getsize(built)))

        # Upstream 0.54 ships no automated test suite (single-file daemon +
        # 223-byte Makefile with only all/clean targets; no tests/ dir, no
        # check/test target). Emit the no_tests evidence marker here; the
        # test_package phase re-emits it so cache-hit rounds stay covered.
        try:
            upstream = {
                "status": "no_tests",
                "framework": "make",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "unscd-0.54 audited: upstream is a single nscd-0.54.c file plus a 223-byte Makefile with only all/clean targets; no tests/ dir, no test sources, no check/test target (make -n check reports no rule)",
            }
            up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(up_msg, flush=True)
            self.output.info(up_msg)
        except Exception:
            pass

    def package(self):
        src_bin = None
        for cand in ("nscd", "unscd"):
            if os.path.isfile(os.path.join(self.source_folder, cand)):
                src_bin = os.path.join(self.source_folder, cand)
                break
        if src_bin is None:
            raise ConanException("unscd binary missing in package step")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        # Ship both names as real copies (no symlinks: HMDFS symlink support
        # is restricted). Upstream builds `nscd`; `unscd` is the package name.
        shutil.copy2(src_bin, os.path.join(bin_dir, "unscd"))
        shutil.copy2(src_bin, os.path.join(bin_dir, "nscd"))
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
