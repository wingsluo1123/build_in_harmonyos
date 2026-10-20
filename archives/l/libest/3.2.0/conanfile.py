#!/usr/bin/env python3
"""Conan recipe — libest 3.2.0 (Autotools)."""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibestConan(ConanFile):
    name = "libest"
    version = "3.2.0"
    description = "Enrollment over Secure Transport (EST, RFC 7030) library by Cisco"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cisco/libest"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openssl/3.5.6.1 为制品仓已发布 OHOS 二进制版本（与 libest 1.0.0
        # 已验证配方一致），直接命中预编译包，避免 conancenter 1.1.1w
        # 源码构建（OHOS 不支持 + 真机 perl OOM）。
        # 3.2.0 源码已含 HAVE_OLD_OPENSSL 分支（EVP_MD_CTX_new/
        # ASN1_STRING_get0_data/TLS_server_method），仅需 0004-0006
        # 移植 1.0.0 的 OpenSSL 3.x 余量修复（FIPS_mode/extern/attr释放）。
        self.requires("openssl/3.5.6.1")

    def build_requirements(self):
        # Upstream test/UT/runtest (55 CUnit suites) links -lcunit -lcurl.
        # test_requires: build-time only, never enters the consumer link
        # closure (wslay/1.1.1 + dcap/2.47.14 precedent: cunit for
        # upstream `make check`). curl/8.15.0 is the in-repo OHOS-hardened
        # recipe (manifest built); bare version resolves to the same
        # ohpcd-published package as openssl/3.5.6.1.
        # cunit MUST be 2.1.3 (dot, in-repo CMake recipe, ohpcd-only):
        # conancenter also hosts cunit/2.1-3 (dash), so test_requires on
        # 2.1-3 resolves to conancenter first on preflight hosts where both
        # remotes are enabled and its autotools build-requires chain
        # (libtool/automake/autoconf/m4) runs configure under the profile
        # CONFIG_SHELL=/data/service/hnp/bin/bash, which is inaccessible
        # on the current HMBS host (Error 127, this round). 2.1.3 exists
        # only in ohpcd (libcoap/4.3.5b precedent), its CMake build has no
        # autotools chain, and it ships the same -lcunit API.
        self.test_requires("cunit/2.1.3")
        self.test_requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # libest configure.ac: --with-ssl-dir -> SSL_CFLAGS/LDFLAGS point at
        # $ssldir/include and $ssldir/lib; point it at the conan openssl
        # package folder so headers/libs resolve inside the dependency graph.
        tc.configure_args.append(
            "--with-ssl-dir=" + self.dependencies["openssl"].package_folder)
        # R15: never pass --build/--host on the true machine. The build and
        # host are both aarch64 OHOS (native), and the patched config.guess
        # already returns *-linux-ohos. Passing explicit triplets forces a
        # cross path whose compiler probe runs before SSL/safec flags exist.
        # (bwm/0.6.3 precedent: same "C compiler cannot create executables"
        # with CC=/data/service/hnp/bin/clang fixed by stripping triplets.)
        try:
            tc.configure_args = [
                a for a in tc.configure_args
                if not str(a).startswith("--build=")
                and not str(a).startswith("--host=")
            ]
        except Exception:
            pass
        tc.generate()
        # True-machine guard: the repo profile pins
        # CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash, which is
        # inaccessible on the current HMBS host (configure re-exec dies
        # with "inaccessible or not found", Error 127). HMBS injects
        # SHELL=/bin/sh (capabilities shell=/bin/sh). Save a build-scope
        # env script so every conanbuild aggregation sees a usable shell
        # plus a writable TMPDIR instead of read-only /tmp.
        # Generated scripts win over the profile [buildenv].
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        _cc, _cxx, _lbl = self._resolve_compiler()
        if _cc:
            env.define("CC", _cc)
        if _cxx:
            env.define("CXX", _cxx)
        env.vars(self, scope="build").save_script("libest_hmos_fix")
        self.output.info(
            f"libest_hmos_fix: SHELL/CONFIG_SHELL={shell} TMPDIR={tmpdir} "
            f"compiler={_lbl} CC={_cc} CXX={_cxx}")

    def build(self):
        apply_conandata_patches(self)
        # Autoconf tmpdir hardening (E114/HMDFS setgid): the template
        # `(umask 077 && mktemp -d "./confXXXXXX")` yields an
        # owner-unwritable dir on HMDFS. Rewrite to umask 022 in every
        # configure/config.status copy (source + build trees; make may
        # re-invoke config.status). Idempotent. Deliberately NOT a
        # mktemp-exit-1 shim: under HMBS_CAP_CHMOD=0 the shim is not
        # executable and the mkdir fallback carries the same umask 077
        # (zurl/avahi evidence).
        if self.settings.os == "OHOS":
            self._patch_autoconf_umask(self.source_folder)
            try:
                self._patch_autoconf_umask(self.build_folder)
            except Exception:
                pass
        # Inline env hardening, same reasons as generate(): profile pins
        # SHELL/CONFIG_SHELL to HNP bash, unusable on some HMBS hosts,
        # and profile CC may be stale. Inline exports run after
        # conanbuild.sh is sourced, so the good values win in the same
        # shell invocation (bwm-style, juise-style).
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir),
                         ("TEMP", tmpdir)):
            os.environ[var] = val
        cc, cxx, lbl = self._resolve_compiler()
        self.output.info(
            f"libest build shell={shell} tmpdir={tmpdir} "
            f"compiler={lbl} CC={cc} CXX={cxx}")
        prefix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && '
            f'export TEMP="{tmpdir}" && '
        )
        if cc:
            prefix += f'export CC="{cc}" && '
            os.environ["CC"] = cc
        if cxx:
            prefix += f'export CXX="{cxx}" && '
            os.environ["CXX"] = cxx
        # Do NOT use Autotools.configure(): the helper runs configure via
        # env="conanbuild", which re-exports the profile's stale
        # CONFIG_SHELL AFTER our override, and it relies on the private
        # _configure_args attribute (version-fragile, previously produced
        # an arg-less configure that lost --with-ssl-dir/--host handling).
        # Run explicitly via the usable shell with inline exports AFTER
        # conanbuild.sh is sourced. Args are explicit (no helper
        # duplication, aggregate #34): prefix + ssl-dir + static flags.
        # No --build/--host (R15, native aarch64 OHOS true machine).
        configure_path = os.path.join(self.source_folder, "configure")
        cfg_dir = self.source_folder if os.path.isfile(
            configure_path) else self.build_folder
        if not os.path.isfile(configure_path):
            configure_path = os.path.join(self.build_folder, "configure")
            cfg_dir = self.build_folder
        try:
            ssl_dir = self.dependencies["openssl"].package_folder
        except Exception:
            ssl_dir = ""
        static_args = ""
        if not self.options.shared:
            static_args = " --enable-static --disable-shared"
        ssl_arg = f' --with-ssl-dir="{ssl_dir}"' if ssl_dir else ""
        # BRSKI (strategy-cycle-2 library-side fix): test/UT/st_server.c
        # (process_brski_voucher_request) calls est_find_ser_num_in_subj,
        # which lives in src/est/est_ossl_util.c inside #if ENABLE_BRSKI.
        # configure --enable-brski defines ENABLE_BRSKI for the library
        # (configure.ac AM_CONDITIONAL + AC_DEFINE). Previous rounds kept
        # the library without this flag while tests compiled with
        # -DENABLE_BRSKI, so no test-link tweak (-fcommon/safe-append/
        # FULL-set) could create the missing symbol in libest.a. Enable
        # it here so lib and tests agree (no extra dep, adds 5 suites).
        brski_arg = " --enable-brski"
        # NOTE: package_folder is the install prefix (Autotools helper
        # default). Quote paths; the true-machine path has no spaces but
        # quoting is harmless and avoids word-splitting regressions.
        conf_args = (
            f'--prefix="{self.package_folder}"'
            f"{static_args}{ssl_arg}{brski_arg}"
        )
        # Pre-configure toolchain probe: dump CC/CFLAGS/LDFLAGS, clang
        # liveness, and minimal compiles so a failure log shows whether
        # the toolchain itself is at fault. Also dump config.log on
        # configure failure (re-raise after).
        self._probe_toolchain(cfg_dir, prefix, shell)
        try:
            self.run(
                prefix + f'"{shell}" ./configure {conf_args}',
                cwd=cfg_dir, env="conanbuild")
        except Exception:
            self._dump_config_log(cfg_dir)
            raise
        # Build the bundled safe_c stub first: src/est links -lsafe_lib
        # from safe_c_stub/lib (noinst static archive, see
        # safe_c_stub/lib/Makefile.am), so it must exist before src links.
        # example/ programs are demo utilities, not part of the library
        # deliverable, and are excluded from the package.
        # Explicit make via usable shell (same stale-SHELL reason as
        # configure); -j1 honours HMBS tools.build:jobs=1.
        self.run(prefix + '"$SHELL" -c \'make -j1 -C safe_c_stub\'',
                 cwd=cfg_dir, env="conanbuild")
        self.run(prefix + '"$SHELL" -c \'make -j1 -C src\'',
                 cwd=cfg_dir, env="conanbuild")
        # Upstream tests: test/UT/runtest holds 55 CUnit suites but is
        # excluded from top-level SUBDIRS (no `make check` integration).
        # Build + run it here with the cunit+curl test requirements and
        # persist real counts to build_folder/hmbs_upstream.json (re-emitted
        # by test_package, copied to package res/ in package()). Best-effort
        # but honest: failures are reported with evidence, never skipped,
        # and never fail the library build itself (test failures must not
        # masquerade as compile failures).
        try:
            self._build_and_run_upstream_tests(cfg_dir, prefix, shell)
        except Exception as exc:
            self.output.warning(f"libest upstream tests failed: {exc}")
            try:
                self._save_upstream_result(
                    "", "test/UT/runtest (55 CUnit suites)",
                    error=f"upstream harness exception: {exc}")
            except Exception:
                pass

    def package(self):
        # Same stale-CONFIG_SHELL reason as build(): run make install
        # explicitly with inline good-shell/TMPDIR exports instead of
        # Autotools.install() which inherits the profile's bad HNP bash
        # via env="conanbuild".
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && '
            f'export TEMP="{tmpdir}" && '
        )
        cfg_dir = self.build_folder
        # configure ran in source dir (in-source); Makefile for src lives
        # under source tree. Prefer the dir that actually has a Makefile.
        try:
            if os.path.isfile(os.path.join(
                    self.source_folder, "src", "Makefile")):
                cfg_dir = self.source_folder
        except Exception:
            pass
        self.run(fix + '"$SHELL" -c \'make -C src install -j1\'',
                 cwd=cfg_dir, env="conanbuild")
        # Persist upstream evidence into the package so test_package
        # (including cache-hit rounds that skip build()) can re-emit it.
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src_json):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(
                    src_json, os.path.join(dst_dir, "hmbs_upstream.json"))
                self.output.info("libest: upstream evidence copied to res/")
        except Exception as exc:
            self.output.warning(
                f"libest: upstream evidence copy failed: {exc}")
        # 3.2.0 links -lsafe_lib from safe_c_stub/lib (noinst archive, not
        # installed by `make install`). Without it, consumers of the static
        # libest.a fail with undefined *_s symbols (strnlen_s, strcpy_s,
        # memmove_s, ...). Ship the already-built stub archive so the
        # consumer link can resolve them (see package_info below).
        self._install_safe_stub(cfg_dir)

    def package_info(self):
        # est references the bundled safe_c stub (*_s symbols). The stub is
        # shipped as libsafe_lib.a (see _install_safe_stub); list it after
        # est so static consumers link in the right order. Harmless for
        # shared (shared already embeds the objects; the extra archive is
        # then simply unused by the linker).
        self.cpp_info.libs = ["est", "safe_lib"]
        # libest installs its public header under $(includedir)/est (see
        # src/est/Makefile.am: library_includedir=$(includedir)/est).
        self.cpp_info.includedirs = ["include/est"]
        self.cpp_info.requires = ["openssl::openssl"]

    def _install_safe_stub(self, cfg_dir):
        # Locate the just-built noinst archive and ship it as
        # <package>/lib/libsafe_lib.a (link flag -lsafe_lib).
        # In-source builds place it under source_folder; out-of-source
        # under build_folder/cfg_dir; libtool may use .libs/ subdir.
        candidates = []
        for base in (cfg_dir, self.source_folder, self.build_folder):
            if not base:
                continue
            for sub in (os.path.join("safe_c_stub", "lib", "libsafe_lib.a"),
                        os.path.join("safe_c_stub", "lib", ".libs",
                                     "libsafe_lib.a")):
                p = os.path.join(base, sub)
                if p not in candidates:
                    candidates.append(p)
        src = ""
        for p in candidates:
            try:
                if p and os.path.isfile(p):
                    src = p
                    break
            except Exception:
                continue
        if not src:
            self.output.warning(
                "libest: safe stub archive not found; searched="
                + str(candidates))
            return
        try:
            dst_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, "libsafe_lib.a")
            shutil.copy2(src, dst)
            self.output.info(f"libest: installed safe stub {src} -> {dst}")
        except Exception as e:
            self.output.warning(f"libest: install safe stub failed: {e}")

    # --- Upstream test/UT/runtest (55 CUnit suites) ---

    def _build_and_run_upstream_tests(self, cfg_dir, prefix, shell):
        # Best-effort but honest: build test/UT/runtest with the cunit+curl
        # test requirements, run it from test/UT (relative CA/ paths), parse
        # the real CUnit output, persist to build_folder/hmbs_upstream.json
        # and emit HMBS_UPSTREAM_TEST_RESULT. Never raises: failures are
        # reported via the marker, not as build errors.
        log_path = os.path.join(self.build_folder, "libest_upstream.log")
        command = "test/UT/runtest (55 CUnit suites)"
        log = ""
        try:
            # Renew expired test PKI (same keys, fixtures only) before
            # building/running runtest; best-effort, never raises.
            try:
                self._renew_upstream_test_pki()
            except Exception as _e:
                self.output.warning(f"libest PKI renewal hook failed: {_e}")
            dep_dirs = self._upstream_dep_dirs()
            self.output.info(f"libest upstream dep dirs: {dep_dirs}")
            built = self._build_runtest(cfg_dir, prefix, shell, dep_dirs)
            if not built:
                ev = ""
                try:
                    evp = os.path.join(
                        self.build_folder,
                        "libest_upstream_build_evidence.txt")
                    if os.path.isfile(evp):
                        with open(evp, "r", encoding="utf-8",
                                  errors="replace") as _fh:
                            ev = _fh.read()[-3000:]
                    mkp = os.path.join(
                        self.build_folder, "libest_upstream_make.log")
                    if os.path.isfile(mkp):
                        with open(mkp, "r", encoding="utf-8",
                                  errors="replace") as _fh:
                            ev = (ev + "\nmake log tail: "
                                  + _fh.read()[-2000:])
                except Exception:
                    pass
                if not ev.strip():
                    ev = "no build evidence captured"
                self._save_upstream_result(
                    "", command,
                    error="runtest build produced no executable; "
                          "searched test/UT/runtest under source/build "
                          "trees; evidence: " + ev[-2500:])
                return
            # Strategy-cycle-3 route (crash containment): run each suite
            # in its own process via a generated single-suite driver so a
            # crashing suite can no longer hide the other suites or
            # suppress the CUnit Run Summary (observed: 1-suite run +
            # core dump with source=verbose-suites-fallback). Falls back
            # to the single runtest run when the driver cannot be built.
            # Never raises; the fallback path keeps the old behaviour.
            try:
                if self._run_suites_isolated(cfg_dir, prefix, dep_dirs,
                                             command):
                    return
            except Exception as _iso_exc:
                self.output.warning(
                    "libest isolated suite run failed "
                    f"({_iso_exc}); falling back to single runtest run")
            log = self._run_runtest(built, log_path, prefix, shell)
            self._save_upstream_result(log, command)
        except Exception as exc:
            self.output.warning(f"libest upstream run failed: {exc}")
            try:
                tail = ""
                if os.path.isfile(log_path):
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as f:
                        tail = f.read()[-2000:]
                self._save_upstream_result(
                    tail, command, error=f"harness exception: {exc}")
            except Exception:
                pass

    def _upstream_dep_dirs(self):
        # Resolve include/lib dirs of openssl + cunit + curl test deps.
        # Missing deps are reported, not silently skipped (守则: 缺依赖必须
        # 补齐再测, missing_dependency 不得包装成 environment 豁免).
        out = {}
        for name in ("openssl", "cunit", "curl"):  # curl = Conan dep lookup, not external download
            try:
                dep = self.dependencies[name]
                out[name] = str(dep.package_folder)
            except Exception:
                out[name] = ""
        return out

    def _build_runtest(self, cfg_dir, prefix, shell, dep_dirs):
        # Strategy 1: upstream hand-written test/UT/Makefile (NOT generated
        # by configure: AC_CONFIG_FILES omits test/). It hardcodes
        # CC=gcc and OPENSSL_DIR/CURL_DIR/CUNIT_DIR=/usr/local* defaults,
        # so a bare `make` fails on the true machine (clang-only, conan
        # dep dirs elsewhere). Override on the make command line (wins
        # over `CC = gcc` / `ifndef` defaults) with the resolved compiler
        # and conan package folders. ENABLE_BRSKI=1 needs no extra dep
        # and adds 5 suites; CoAP suites stay disabled (require
        # LIBCOAP_DIR; upstream optional, see gaps in _save_upstream).
        # Strategy 2 (single FULL manual link): earlier subset tiers
        # (FULL-without-CoAP, MINIMAL-without-BRSKI/CoAP) failed with 0/55
        # because upstream TUs share cross-file helpers (evidence:
        # undefined us1864_test1 referenced by us1864.o in the minimal
        # tier). Upstream SRC is inseparable: link the complete file set.
        # runtest.c guards BRSKI refs with #ifdef ENABLE_BRSKI and CoAP
        # refs with #ifdef HAVE_LIBCOAP; CoAP suites stay dormant without
        # LIBCOAP_DIR (upstream-optional) and are reported as ohos_feature
        # gaps from the CUnit log. US5248/us5248.c stays included: it
        # defines both us5248coap_add_suite (CoAP-guarded) and
        # us5248http_add_suite (always registered). Evidence (make log tail +
        # failing TU + compiler output) is persisted to
        # build_folder/libest_upstream_build_evidence.txt and surfaced in
        # the final failed marker, never an empty "log tail: ".
        # Returns the runtest executable path or "".
        src_ut = os.path.join(self.source_folder, "test", "UT")
        bld_ut_candidates = [
            os.path.join(cfg_dir, "test", "UT"),
            os.path.join(self.build_folder, "test", "UT"),
        ]
        # Locate the tree that actually holds runtest.c (in-source builds:
        # source_folder; out-of-source: build_folder copy if any).
        work_ut = ""
        for cand in [src_ut] + bld_ut_candidates:
            try:
                if cand and os.path.isfile(os.path.join(cand, "runtest.c")):
                    work_ut = cand
                    break
            except Exception:
                continue
        if not work_ut:
            self.output.warning(
                "libest upstream: runtest.c not found; searched="
                + str([src_ut] + bld_ut_candidates))
            self._append_build_evidence("runtest.c not found; searched="
                                        + str([src_ut] + bld_ut_candidates))
            return ""
        # Check for an existing binary first (idempotent rebuilds).
        for cand in [os.path.join(work_ut, "runtest"),
                     os.path.join(work_ut, "runtest.exe")]:
            try:
                if cand and os.path.isfile(cand):
                    return cand
            except Exception:
                continue
        cc, _, _ = self._resolve_compiler()
        if not cc:
            try:
                cc = self.conf.get("tools.build:compiler_executables:c",
                                   check_type=str) or "clang"
            except Exception:
                cc = "clang"
        inc_flags = []
        lib_flags = []
        for key in ("cunit", "curl", "openssl"):  # curl = Conan dep lookup, not external download
            base = dep_dirs.get(key, "")
            if base and os.path.isdir(os.path.join(base, "include")):
                inc_flags.append(f'-I"{os.path.join(base, "include")}"')
            if base and os.path.isdir(os.path.join(base, "lib")):
                lib_flags.append(f'-L"{os.path.join(base, "lib")}"')
        # libest's own headers: src/est public dir + built safe stub.
        # Plus test/util (curl_utils.h/test_utils.h/st_server.h), the UT
        # dir itself, and the source root (est_config.h lives there via
        # `cp confdefs.h est_config.h`).
        for hdr in (os.path.join(self.source_folder, "src", "est"),
                    os.path.join(self.source_folder, "src"),
                    os.path.join(self.source_folder, "safe_c_stub",
                                "include"),
                    os.path.join(self.source_folder, "test", "util"),
                    work_ut,
                    self.source_folder):
            try:
                if hdr and os.path.isdir(hdr):
                    inc_flags.append(f'-I"{hdr}"')
            except Exception:
                continue
        est_lib = ""
        for cand_base in (cfg_dir, self.source_folder, self.build_folder):
            for sub in (os.path.join("src", "est", ".libs", "libest.a"),
                        os.path.join("src", "est", "libest.a"),
                        os.path.join("src", ".libs", "libest.a")):
                try:
                    p = os.path.join(cand_base, sub) if cand_base else ""
                    if p and os.path.isfile(p):
                        est_lib = p
                        break
                except Exception:
                    continue
            if est_lib:
                break
        safe_lib = ""
        for cand_base in (cfg_dir, self.source_folder, self.build_folder):
            for sub in (os.path.join("safe_c_stub", "lib", "libsafe_lib.a"),
                        os.path.join("safe_c_stub", "lib", ".libs",
                                     "libsafe_lib.a")):
                try:
                    p = os.path.join(cand_base, sub) if cand_base else ""
                    if p and os.path.isfile(p):
                        safe_lib = p
                        break
                except Exception:
                    continue
            if safe_lib:
                break
        # OpenSSL 3.x test-harness compat (strategy-cycle-3, library-test
        # config match already done via --enable-brski): test/UT sources
        # call FIPS_mode_set()/FIPS_mode(), removed in OpenSSL 3.0.
        # us1864_test1 (US1864/us1864.c) probes FIPS_mode_set(1): with the
        # 3.5.6.1 non-FIPS provider it must report "unsupported" (return 0)
        # so the test takes its pre-existing skip branch. The shipped lib
        # already ports to EVP_default_properties_is_fips_enabled (patches
        # 0004/0005); this stub is test-runner scope only, no upstream
        # file is modified, no assertion is changed. Prebuilt once here so
        # all three link tiers (make LIBS override, 1b, manual full) can
        # append the same absolute archive.
        fips_stub_lib = ""
        try:
            _stub_c = os.path.join(self.build_folder, "libest_fips_stub.c")
            _stub_o = os.path.join(self.build_folder, "libest_fips_stub.o")
            fips_stub_lib = os.path.join(
                self.build_folder, "libest_fips_stub.a")
            if not os.path.isfile(fips_stub_lib):
                with open(_stub_c, "w", encoding="utf-8",
                          newline="\n") as _fh:
                    _fh.write(
                        "/* libest test-runner OpenSSL 3.x compat stub. */\n"
                        "int FIPS_mode_set(int onoff)"
                        "{(void)onoff;return 0;}\n"
                        "int FIPS_mode(void){return 0;}\n")
                self.run(
                    prefix + f'"{cc}" -c "{_stub_c}" -o "{_stub_o}"',
                    cwd=self.build_folder, env="conanbuild")
                self.run(
                    prefix + f'ar rcs "{fips_stub_lib}" "{_stub_o}"',
                    cwd=self.build_folder, env="conanbuild")
                self.output.info(
                    "libest upstream: built FIPS stub " + fips_stub_lib)
            else:
                self.output.info(
                    "libest upstream: reusing FIPS stub " + fips_stub_lib)
        except Exception as _stub_exc:
            self.output.warning(
                "libest upstream FIPS stub build failed: " + str(_stub_exc))
            self._append_build_evidence(
                "FIPS stub build failed: " + str(_stub_exc))
            fips_stub_lib = ""
        # Strategy 1: make when a Makefile exists in the UT dir.
        # Upstream Makefile hardcodes CC=gcc + /usr/local* defaults; pass
        # conan dep dirs + resolved compiler on the command line (wins over
        # `CC = gcc` / `ifndef` defaults). ENABLE_BRSKI=1 needs no extra
        # dep and adds 5 suites; CoAP stays off (needs LIBCOAP_DIR).
        # -fcommon (test-runner only): US3646/US4710/US4778 each define
        # tentative globals client_cert/client_priv_key; clang>=11
        # (-fno-common default) reports duplicate symbol at link time.
        # runtest is an app-type test executable, so restoring common
        # merging via CFLAGS is the sanctioned route (DRAFT-24660 (a));
        # the shipped lib itself keeps the source-level extern fix (0006).
        # Makefile appends CFLAGS+=... (BRSKI) to the command-line value,
        # so CFLAGS=-fcommon preserves -DENABLE_BRSKI via += and flows
        # into CCFLAGS -> .c.o compile lines.
        # NOTE: true-machine paths contain no spaces, so inner values are
        # passed WITHOUT embedded double quotes: quoted
        # CUNIT_DIR="/path" would bake literal quotes into the make
        # variable and break -I$(CUNIT_DIR)/include.
        mk = os.path.join(work_ut, "Makefile")
        mk_log = os.path.join(self.build_folder, "libest_upstream_make.log")
        if os.path.isfile(mk):
            try:
                openssl_dir = dep_dirs.get("openssl", "") or "/usr/local/ssl"
                curl_dir = dep_dirs.get("curl", "") or "/usr/local/curl"  # curl = Conan dep lookup, not external download
                cunit_dir = dep_dirs.get("cunit", "") or "/usr/local"
                # Stale-object guard: make rebuilds only when .c is newer
                # than .o, so objects compiled by an older round with
                # different CFLAGS would survive and re-break the link.
                # Rebuild from clean iff the recorded flags differ.
                try:
                    flag_file = os.path.join(
                        self.build_folder, "libest_upstream_cflags.txt")
                    prev = ""
                    if os.path.isfile(flag_file):
                        with open(flag_file, "r", encoding="utf-8",
                                  errors="replace") as fh_flag:
                            prev = fh_flag.read().strip()
                    if prev and prev != "-fcommon -DENABLE_BRSKI":
                        self.output.info(
                            "libest upstream: CFLAGS changed "
                            + prev + " -> -fcommon -DENABLE_BRSKI; make clean")
                        try:
                            self.run(prefix + '"$SHELL" -c "make clean"',
                                     cwd=work_ut, env="conanbuild")
                        except Exception as clean_exc:
                            self.output.warning(
                                "libest upstream make clean failed: "
                                + str(clean_exc))
                    with open(flag_file, "w", encoding="utf-8") as fh_flag:
                        fh_flag.write("-fcommon -DENABLE_BRSKI")
                except Exception as flag_exc:
                    self.output.warning(
                        "libest upstream cflags guard failed: "
                        + str(flag_exc))
                # Static-link fix for the upstream link line (Makefile:121):
                # upstream LIBS has -lest but no -lsafe_lib (its default
                # shared build embeds safe via libtool LIBADD; our
                # --disable-shared leaves *_s undefined) and no FIPS stub
                # (test-only OpenSSL 3.x removal). Override LIBS on the
                # make command line with the upstream value plus both
                # absolute archives appended AFTER -lest/-lcurl (static
                # left-to-right order). Paths have no spaces, so no inner
                # quotes. If an archive is missing, fall back to the
                # un-overridden make link and let 1b/manual tiers handle it.
                mk_libs_extra = ""
                try:
                    if safe_lib and os.path.isfile(safe_lib):
                        mk_libs_extra += " " + safe_lib
                    if fips_stub_lib and os.path.isfile(fips_stub_lib):
                        mk_libs_extra += " " + fips_stub_lib
                except Exception:
                    pass
                mk_libs_override = ""
                try:
                    if mk_libs_extra.strip():
                        mk_libs_override = (
                            " LIBS=\"-L../../src/est/.libs"
                            f" -L{openssl_dir}/lib -L{curl_dir}/lib"
                            f" -L{cunit_dir}/lib -lcunit -ldl -lpthread"
                            " -lssl -lcrypto -lest -lcurl"
                            + mk_libs_extra + "\"")
                except Exception as _lib_exc:
                    self.output.warning(
                        "libest upstream LIBS override build failed: "
                        + str(_lib_exc))
                    mk_libs_override = ""
                # GNU make ignores makefile CFLAGS+= appends when CFLAGS is
                # set on the command line, so bare CFLAGS=-fcommon silently
                # drops the Makefile's own -DENABLE_BRSKI (observed: 30 not
                # 35 suites). Spell -DENABLE_BRSKI out explicitly here.
                mk_cmd = (
                    prefix + f'"$SHELL" -c \'make -j1 '
                    f'CC={cc} '
                    f'OPENSSL_DIR={openssl_dir} '
                    f'CURL_DIR={curl_dir} '
                    f'CUNIT_DIR={cunit_dir} CFLAGS="-fcommon -DENABLE_BRSKI" '
                    f'ENABLE_BRSKI=1{mk_libs_override}\''
                )
                self.output.info(
                    f"libest upstream: make in {work_ut} CC={cc} "
                    f"OPENSSL_DIR={openssl_dir} CURL_DIR={curl_dir} "
                    f"CUNIT_DIR={cunit_dir} ENABLE_BRSKI=1 CFLAGS=-fcommon -DENABLE_BRSKI"
                    f" libs_extra={mk_libs_extra.strip()[:200]}")
                self.run(mk_cmd + f' > "{mk_log}" 2>&1', cwd=work_ut, env="conanbuild")
                try:
                    with open(mk_log, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        self.output.info("libest upstream make log tail:\n"
                                         + _fh.read()[-3000:])
                except Exception:
                    pass
            except Exception as exc:
                tail = ""
                try:
                    if os.path.isfile(mk_log):
                        with open(mk_log, "r", encoding="utf-8",
                                  errors="replace") as _fh:
                            tail = _fh.read()[-4000:]
                except Exception:
                    pass
                self.output.warning(
                    f"libest upstream make in test/UT failed: {exc}; "
                    f"make log tail: {tail}; "
                    "falling back to tiered manual link")
                self._append_build_evidence(
                    f"make failed: {exc}; make log tail: {tail}")
            for cand in (os.path.join(work_ut, "runtest"),
                         os.path.join(work_ut, "runtest.exe")):
                try:
                    if os.path.isfile(cand):
                        try:
                            with open(os.path.join(
                                    self.build_folder,
                                    "libest_upstream_tier.txt"),
                                    "w", encoding="utf-8") as _th:
                                _th.write("full-brski(make)")
                        except Exception:
                            pass
                        return cand
                except Exception:
                    continue
            # Strategy 1b: link make's in-place objects manually. The make
            # compile now succeeds (CFLAGS=-fcommon) but the upstream link
            # line (Makefile:121) lacks the bundled safe_c stub: the static
            # libest.a does not embed the *_s symbols (strcmp_s/memset_s/
            # strstr_s/strtok_s/strncpy_s/...), and consumers are expected
            # to link libsafe_lib.a (see package_info libs). Reuse the
            # exact objects make just compiled (upstream SRC, in-place .o
            # files: full suite set incl. CoAP TUs, same as upstream default
            # `make runtest`) with the safe archive appended AFTER libest
            # (static left-to-right order matters). Test-runner scope only.
            linked_1b = ""
            try:
                b1_src = [
                    "runtest.c", "US748/us748.c",
                    "US893/us893.c", "US894/us894.c", "US895/us895.c",
                    "US896/us896.c", "US897/us897.c", "US898/us898.c",
                    "US899/us899.c", "US900/us900.c", "US901/us901.c",
                    "US902/us902.c", "US903/us903.c", "US1005/us1005.c",
                    "US1159/us1159.c", "US1060/us1060.c", "US1060/us1060c.c",
                    "US1190/us1190.c", "US1864/us1864.c", "US1883/us1883.c",
                    "US1884/us1884.c", "US2174/us2174.c", "US3496/us3496.c",
                    "US3512/us3512.c", "US3612/us3612.c", "US3646/us3646.c",
                    "US4020/us4020.c", "US4710/us4710.c", "US4778/us4778.c",
                    "US4784/us4784.c", "US4752/us4752.c", "US4880/us4880.c",
                    "US5052/us5052.c", "US5121/us5121.c", "US5139/us5139.c",
                    "US5184/us5184.c", "US5213/us5213.c", "US5226/us5226.c",
                    "US5230/us5230.c", "US5237/us5237.c", "US5240/us5240.c",
                    "US5241/us5241.c", "US5244/us5244.c", "US5246/us5246.c",
                    "US5248/us5248.c", "US5255/us5255.c", "US5282/us5282.c",
                    "US5331/us5331.c", "US5357/us5357.c", "US5367/us5367.c",
                    "US5394/us5394.c", "US5399/us5399.c",
                    "US5418/us5418c.c", "US5418/us5418h.c",
                ]
                b1_util = [
                    "cdets.c", "curl_utils.c", "test_utils.c",
                    "st_server.c", "st_proxy.c", "ossl_srv.c",
                ]
                b1_objs = []
                b1_missing = []
                for b1_rel in b1_src:
                    b1_o = os.path.join(work_ut, b1_rel[:-2] + ".o")
                    if os.path.isfile(b1_o):
                        b1_objs.append(b1_o)
                    else:
                        b1_missing.append(b1_o)
                b1_utildir = os.path.join(os.path.dirname(work_ut), "util")
                for b1_rel in b1_util:
                    b1_o = os.path.join(b1_utildir, b1_rel[:-2] + ".o")
                    if os.path.isfile(b1_o):
                        b1_objs.append(b1_o)
                    else:
                        b1_missing.append(b1_o)
                if b1_missing:
                    self.output.warning(
                        "libest upstream 1b: missing make objects: "
                        + str(b1_missing))
                    self._append_build_evidence(
                        "1b missing make objects: " + str(b1_missing))
                elif not est_lib or not safe_lib:
                    self.output.warning(
                        "libest upstream 1b: archives missing est_lib="
                        + str(est_lib) + " safe_lib=" + str(safe_lib))
                    self._append_build_evidence(
                        "1b archives missing est_lib=" + str(est_lib)
                        + " safe_lib=" + str(safe_lib))
                else:
                    b1_out = os.path.join(work_ut, "runtest")
                    b1_log = os.path.join(
                        self.build_folder, "libest_upstream_1b_link.log")
                    b1_cmd = (
                        prefix + f'"{cc}" -o "{b1_out}" '
                        + " ".join('"' + b1_o + '"' for b1_o in b1_objs)
                        + f' "{est_lib}" "{safe_lib}"'
                        + (f' "{fips_stub_lib}"' if fips_stub_lib else '')
                        + ' -lcunit -lcurl '
                          "-lssl -lcrypto -ldl -lpthread -fcommon "
                        + " ".join(lib_flags))
                    try:
                        self.run(b1_cmd + ' > "' + b1_log + '" 2>&1',
                                 cwd=work_ut, env="conanbuild")
                        if os.path.isfile(b1_out):
                            self.output.info(
                                "libest upstream 1b linked " + b1_out
                                + " objs=" + str(len(b1_objs)))
                            with open(os.path.join(
                                    self.build_folder,
                                    "libest_upstream_tier.txt"),
                                    "w", encoding="utf-8") as fh_tier:
                                fh_tier.write("full-brski(make-objs)")
                            linked_1b = b1_out
                        else:
                            b1_tail = ""
                            try:
                                with open(b1_log, "r", encoding="utf-8",
                                          errors="replace") as fh_log:
                                    b1_tail = fh_log.read()[-2000:]
                            except Exception:
                                pass
                            self._append_build_evidence(
                                "1b link produced no binary; log tail: "
                                + b1_tail)
                    except Exception as b1_exc:
                        b1_tail = ""
                        try:
                            if os.path.isfile(b1_log):
                                with open(b1_log, "r", encoding="utf-8",
                                          errors="replace") as fh_log:
                                    b1_tail = fh_log.read()[-3000:]
                        except Exception:
                            pass
                        self.output.warning(
                            "libest upstream 1b link failed: " + str(b1_exc)
                            + "; log tail: " + b1_tail)
                        self._append_build_evidence(
                            "1b link failed: " + str(b1_exc)
                            + "; log tail: " + b1_tail)
            except Exception as b1_exc:
                self.output.warning(
                    "libest upstream 1b harness failed: " + str(b1_exc))
                self._append_build_evidence(
                    "1b harness failed: " + str(b1_exc))
            if linked_1b:
                return linked_1b
            try:
                if os.path.isfile(mk_log):
                    with open(mk_log, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        self._append_build_evidence(
                            "make completed but produced no binary; "
                            "make log tail: " + _fh.read()[-4000:])
                else:
                    self._append_build_evidence(
                        "make completed but produced no binary; "
                        "no make log found")
            except Exception:
                pass
        # Strategy 2: tiered manual link with upstream-faithful lists.
        # Upstream test/UT/Makefile SRC enumerates the exact objects to
        # link (runtest.c + one .c per US suite + 6 test/util helpers).
        # A bare `*.c + */*.c` glob is WRONG: test/UT/US748/perftest.c
        # is a standalone perf tool with its own main() and
        # test/util/st_*_windows.c need <windows.h>.
        # COAP tier (19 suites) needs --with-libcoap-dir/LIBCOAP_DIR
        # which this recipe does not provide: those objects are skipped
        # and reported as ohos_feature gaps. US5248/us5248.c is NOT in
        # the CoAP skip set: it defines both us5248coap_add_suite
        # (CoAP-guarded) and us5248http_add_suite (always), so it must
        # stay in every tier. Single FULL tier (base+BRSKI+CoAP+util =
        # upstream SRC exactly): upstream TUs share cross-file helpers, so
        # any subset link fails with undefined symbols (minimal-tier
        # evidence: undefined us1864_test1 referenced by us1864.o).
        _coap_rel = [
            "US5052/us5052.c", "US5139/us5139.c", "US5184/us5184.c",
            "US5213/us5213.c", "US5226/us5226.c", "US5230/us5230.c",
            "US5237/us5237.c", "US5240/us5240.c", "US5244/us5244.c",
            "US5246/us5246.c", "US5255/us5255.c", "US5282/us5282.c",
            "US5331/us5331.c", "US5357/us5357.c", "US5367/us5367.c",
            "US5394/us5394.c", "US5399/us5399.c", "US5418/us5418c.c",
        ]
        _brski_rel = [
            "US3646/us3646.c", "US4710/us4710.c", "US4778/us4778.c",
            "US4784/us4784.c", "US5418/us5418h.c",
        ]
        _base_ut_rel = [
            "runtest.c", "US748/us748.c",
            "US893/us893.c", "US894/us894.c", "US895/us895.c",
            "US896/us896.c", "US897/us897.c", "US898/us898.c",
            "US899/us899.c", "US900/us900.c", "US901/us901.c",
            "US902/us902.c", "US903/us903.c", "US1005/us1005.c",
            "US1159/us1159.c", "US1060/us1060.c", "US1060/us1060c.c",
            "US1190/us1190.c", "US1864/us1864.c", "US1883/us1883.c",
            "US1884/us1884.c", "US2174/us2174.c", "US3496/us3496.c",
            "US3512/us3512.c", "US3612/us3612.c", "US4020/us4020.c",
            "US4752/us4752.c", "US4880/us4880.c",
            "US5121/us5121.c", "US5241/us5241.c",
            "US5248/us5248.c",
        ]
        _util_rel = [
            "cdets.c", "curl_utils.c", "test_utils.c",
            "st_server.c", "st_proxy.c", "ossl_srv.c",
        ]
        util_dir = os.path.join(self.source_folder, "test", "util")
        _tiers = [
            ("full", _base_ut_rel + _brski_rel + _coap_rel,
             "-DHAVE_CUNIT -DHAVE_LIBCURL -DNO_SSL_DL -DENABLE_BRSKI"),
        ]
        last_err = ""
        for tier_name, ut_rel, extra_defs in _tiers:
            self.output.info(
                f"libest upstream: trying manual tier={tier_name} "
                f"files={len(ut_rel)}+{len(_util_rel)} defs={extra_defs}")
            uniq_sources = []
            missing = []
            for rel in ut_rel:
                p = os.path.join(work_ut, rel)
                try:
                    if p and os.path.isfile(p):
                        uniq_sources.append(p)
                    else:
                        missing.append(p)
                except Exception:
                    missing.append(p)
            for rel in _util_rel:
                p = os.path.join(util_dir, rel)
                try:
                    if p and os.path.isfile(p):
                        uniq_sources.append(p)
                    else:
                        missing.append(p)
                except Exception:
                    missing.append(p)
            if missing:
                self.output.warning(
                    f"libest upstream tier={tier_name}: missing files: "
                    + str(missing))
                self._append_build_evidence(
                    f"tier={tier_name} missing files: {missing}")
            # Defensive filter (SRC-faithful lists should not contain
            # these, but keep the guard against future upstream additions).
            filtered = []
            for s in uniq_sources:
                try:
                    base = os.path.basename(s).lower()
                except Exception:
                    continue
                if base == "perftest.c":
                    continue
                if base in ("st_server_windows.c", "st_proxy_windows.c"):
                    continue
                filtered.append(s)
            uniq_sources = filtered
            if not uniq_sources:
                last_err = f"tier={tier_name}: no test sources"
                self._append_build_evidence(last_err)
                continue
            out_bin = os.path.join(self.build_folder,
                                   f"runtest_libest_{tier_name}")
            obj_dir = os.path.join(self.build_folder,
                                   f"runtest_objs_{tier_name}")
            try:
                os.makedirs(obj_dir, exist_ok=True)
            except Exception:
                pass
            objs = []
            # -fcommon (test-runner only, same DRAFT-24660 rationale as the
            # Strategy-1 CFLAGS override above): BRSKI TUs carry tentative
            # definitions (client_cert/client_priv_key) that clang>=11
            # rejects as duplicate symbol under -fno-common. Scoped to the
            # runtest objects + link only; the shipped lib keeps the
            # source-level extern fix (patch 0006).
            extra_cflags = " ".join(inc_flags) + " " + extra_defs + " -fcommon"
            tier_failed = ""
            for src in uniq_sources:
                base = os.path.basename(src).replace(".c", ".o")
                obj = os.path.join(obj_dir, base)
                idx = 0
                stem = base
                while obj in objs:
                    idx += 1
                    obj = os.path.join(obj_dir, f"{idx}_{stem}")
                objs.append(obj)
                compile_cmd = (
                    prefix + f'"{cc}" -c "{src}" -o "{obj}" {extra_cflags} -fPIC')
                try:
                    self.run(compile_cmd, cwd=self.build_folder, env="conanbuild")
                except Exception as exc:
                    tier_failed = (
                        f"tier={tier_name} compile failed for "
                        f"{os.path.basename(src)}: {exc}")
                    self.output.warning(tier_failed)
                    self._append_build_evidence(tier_failed)
                    break
            if tier_failed:
                last_err = tier_failed
                continue
            link_libs = " ".join(lib_flags)
            est_part = f'"{est_lib}"' if est_lib else "-lest"
            safe_part = f'"{safe_lib}"' if safe_lib else "-lsafe_lib"
            # Upstream LDFLAGS: -lcunit -ldl -lpthread -lssl -lcrypto
            # -lest -lcurl. -ldl/-lpthread are required on OHOS/Linux.
            self.output.info(
                f"libest upstream tier={tier_name}: est_lib={est_lib} "
                f"safe_lib={safe_lib} objs={len(objs)}")
            if not est_lib or not safe_lib:
                self._append_build_evidence(
                    f"tier={tier_name}: archive missing est_lib={est_lib} "
                    f"safe_lib={safe_lib}")
            link_log = os.path.join(
                self.build_folder, f"runtest_link_{tier_name}.log")
            link_cmd = (
                prefix + f'"{cc}" -o "{out_bin}" '
                + " ".join(f'"{o}"' for o in objs)
                + f" {est_part} {safe_part}"
                + (f' "{fips_stub_lib}"' if fips_stub_lib else '')
                + " -lcunit -lcurl -lssl -lcrypto "
                  "-ldl -lpthread -fcommon "
                + link_libs)
            try:
                self.run(link_cmd + f' > "{link_log}" 2>&1',
                         cwd=self.build_folder, env="conanbuild")
            except Exception as exc:
                link_tail = ""
                try:
                    if os.path.isfile(link_log):
                        with open(link_log, "r", encoding="utf-8",
                                  errors="replace") as fh_link:
                            link_tail = fh_link.read()[-3000:]
                except Exception:
                    pass
                last_err = f"tier={tier_name} link failed: {exc}"
                self.output.warning(last_err + "; log tail: " + link_tail)
                self._append_build_evidence(last_err + "; log tail: "
                                            + link_tail)
                continue
            try:
                if os.path.isfile(out_bin):
                    self.output.info(
                        f"libest upstream: tier={tier_name} built {out_bin}")
                    try:
                        with open(os.path.join(
                                self.build_folder,
                                "libest_upstream_tier.txt"),
                                "w", encoding="utf-8") as _th:
                            _th.write(tier_name)
                    except Exception:
                        pass
                    return out_bin
            except Exception:
                pass
            last_err = f"tier={tier_name}: link produced no binary"
            self._append_build_evidence(last_err)
        self._append_build_evidence("all manual tiers failed; last: " + last_err)
        return ""

    def _append_build_evidence(self, text):
        # Persist per-file build evidence so the final failed marker
        # carries the real failing TU + log tail instead of an empty
        # "log tail: ". Best-effort, never raises.
        try:
            p = os.path.join(self.build_folder,
                             "libest_upstream_build_evidence.txt")
            with open(p, "a", encoding="utf-8") as h:
                h.write(text + "\n")
        except Exception:
            pass

    def _renew_upstream_test_pki(self):
        # Best-effort renewal of the expired upstream test PKI (test/UT
        # fixtures only; library sources and test assertions untouched).
        # Root cause (preflight rounds 9-10: 0/55 passed): the whole EST
        # test PKI expired 2026-06-14/15 (estCA cacert NotAfter=260614,
        # server cert + per-suite leaves are the same 12-year batch) while
        # preflights run 2026-10; curl helpers enforce SSL_VERIFYPEER=1,
        # so every TLS-verify assert fails. MFG/SUDI PKI (valid 2030/2040)
        # and negative fixtures (revoked/selfsigned/intentionally-expired)
        # are never touched. Same-key renewal: CA certs self-renewed with
        # their committed keys; leaves reissued via `openssl x509 -req -CA`
        # with original subjects; trust bundles refreshed by same-pubkey
        # block swap (order/composition preserving). Idempotent and
        # self-healing (renews when expiring within 90 days). Never raises:
        # any failure only warns and tests proceed as before.
        import datetime as _dt
        import shutil as _sh
        import subprocess as _sp
        try:
            ut_dir = os.path.join(self.source_folder, "test", "UT")
            ca_dir = os.path.join(ut_dir, "CA")
            if not os.path.isdir(ca_dir):
                return
            ossl = _sh.which("openssl") or ""
            if not ossl or not os.path.isfile(ossl):
                try:
                    _pf = str(self.dependencies["openssl"].package_folder)
                    for _c in (os.path.join(_pf, "bin", "openssl"),
                               os.path.join(_pf, "bin", "openssl.exe")):
                        if os.path.isfile(_c):
                            ossl = _c
                            break
                except Exception:
                    pass
            if not ossl or not os.path.isfile(ossl):
                self.output.warning(
                    "libest PKI renewal skipped: no openssl binary")
                return

            def _run(args):
                return _sp.run(
                    args, cwd=ca_dir, stdout=_sp.PIPE, stderr=_sp.PIPE,
                    text=True, timeout=180)

            def _enddate(pem):
                try:
                    r = _run([ossl, "x509", "-noout", "-enddate",
                              "-in", pem])
                    if r.returncode != 0:
                        return None
                    s = r.stdout.strip().split("=", 1)[1]
                    # Locale-independent parse (true-machine LC_TIME may
                    # not be English; strptime %b would then fail).
                    _m = re.match(
                        r"(\w{3})\s+(\d+)\s+(\d+):(\d+):(\d+)\s+(\d+)",
                        s.strip())
                    if _m:
                        _mon = {"jan": 1, "feb": 2, "mar": 3, "apr": 4,
                                "may": 5, "jun": 6, "jul": 7, "aug": 8,
                                "sep": 9, "oct": 10, "nov": 11,
                                "dec": 12}.get(_m.group(1).lower(), 0)
                        if _mon:
                            return _dt.datetime(
                                int(_m.group(6)), _mon, int(_m.group(2)),
                                int(_m.group(3)), int(_m.group(4)),
                                int(_m.group(5)))
                    return _dt.datetime.strptime(
                        s, "%b %d %H:%M:%S %Y %Z")
                except Exception:
                    return None

            def _pubkey(pem):
                try:
                    r = _run([ossl, "x509", "-noout", "-pubkey",
                              "-in", pem])
                    if r.returncode != 0:
                        return ""
                    return " ".join(r.stdout.split())
                except Exception:
                    return ""

            def _keypub(pem):
                # SubjectPublicKeyInfo of a PRIVATE key file (_pubkey above
                # only handles certs). Used for the same-key guard.
                try:
                    r = _run([ossl, "pkey", "-in", pem, "-pubout"])
                    if r.returncode != 0:
                        r = _run([ossl, "rsa", "-in", pem, "-pubout"])
                    if r.returncode != 0:
                        return ""
                    return " ".join(r.stdout.split())
                except Exception:
                    return ""

            def _subject(pem):
                try:
                    r = _run([ossl, "x509", "-noout", "-subject",
                              "-nameopt", "oneline", "-in", pem])
                    if r.returncode != 0:
                        return ""
                    s = r.stdout.strip()
                    if s.lower().startswith("subject="):
                        s = s[len("subject="):].strip()
                    return s
                except Exception:
                    return ""

            def _req_subj(s):
                # `openssl req -subj` demands slash format (/CN=x/OU=y)
                # while `x509 -subject -nameopt oneline` prints
                # 'CN = x, OU = y'. The true machine rejected the oneline
                # form verbatim ("subject name is expected to be in the
                # format /type0=value0/...; 'CN = estExampleCA'").
                # Convert deterministically; "" means unparseable and the
                # caller must skip instead of issuing a mis-subject cert.
                try:
                    s = (s or "").strip()
                    if not s:
                        return ""
                    if s.startswith("/"):
                        return s
                    parts = []
                    for comp in s.split(","):
                        comp = comp.strip()
                        if not comp or "=" not in comp:
                            continue
                        k, v = comp.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if not k or not v:
                            continue
                        v = v.replace("/", "\\/")
                        parts.append("/" + k + "=" + v)
                    return "".join(parts)
                except Exception:
                    return ""

            def _issuer(pem):
                try:
                    r = _run([ossl, "x509", "-noout", "-issuer",
                              "-nameopt", "oneline", "-in", pem])
                    if r.returncode != 0:
                        return ""
                    return r.stdout.strip()
                except Exception:
                    return ""

            def _read(p):
                with open(p, "r", encoding="utf-8",
                          errors="replace") as _f:
                    return _f.read()

            def _write(p, data):
                with open(p, "w", encoding="utf-8", newline="\n") as _f:
                    _f.write(data)

            now = _dt.datetime.utcnow()
            horizon = now + _dt.timedelta(days=90)
            renewed = {}
            touched = []

            # 1) Self-renew the two EST CA certs with their committed keys.
            # Extension-preserving renewal (cycle-3 fix): upstream
            # createCA.sh mints the CA with `-extensions v3_ca -config
            # $EST_OPENSSL_CACNF`; the previous bare `req -new -x509`
            # emitted a v1 cert without basicConstraints CA:TRUE, which
            # breaks chain validation and aborts server-init paths
            # (observed next round as a 1-suite run ending in a core
            # dump). Discover the committed upstream openssl config
            # (the one carrying a [v3_ca] section) and reuse it; when no
            # such config exists, skip CA renewal instead of emitting a
            # v1 cert (fail safe, fixtures untouched).
            _cnf = ""
            try:
                _cands = []
                for _cr, _cds, _cfs in os.walk(ca_dir):
                    for _cf in sorted(_cfs):
                        if _cf.lower().endswith((".cnf", ".conf")):
                            _cands.append(os.path.join(_cr, _cf))
                    if _cands:
                        break
                for _cc in _cands:
                    try:
                        if "v3_ca" in _read(_cc):
                            _cnf = _cc
                            break
                    except Exception:
                        continue
                if not _cnf and _cands:
                    _cnf = _cands[0]
            except Exception:
                _cnf = ""
            if _cnf:
                self.output.info(f"libest PKI: CA renewal config {_cnf}")
            for _ca, _key in (
                    ("estCA/cacert.crt", "estCA/private/cakey.pem"),
                    ("extCA/cacert.crt", "extCA/private/cakey.pem")):
                try:
                    _cp = os.path.join(ca_dir, _ca)
                    _kp = os.path.join(ca_dir, _key)
                    if not (os.path.isfile(_cp) and os.path.isfile(_kp)):
                        continue
                    _ed = _enddate(_cp)
                    if _ed is not None and _ed > horizon:
                        continue
                    _subj = _req_subj(_subject(_cp))
                    if not _subj:
                        self.output.warning(
                            f"libest PKI: CA {_ca} subject unparseable; "
                            "skipping (refusing mis-subject reissue)")
                        continue
                    if not _cnf:
                        self.output.warning(
                            "libest PKI: no openssl config with v3_ca; "
                            f"skipping CA {_ca} (refusing v1 reissue)")
                        continue
                    _old_pub = _pubkey(_cp)
                    _new = _cp + ".renewed"
                    r = _run([ossl, "req", "-new", "-x509", "-key", _kp,
                              "-subj", _subj, "-days", "3650", "-sha256",
                              "-config", _cnf, "-extensions", "v3_ca",
                              "-out", _new])
                    if r.returncode != 0 or not os.path.isfile(_new):
                        self.output.warning(
                            f"libest PKI: CA renew failed {_ca}: "
                            f"{r.stderr[-300:]}")
                        continue
                    _write(_cp, _read(_new))
                    try:
                        os.remove(_new)
                    except Exception:
                        pass
                    if _old_pub:
                        renewed[_old_pub] = _read(_cp)
                    touched.append(_ca)
                except Exception as _e:
                    self.output.warning(
                        f"libest PKI: CA {_ca} error {_e}")

            # 2) Reissue the EST server cert from its committed key (+IP SAN;
            # original has CN-only, curl 8 needs SAN or CN fallback).
            try:
                _srv_crt = os.path.join(
                    ca_dir, "estCA/private/estservercertandkey.pem")
                _srv_only = os.path.join(ca_dir, "estCA/estserver.crt")
                _ca_crt = os.path.join(ca_dir, "estCA/cacert.crt")
                _ca_key = os.path.join(ca_dir, "estCA/private/cakey.pem")
                if (os.path.isfile(_srv_crt) and os.path.isfile(_ca_crt)
                        and os.path.isfile(_ca_key)):
                    _ed = _enddate(_srv_crt)
                    if _ed is None or _ed <= horizon:
                        _blob = _read(_srv_crt)
                        _ks = _blob.find("-----BEGIN PRIVATE KEY-----")
                        _ke = _blob.find("-----END PRIVATE KEY-----")
                        if _ks < 0:
                            _ks = _blob.find("-----BEGIN RSA PRIVATE KEY-----")
                            _ke = _blob.find("-----END RSA PRIVATE KEY-----")
                        if _ks >= 0 and _ke > _ks:
                            _ke = _blob.find("\n", _ke) + 1 or len(_blob)
                            _key_tmp = os.path.join(
                                self.build_folder, "libest_pki_srvkey.pem")
                            _csr = os.path.join(
                                self.build_folder, "libest_pki_srv.csr")
                            _san = os.path.join(
                                self.build_folder, "libest_pki_san.cnf")
                            _write(_key_tmp, _blob[_ks:_ke])
                            _write(_san, "subjectAltName=IP:127.0.0.1\n")
                            r1 = _run([ossl, "req", "-new", "-key", _key_tmp,
                                       "-subj", "/CN=127.0.0.1",
                                       "-out", _csr])
                            if r1.returncode == 0:
                                _new = _srv_crt + ".renewed"
                                r2 = _run([ossl, "x509", "-req", "-in", _csr,
                                           "-CA", _ca_crt, "-CAkey", _ca_key,
                                           "-CAcreateserial", "-days", "1825",
                                           "-sha256", "-extfile", _san,
                                           "-out", _new])
                                if r2.returncode == 0 and os.path.isfile(_new):
                                    _nb = _read(_new)
                                    _spub = _pubkey(_new)
                                    _ob = _read(_srv_crt)
                                    _opub = _pubkey(_srv_crt)
                                    _write(_srv_crt, _nb + _blob[_ks:_ke])
                                    if os.path.isfile(_srv_only):
                                        _write(_srv_only, _nb)
                                    if _opub:
                                        renewed[_opub] = _nb
                                    if _spub:
                                        renewed[_spub] = _nb
                                    touched.append(
                                        "estCA/private/estservercertandkey.pem")
                                    try:
                                        os.remove(_new)
                                    except Exception:
                                        pass
                            for _t in (_key_tmp, _csr, _san):
                                try:
                                    os.remove(_t)
                                except Exception:
                                    pass
            except Exception as _e:
                self.output.warning(f"libest PKI: server cert error {_e}")

            # 3) Reissue expired EST-batch leaf certs (same key+subject).
            # Denylist: negative fixtures + bundles + non-cert material.
            _deny = ("revok", "selfsign", "expired", "bad", "invalid",
                     "untrust", "wrong", "bogus", "corrupt", "mimic")
            _bundles = {"trustedcerts.crt", "multicacerts.crt",
                        "cacertandcrl.crt", "sudi_chain.crt",
                        "brski_trustedcerts.crt"}
            _skip_dirs = ("masa", "mfg", "sudi", "coap_emu")
            _ca_pair = {
                "estexampleca": ("estCA/cacert.crt",
                                 "estCA/private/cakey.pem"),
                "estexternalca": ("extCA/cacert.crt",
                                  "extCA/private/cakey.pem"),
            }
            try:
                _scan_n = 0
                for _root, _ds, _fs in os.walk(ut_dir):
                    _rel = os.path.relpath(_root, ut_dir).lower()
                    if _rel.split(os.sep)[0] in _skip_dirs or any(
                            _k in _rel for _k in _skip_dirs):
                        continue
                    for _fn in sorted(_fs):
                        _scan_n += 1
                        if _scan_n % 50 == 0:
                            self.output.info(
                                "libest PKI: leaf scan progress "
                                f"{_scan_n} files touched={len(touched)}")
                        try:
                            _lp = os.path.join(_root, _fn)
                            _ln = _fn.lower()
                            if _ln in _bundles:
                                continue
                            if _ln.endswith((".key", ".cnf", ".req", ".srl",
                                             ".db", ".old", ".attr", ".txt",
                                             ".sh", ".bat", ".log",
                                             ".renewed")):
                                continue
                            if any(_k in _ln for _k in _deny):
                                continue
                            try:
                                _blob = _read(_lp)
                            except Exception:
                                continue
                            if "-----BEGIN CERTIFICATE-----" not in _blob:
                                continue
                            if "PRIVATE KEY" in _blob:
                                continue
                            _ed = _enddate(_lp)
                            if _ed is not None and _ed > horizon:
                                continue
                            _iss = _issuer(_lp).lower()
                            _pair = None
                            for _k, _v in _ca_pair.items():
                                if _k in _iss:
                                    _pair = _v
                                    break
                            if _pair is None:
                                continue
                            _subj = _req_subj(_subject(_lp))
                            if not _subj:
                                continue
                            _cac, _cak = (os.path.join(ca_dir, _pair[0]),
                                          os.path.join(ca_dir, _pair[1]))
                            if not (os.path.isfile(_cac)
                                    and os.path.isfile(_cak)):
                                continue
                            # sibling private keys in the same dir
                            _keys = []
                            for _kf in sorted(os.listdir(_root)):
                                if "key" in _kf.lower() or "priv" in _kf.lower():
                                    _kp2 = os.path.join(_root, _kf)
                                    try:
                                        if ("PRIVATE KEY" in _read(_kp2)
                                                and os.path.isfile(_kp2)):
                                            _keys.append(_kp2)
                                    except Exception:
                                        continue
                            if not _keys:
                                continue
                            _old_pub = _pubkey(_lp)
                            # Same-key guard (cycle-3 fix): only reissue
                            # with the sibling key whose pubkey matches the
                            # original leaf. `openssl x509 -req -CA` does not
                            # check key ownership, so a non-matching sibling
                            # key would still verify against the CA yet break
                            # the key/cert pair at TLS handshake time,
                            # trading one failure mode for another. No
                            # matching key -> leave the fixture untouched.
                            _matched = []
                            for _kk in _keys:
                                try:
                                    if _old_pub and _keypub(_kk) == _old_pub:
                                        _matched.append(_kk)
                                except Exception:
                                    continue
                            if not _matched:
                                continue
                            _done = False
                            for _kk in _matched:
                                _csr = os.path.join(
                                    self.build_folder, "libest_pki_leaf.csr")
                                _new = _lp + ".renewed"
                                r1 = _run([ossl, "req", "-new", "-key", _kk,
                                           "-subj", _subj, "-out", _csr])
                                if r1.returncode != 0:
                                    continue
                                r2 = _run([ossl, "x509", "-req", "-in", _csr,
                                           "-CA", _cac, "-CAkey", _cak,
                                           "-CAcreateserial", "-days", "1825",
                                           "-sha256", "-out", _new])
                                if r2.returncode != 0 or not os.path.isfile(
                                        _new):
                                    continue
                                r3 = _run([ossl, "verify", "-CAfile", _cac,
                                           _new])
                                if r3.returncode != 0:
                                    try:
                                        os.remove(_new)
                                    except Exception:
                                        pass
                                    continue
                                _nb = _read(_new)
                                _write(_lp, _nb)
                                if _old_pub:
                                    renewed[_old_pub] = _nb
                                touched.append(
                                    os.path.relpath(_lp, ut_dir))
                                try:
                                    os.remove(_new)
                                except Exception:
                                    pass
                                try:
                                    os.remove(_csr)
                                except Exception:
                                    pass
                                _done = True
                                break
                            if _done:
                                continue
                        except Exception as _e:
                            self.output.warning(
                                f"libest PKI: leaf {_fn} error {_e}")
                            continue
            except Exception as _e:
                self.output.warning(f"libest PKI: leaf walk error {_e}")

            # 4) Refresh trust bundles by same-pubkey block swap.
            if renewed:
                for _b in ("CA/trustedcerts.crt",
                           "CA/estCA/multicacerts.crt",
                           "CA/estCA/cacertandcrl.crt"):
                    try:
                        _bp = os.path.join(ut_dir, _b)
                        if not os.path.isfile(_bp):
                            continue
                        _txt = _read(_bp)
                        _parts = _txt.split("-----BEGIN CERTIFICATE-----")
                        _head = _parts[0]
                        _out = [_head]
                        _swapped = 0
                        for _pc in _parts[1:]:
                            _blk = ("-----BEGIN CERTIFICATE-----" + _pc)
                            # Preserve any trailing non-cert material
                            # (e.g. the CRL block in cacertandcrl.crt).
                            _endm = "-----END CERTIFICATE-----"
                            _ei = _blk.find(_endm)
                            if _ei >= 0:
                                _certpart = _blk[:_ei + len(_endm)]
                                _tail = _blk[_ei + len(_endm):]
                            else:
                                _certpart, _tail = _blk, ""
                            _tmp = os.path.join(
                                self.build_folder, "libest_pki_blk.pem")
                            _write(_tmp, _certpart)
                            _pk = _pubkey(_tmp)
                            try:
                                os.remove(_tmp)
                            except Exception:
                                pass
                            if _pk and _pk in renewed:
                                _out.append(renewed[_pk] + _tail)
                                _swapped += 1
                            else:
                                _out.append(_blk)
                        if _swapped:
                            _write(_bp, "".join(_out))
                            touched.append(f"{_b} ({_swapped} blocks)")
                    except Exception as _e:
                        self.output.warning(
                            f"libest PKI: bundle {_b} error {_e}")
            self.output.info(
                f"libest PKI renewal: touched={len(touched)} {touched[:12]}")
        except Exception as _e:
            try:
                self.output.warning(f"libest PKI renewal aborted: {_e}")
            except Exception:
                pass

    def _run_runtest(self, runtest_bin, log_path, prefix, shell):
        # Run from test/UT so relative CA/ cert paths resolve (runtest
        # chdirs internally in some versions; cwd here is the safe default).
        run_dir = os.path.dirname(runtest_bin)
        try:
            src_ut = os.path.join(self.source_folder, "test", "UT")
            if os.path.isfile(os.path.join(src_ut, "runtest.c")):
                run_dir = src_ut
        except Exception:
            pass
        # Hang guard (same SSH-drop rationale as the isolated loop):
        # bound the single fallback run with `timeout -k` when present.
        try:
            _to1 = shutil.which("timeout") or ""
        except Exception:
            _to1 = ""
        _tpre1 = (f'"{_to1}" -k 10 600 ' if _to1 else "")
        cmd = prefix + _tpre1 + f'"{runtest_bin}" > "{log_path}" 2>&1'
        try:
            self.run(cmd, cwd=run_dir, env="conanrun")
        except Exception as exc:
            self.output.warning(f"libest runtest exited non-zero: {exc}")
        log = ""
        try:
            if os.path.isfile(log_path):
                with open(log_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    log = f.read()
                self.output.info(
                    "libest upstream runtest output tail:\n" + log[-6000:])
            else:
                self.output.warning(
                    f"libest upstream log missing: {log_path}")
        except Exception as exc:
            self.output.warning(f"libest upstream log read failed: {exc}")
        if not log.strip():
            raise Exception(
                f"runtest produced empty output; log={log_path}")
        # Falsifiability: an empty fixture (toybox tar-B lesson) can print
        # PASS while asserting nothing. Require the log to be non-trivial.
        if len(log.strip()) < 200:
            raise Exception(
                "runtest output suspiciously short "
                f"({len(log.strip())} chars); refusing to count; "
                f"log={log_path}")
        return log

    def _crash_hint(self, log):
        # Single-purpose crash-signal scan (evidence only, never counts):
        # returns the first process-death keyword line found in the log
        # (core dump / signal / abort / segfault / assertion trap) or "".
        # Counting always comes from _parse_cunit_log or the isolated
        # per-suite logs, never from this scan.
        try:
            for line in log.splitlines():
                low = line.lower()
                for kw in ("core dumped", "core dump", "signal ",
                           "segmentation fault", "segfault", "sigsegv",
                           "sigabort", "sigbus", "sigill", "sigfpe",
                           "aborted", "assertion", "trace/breakpoint"):
                    if kw in low:
                        return line.strip()[:200]
        except Exception:
            pass
        return ""

    def _suite_table(self):
        # (UT relpath, suite name, add_func) for the 35 suites registered
        # by this non-CoAP + BRSKI build. Mirrors upstream test/UT/Makefile
        # SRC minus the 18 CoAP-only TUs (their runtest.c registration is
        # #ifdef HAVE_LIBCOAP) and minus runtest.c itself; us5248.c maps to
        # us5248http_add_suite (its coap half is guarded). Registration
        # order follows runtest.c (deterministic evidence).
        return [
            ("US748/us748.c", "us748", "us748_add_suite"),
            ("US893/us893.c", "us893", "us893_add_suite"),
            ("US894/us894.c", "us894", "us894_add_suite"),
            ("US895/us895.c", "us895", "us895_add_suite"),
            ("US896/us896.c", "us896", "us896_add_suite"),
            ("US897/us897.c", "us897", "us897_add_suite"),
            ("US898/us898.c", "us898", "us898_add_suite"),
            ("US899/us899.c", "us899", "us899_add_suite"),
            ("US900/us900.c", "us900", "us900_add_suite"),
            ("US901/us901.c", "us901", "us901_add_suite"),
            ("US902/us902.c", "us902", "us902_add_suite"),
            ("US903/us903.c", "us903", "us903_add_suite"),
            ("US1005/us1005.c", "us1005", "us1005_add_suite"),
            ("US1159/us1159.c", "us1159", "us1159_add_suite"),
            ("US1060/us1060.c", "us1060", "us1060_add_suite"),
            ("US1060/us1060c.c", "us1060c", "us1060c_add_suite"),
            ("US1190/us1190.c", "us1190", "us1190_add_suite"),
            ("US1864/us1864.c", "us1864", "us1864_add_suite"),
            ("US1883/us1883.c", "us1883", "us1883_add_suite"),
            ("US1884/us1884.c", "us1884", "us1884_add_suite"),
            ("US2174/us2174.c", "us2174", "us2174_add_suite"),
            ("US3496/us3496.c", "us3496", "us3496_add_suite"),
            ("US3512/us3512.c", "us3512", "us3512_add_suite"),
            ("US3612/us3612.c", "us3612", "us3612_add_suite"),
            ("US3646/us3646.c", "us3646", "us3646_add_suite"),
            ("US4020/us4020.c", "us4020", "us4020_add_suite"),
            ("US4710/us4710.c", "us4710", "us4710_add_suite"),
            ("US4778/us4778.c", "us4778", "us4778_add_suite"),
            ("US4784/us4784.c", "us4784", "us4784_add_suite"),
            ("US4752/us4752.c", "us4752", "us4752_add_suite"),
            ("US4880/us4880.c", "us4880", "us4880_add_suite"),
            ("US5121/us5121.c", "us5121", "us5121_add_suite"),
            ("US5241/us5241.c", "us5241", "us5241_add_suite"),
            ("US5248/us5248.c", "us5248http", "us5248http_add_suite"),
            ("US5418/us5418h.c", "us5418h", "us5418h_add_suite"),
        ]

    def _write_suite_driver(self, path, table):
        # Generates run_one_suite.c: registers exactly one suite (argv[1])
        # and runs it in this process. Mirrors runtest.c main() (SIGPIPE
        # ignore, est_apps_startup/shutdown, CUnit Basic verbose) minus the
        # 55-suite fan-out, so a crashing suite kills only its own child
        # process. Harness-only isolation: no test assertion is touched.
        parts = []
        parts.append("/* libest HMBS per-suite isolation driver. */")
        parts.append("#include <stdio.h>")
        parts.append("#include <string.h>")
        parts.append("#ifndef WIN32")
        parts.append("#include <signal.h>")
        parts.append("#endif")
        parts.append('#include "est.h"')
        parts.append('#include "CUnit/Basic.h"')
        for _rel, _suite, _func in table:
            parts.append("extern int " + _func + "(void);")
        parts.append("static struct { const char *name; int (*add)(void); } kSuites[] = {")
        for _rel, _suite, _func in table:
            parts.append('  {"' + _suite + '", ' + _func + "},")
        parts.append("  {0, 0}")
        parts.append("};")
        parts.append("int main(int argc, char *argv[]) {")
        parts.append("#ifndef WIN32")
        parts.append("  struct sigaction sig_act;")
        parts.append("  memset(&sig_act, 0, sizeof(struct sigaction));")
        parts.append("  sig_act.sa_handler = SIG_IGN;")
        parts.append("  sigemptyset(&sig_act.sa_mask);")
        parts.append("  sigaction(SIGPIPE, &sig_act, NULL);")
        parts.append("#endif")
        parts.append("  if (argc != 2) {")
        parts.append('    fprintf(stderr, "usage: run_one_suite <suite>\\n");')
        parts.append("    return 2;")
        parts.append("  }")
        parts.append("  {")
        parts.append("    int i;")
        parts.append("    int (*add)(void) = 0;")
        parts.append("    for (i = 0; kSuites[i].name; i++) {")
        parts.append("      if (!strcmp(kSuites[i].name, argv[1])) { add = kSuites[i].add; break; }")
        parts.append("    }")
        parts.append("    if (!add) {")
        parts.append('      fprintf(stderr, "unknown suite: %s\\n", argv[1]);')
        parts.append("      return 2;")
        parts.append("    }")
        parts.append("    est_apps_startup();")
        parts.append("    if (CUE_SUCCESS != CU_initialize_registry()) {")
        parts.append('      fprintf(stderr, "CU_initialize_registry failed\\n");')
        parts.append("      return 3;")
        parts.append("    }")
        parts.append("    {")
        parts.append("      int rv = add();")
        parts.append("      if (rv != CUE_SUCCESS) {")
        parts.append('        printf("add_suite %s failed (%d)\\n", argv[1], rv);')
        parts.append("        return 3;")
        parts.append("      }")
        parts.append("    }")
        parts.append("    CU_basic_set_mode(CU_BRM_VERBOSE);")
        parts.append("    CU_basic_run_tests();")
        parts.append('    printf("\\nHMBS_SUITE_RESULT name=%s tests_run=%u tests_failed=%u\\n",')
        parts.append("           argv[1], CU_get_number_of_tests_run(), CU_get_number_of_tests_failed());")
        parts.append("    CU_cleanup_registry();")
        parts.append("    est_apps_shutdown();")
        parts.append("    return 0;")
        parts.append("  }")
        parts.append("}")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(parts) + "\n")

    def _isolated_build_inputs(self, cfg_dir, dep_dirs):
        # Discovers (work_ut, run_dir, objs, est_lib, safe_lib, inc_flags,
        # lib_flags) for the isolated driver link. Reuses the make-built
        # in-place objects (upstream SRC full set, same objects the
        # full-brski(make) tier just linked) plus the already-built
        # archives. Returns None when anything is missing (caller falls
        # back to the single runtest run). Never raises.
        try:
            table = self._suite_table()
            src_ut = os.path.join(self.source_folder, "test", "UT")
            work_ut = ""
            for cand in (src_ut,
                         os.path.join(cfg_dir, "test", "UT"),
                         os.path.join(self.build_folder, "test", "UT")):
                try:
                    if cand and os.path.isfile(os.path.join(cand, "runtest.c")):
                        work_ut = cand
                        break
                except Exception:
                    continue
            if not work_ut:
                return None
            objs = []
            for rel, _suite, _func in table:
                o = os.path.join(work_ut, rel[:-2] + ".o")
                try:
                    if o and os.path.isfile(o):
                        objs.append(o)
                    else:
                        return None
                except Exception:
                    return None
            util_dir = os.path.join(os.path.dirname(work_ut), "util")
            for rel in ("cdets.c", "curl_utils.c", "test_utils.c",
                        "st_server.c", "st_proxy.c", "ossl_srv.c"):
                o = os.path.join(util_dir, rel[:-2] + ".o")
                try:
                    if o and os.path.isfile(o):
                        objs.append(o)
                    else:
                        return None
                except Exception:
                    return None
            est_lib = ""
            for cand_base in (cfg_dir, self.source_folder, self.build_folder):
                for sub in (os.path.join("src", "est", ".libs", "libest.a"),
                            os.path.join("src", "est", "libest.a"),
                            os.path.join("src", ".libs", "libest.a")):
                    try:
                        p = os.path.join(cand_base, sub) if cand_base else ""
                        if p and os.path.isfile(p):
                            est_lib = p
                            break
                    except Exception:
                        continue
                if est_lib:
                    break
            safe_lib = ""
            for cand_base in (cfg_dir, self.source_folder, self.build_folder):
                for sub in (os.path.join("safe_c_stub", "lib", "libsafe_lib.a"),
                            os.path.join("safe_c_stub", "lib", ".libs",
                                         "libsafe_lib.a")):
                    try:
                        p = os.path.join(cand_base, sub) if cand_base else ""
                        if p and os.path.isfile(p):
                            safe_lib = p
                            break
                    except Exception:
                        continue
                if safe_lib:
                    break
            if not est_lib or not safe_lib:
                return None
            inc_flags = []
            lib_flags = []
            for key in ("cunit", "curl", "openssl"):  # curl = Conan dep lookup, not external download
                base = dep_dirs.get(key, "")
                if base and os.path.isdir(os.path.join(base, "include")):
                    inc_flags.append('-I"' + os.path.join(base, "include") + '"')
                if base and os.path.isdir(os.path.join(base, "lib")):
                    lib_flags.append('-L"' + os.path.join(base, "lib") + '"')
            for hdr in (os.path.join(self.source_folder, "src", "est"),
                        os.path.join(self.source_folder, "src"),
                        os.path.join(self.source_folder, "safe_c_stub",
                                     "include"),
                        os.path.join(self.source_folder, "test", "util"),
                        work_ut,
                        self.source_folder):
                try:
                    if hdr and os.path.isdir(hdr):
                        inc_flags.append('-I"' + hdr + '"')
                except Exception:
                    continue
            return (work_ut, src_ut, objs, est_lib, safe_lib,
                    inc_flags, lib_flags)
        except Exception:
            return None

    def _build_suite_driver(self, cfg_dir, prefix, dep_dirs):
        # Compiles run_one_suite.c and links it against the isolated inputs
        # above (make objects + est/safe archives + FIPS stub when present).
        # Returns (driver_path, run_dir) or (None, None). Never raises.
        try:
            inputs = self._isolated_build_inputs(cfg_dir, dep_dirs)
            if not inputs:
                self.output.info("libest isolated: inputs incomplete, skip")
                return (None, None)
            (work_ut, run_dir, objs, est_lib, safe_lib,
             inc_flags, lib_flags) = inputs
            table = self._suite_table()
            drv_c = os.path.join(self.build_folder, "run_one_suite.c")
            self._write_suite_driver(drv_c, table)
            cc, _cxx, _lbl = self._resolve_compiler()
            if not cc:
                cc = "clang"
            extra = (" ".join(inc_flags)
                     + " -DHAVE_CUNIT -DHAVE_LIBCURL -DNO_SSL_DL"
                       " -DENABLE_BRSKI -fcommon")
            drv_o = os.path.join(self.build_folder, "run_one_suite.o")
            try:
                self.run(prefix + '"' + cc + '" -c "' + drv_c + '" -o "'
                         + drv_o + '" ' + extra + " -fPIC",
                         cwd=self.build_folder, env="conanbuild")
            except Exception as exc:
                self.output.warning(
                    "libest isolated: driver compile failed: " + str(exc))
                return (None, None)
            try:
                if not os.path.isfile(drv_o):
                    return (None, None)
            except Exception:
                return (None, None)
            fips = os.path.join(self.build_folder, "libest_fips_stub.a")
            try:
                if not os.path.isfile(fips):
                    fips = ""
            except Exception:
                fips = ""
            out = os.path.join(self.build_folder, "run_one_suite")
            link_log = os.path.join(self.build_folder,
                                    "libest_isolated_link.log")
            cmd = (prefix + '"' + cc + '" -o "' + out + '" "' + drv_o + '" '
                   + " ".join('"' + o + '"' for o in objs)
                   + ' "' + est_lib + '" "' + safe_lib + '"'
                   + (' "' + fips + '"' if fips else '')
                   + " -lcunit -lcurl -lssl -lcrypto -ldl -lpthread -fcommon "
                   + " ".join(lib_flags))
            try:
                self.run(cmd + ' > "' + link_log + '" 2>&1',
                         cwd=work_ut, env="conanbuild")
            except Exception as exc:
                tail = ""
                try:
                    with open(link_log, "r", encoding="utf-8",
                              errors="replace") as fh:
                        tail = fh.read()[-2000:]
                except Exception:
                    pass
                self.output.warning(
                    "libest isolated: driver link failed: " + str(exc)
                    + "; log tail: " + tail)
                return (None, None)
            try:
                if os.path.isfile(out):
                    self.output.info(
                        "libest isolated: driver built " + out
                        + " objs=" + str(len(objs)))
                    return (out, run_dir)
            except Exception:
                pass
            return (None, None)
        except Exception as exc:
            self.output.warning(
                "libest isolated: driver build harness failed: " + str(exc))
            return (None, None)

    def _run_suites_isolated(self, cfg_dir, prefix, dep_dirs, command):
        # Runs each of the 35 suites in its own driver child process
        # (cwd=test/UT so relative CA/ paths resolve), parses each child
        # log from a single deterministic source, and persists the
        # HMBS_UPSTREAM_TEST_RESULT marker. Returns True when the marker
        # was persisted (caller must return immediately); False selects
        # the single-runtest fallback. Never raises.
        try:
            drv, run_dir = self._build_suite_driver(cfg_dir, prefix,
                                                    dep_dirs)
            if not drv:
                return False
            table = self._suite_table()
            per = []
            for _rel, suite, _func in table:
                slog = os.path.join(self.build_folder,
                                    "libest_suite_" + suite + ".log")
                # Hang guard: a wedged EST server/child used to hold the
                # SSH session open with no output until the host dropped it
                # ("Connection closed by remote host" with zero upstream
                # counts). Bound each child with `timeout -k` when present
                # (fallback: plain run); a timeout surfaces as rc=124 and
                # is recorded as crashed with evidence, never a hang.
                try:
                    _to = shutil.which("timeout") or ""
                except Exception:
                    _to = ""
                _tpre = (f'"{_to}" -k 10 120 ' if _to else "")
                cmd = (prefix + _tpre + '"' + drv + '" "' + suite
                       + '" > "' + slog + '" 2>&1')
                rc_ok = True
                try:
                    self.run(cmd, cwd=run_dir, env="conanrun")
                except Exception as exc:
                    rc_ok = False
                    self.output.info(
                        "libest isolated: suite " + suite
                        + " child rc!=0 (" + str(exc)[:200] + ")")
                text = ""
                try:
                    if os.path.isfile(slog):
                        with open(slog, "r", encoding="utf-8",
                                  errors="replace") as fh:
                            text = fh.read()
                except Exception:
                    text = ""
                try:
                    self.output.info("libest isolated suite " + suite
                                     + " tail:\n" + text[-1500:])
                except Exception:
                    pass
                # Single-source verdict per child: the driver-emitted
                # HMBS_SUITE_RESULT line (printed after CU_basic_run_tests)
                # is the ONLY count source. The CUnit Run Summary row is
                # the fallback single source when the driver line is absent
                # but a summary exists (init-skipped suites). Anything else
                # (crash, empty) is a crashed verdict with evidence. Never
                # mixed, never derived by subtraction across sources.
                m = re.search(
                    r"HMBS_SUITE_RESULT\s+name=\S+\s+tests_run=(\d+)"
                    r"\s+tests_failed=(\d+)", text)
                if m:
                    try:
                        trun = int(m.group(1))
                        tfail = int(m.group(2))
                    except ValueError:
                        trun, tfail = 0, 0
                    if tfail > trun:
                        tfail = trun
                    per.append((suite, "verdict", trun, tfail,
                                text[-800:]))
                    continue
                parsed = self._parse_cunit_log(text)
                if parsed is not None:
                    _t, ran, _p, failed, _i, _src = parsed
                    if ran >= 1:
                        per.append((suite, "verdict", ran, failed,
                                    text[-800:]))
                    else:
                        per.append((suite, "inactive", 0, 0,
                                    text[-800:]))
                    continue
                hint = self._crash_hint(text)
                ev = ((hint + " | ") if hint else "") + text.strip()[-800:]
                if not ev.strip():
                    ev = ("child produced no output rc_ok=" + str(rc_ok)
                          + "; searched=" + slog)
                per.append((suite, "crashed", 0, 1, ev))
            self._save_isolated_result(per, command)
            return True
        except Exception as exc:
            self.output.warning(
                "libest isolated: run harness failed: " + str(exc))
            return False

    def _save_isolated_result(self, per, command):
        # Aggregates the isolated per-suite verdicts into the 55-suite
        # audit denominator. Single-source counts: passed/failed/inactive
        # come only from the per-child verdicts above; CoAP-conditional
        # (19) and residual (US4747 never registered + version delta, 1)
        # fill the remainder with upstream-conditional taxonomy.
        # Identities: passed+failed==executed, executed+skipped==discovered,
        # gaps-sum==discovered-passed. Never raises (fail-closed marker).
        total_audit = 55
        coap_n = 19
        try:
            table_n = len(self._suite_table())
        except Exception:
            table_n = 35
        try:
            passed_names = [s for s, k, _tr, tf, _ev in per
                            if k == "verdict" and tf == 0]
            failed_names = [s for s, k, _tr, tf, _ev in per
                            if (k == "verdict" and tf > 0) or k == "crashed"]
            inactive_names = [s for s, k, _tr, _tf, _ev in per
                              if k == "inactive"]
            passed = len(passed_names)
            failed = len(failed_names)
            inactive = len(inactive_names)
            accounted = passed + failed + inactive
            unaccounted = max(table_n - accounted, 0)
            executed = passed + failed
            skipped = total_audit - executed
            gaps = []
            if failed > 0:
                fail_ev = []
                for s, k, tr, tf, ev in per:
                    if (k == "verdict" and tf > 0) or k == "crashed":
                        fail_ev.append(s + "(" + k + "):" + ev[-300:])
                        if len(fail_ev) >= 8:
                            break
                gaps.append(
                    {
                        "count": failed,
                        "category": "test_failure",
                        "detail": (
                            "isolated per-suite run: failed/aborted suites "
                            + str(failed_names[:15])),
                        "evidence": " | ".join(fail_ev)[-2000:],
                    }
                )
            if inactive > 0:
                gaps.append(
                    {
                        "count": inactive,
                        "category": "ohos_feature",
                        "detail": (
                            "CUnit suites compiled but Suite Initialization "
                            "failed on OHOS (Suite Skipped): "
                            + str(inactive_names[:15])),
                        "evidence": "per-suite logs libest_suite_<name>.log",
                    }
                )
            if unaccounted > 0:
                gaps.append(
                    {
                        "count": unaccounted,
                        "category": "test_failure",
                        "detail": (
                            "isolated driver loop did not report these "
                            "suites; harness defect, not a pass"),
                        "evidence": "per-suite logs libest_suite_<name>.log",
                    }
                )
            gaps.append(
                {
                    "count": coap_n,
                    "category": "ohos_feature",
                    "detail": (
                        "upstream-conditional CoAP suites not compiled "
                        "without LIBCOAP_DIR (19 HAVE_LIBCOAP suites: "
                        "US5052/US5139/US5184/US5213/US5226/US5230/US5237/"
                        "US5240/US5244/US5246/US5248coap/US5255/US5282/"
                        "US5331/US5357/US5367/US5394/US5399/US5418c); "
                        "upstream Makefile requires LIBCOAP_DIR + "
                        "-DHAVE_LIBCOAP"),
                    "evidence": "upstream test/UT/Makefile LIBCOAP_DIR block",
                }
            )
            residual = total_audit - table_n - coap_n
            if residual > 0:
                gaps.append(
                    {
                        "count": residual,
                        "category": "ohos_feature",
                        "detail": (
                            "audit residual: US4747 extern declared but "
                            "never registered in runtest.c + version delta"),
                        "evidence": "runtest.c registration audit",
                    }
                )
            result = {
                "status": ("passed"
                           if (failed == 0 and executed == total_audit)
                           else "failed"),
                "framework": "cunit",
                "command": command + " [isolated per-suite]",
                "discovered": total_audit,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "reason": (
                    "isolated per-suite run: suites=" + str(table_n)
                    + " (audited " + str(total_audit) + ") passed="
                    + str(passed) + " failed=" + str(failed) + " inactive="
                    + str(inactive) + " coap_missing=" + str(coap_n)
                    + " residual=" + str(residual) + "; failed_suites="
                    + str(failed_names[:15]) + "; inactive_suites="
                    + str(inactive_names[:15])),
                "gaps": gaps,
            }
        except Exception as exc:
            result = {
                "status": "failed",
                "framework": "cunit",
                "command": command + " [isolated per-suite]",
                "discovered": total_audit,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": total_audit,
                "reason": "isolated aggregation harness exception: "
                          + str(exc)[:300],
                "gaps": [
                    {
                        "count": total_audit,
                        "category": "test_failure",
                        "detail": "aggregation harness exception",
                        "evidence": str(exc)[:300],
                    }
                ],
            }
        try:
            assert result["passed"] + result["failed"] == result["executed"]
            assert result["executed"] + result["skipped"] == result["discovered"]
            assert result["executed"] <= result["discovered"]
            _gs = sum(g["count"] for g in result.get("gaps", []))
            assert _gs == result["discovered"] - result["passed"]
        except AssertionError:
            self.output.warning(
                "upstream isolated count identity violated: "
                + str(result)[:500])
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            result, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8", newline="\n") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.output.warning("write hmbs_upstream.json failed: " + str(exc))

    def _parse_cunit_log(self, log):
        # Deterministic single source: CUnit Run Summary suites row
        # (e.g. "suites 30 3 n/a 0 27"). Suites Passed is always n/a,
        # so passed = ran - failed. Verbose Suite:/Test: lines are
        # evidence only, never counts (mixing caused ran=3 vs
        # verbose-passed=1, i.e. passed+failed != executed).
        suites_total = None
        suites_ran = None
        suites_failed = 0
        suites_inactive = 0
        suites_src = ""
        m = re.search(
            r"^\s*suites\s+(\d+)\s+(\d+)\s+(n/a|\d+)\s+(\d+)\s+(\d+)",
            log, re.MULTILINE | re.IGNORECASE)
        if m:
            try:
                suites_total = int(m.group(1))
                suites_ran = int(m.group(2))
                suites_failed = int(m.group(4))
                suites_inactive = int(m.group(5))
                suites_src = "run-summary-6col"
            except ValueError:
                suites_total = None
        if suites_total is None:
            m4 = re.search(
                r"^\s*suites\s+(\d+)\s+(\d+)\s+(n/a|\d+)\s+(\d+)",
                log, re.MULTILINE | re.IGNORECASE)
            if m4:
                try:
                    suites_total = int(m4.group(1))
                    suites_ran = int(m4.group(2))
                    suites_failed = int(m4.group(4))
                    suites_inactive = 0
                    suites_src = "run-summary-4col"
                except ValueError:
                    suites_total = None
        suite_order = []
        suite_failed = {}
        current = None
        re_suite = re.compile(r"^\s*Suite\s*:\s*(.+?)\s*$", re.IGNORECASE)
        re_test = re.compile(
            r"^\s*Test\s*:.*\.\.\.\s*(passed|failed)\s*$", re.IGNORECASE)
        for line in log.splitlines():
            ms = re_suite.match(line)
            if ms:
                name = ms.group(1).strip()
                if name and name not in suite_failed:
                    suite_order.append(name)
                    suite_failed[name] = False
                current = name if name else current
                continue
            mv = re_test.match(line)
            if mv and current is not None and current in suite_failed:
                if mv.group(1).lower() == "failed":
                    suite_failed[current] = True
        observed = len(suite_order)
        # Single-source rule: Run Summary suites row is the ONLY count
        # source (total/ran/failed/inactive). Verbose Suite:/Test: lines
        # are cross-check evidence only and MUST NOT supply passed/failed
        # (previous mixing: ran from summary + passed from verbose produced
        # passed+failed != executed, e.g. ran=3 vs verbose passed=1).
        # CUnit suites Passed column is always n/a, so
        # passed = ran - failed (single-source derivation, no arithmetic
        # across sources, no returncode guess).
        if suites_total is not None:
            ran = suites_ran if isinstance(suites_ran, int) else 0
            failed_suites = suites_failed
            # Clamp: summary inconsistency (ran>total etc.) fails closed
            # by clamping, never by inventing verbose counts.
            if ran > suites_total:
                ran = suites_total
            if failed_suites > ran:
                failed_suites = ran
            passed_suites = ran - failed_suites
            total = suites_total
            return (total, ran, passed_suites, failed_suites,
                    suites_inactive, suites_src)
        if observed > 0:
            # Fallback ONLY when summary row is absent: verbose alone is
            # the single source (total=ran=observed).
            failed_suites = sum(1 for v in suite_failed.values() if v)
            passed_suites = observed - failed_suites
            return (observed, observed, passed_suites, failed_suites,
                    0, "verbose-suites-fallback")
        return None

    def _save_upstream_result(self, log, command, error=""):
        total_audit = 55
        parsed = self._parse_cunit_log(log) if log.strip() else None
        if parsed is None:
            result = {
                "status": "failed",
                "framework": "cunit",
                "command": command,
                "discovered": total_audit,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": total_audit,
                "reason": error or (
                    "runtest produced no parseable CUnit summary; "
                    "searched Run Summary tests row + Suite verdict lines; "
                    f"log tail: {log.strip()[-500:]}"),
                "gaps": [
                    {
                        "count": total_audit,
                        "category": "test_failure",
                        "detail": error or "no parseable CUnit summary",
                        "evidence": f"log tail: {log.strip()[-500:]}",
                    }
                ],
            }
        else:
            total, ran, passed, failed, inactive, src = parsed
            # Denominator must equal the audit (55); a mismatch means the
            # harness silently skipped or the version changed -> fail closed.
            # Denominator uses the 55-suite official audit; the runnable
            # subset is smaller when upstream optional features are off.
            # This recipe enables BRSKI (no extra dep, +5 suites) but not
            # CoAP (upstream requires --with-libcoap-dir/LIBCOAP_DIR; 19
            # HAVE_LIBCOAP suites: US5052/US5139/US5184/US5213/US5226/
            # US5230/US5237/US5240/US5244/US5246/US5248coap/US5255/US5282/
            # US5331/US5357/US5367/US5394/US5399/US5418c). Those are
            # upstream-conditional, not test failures: report as
            # ohos_feature with source evidence. Genuine failures stay
            # test_failure so counts remain honest.
            # Unified denominator: always the 55-suite official audit.
            # Single-source counts from _parse (Run Summary row only):
            # executed=ran, passed=ran-failed, skipped=discovered-executed.
            # identities: passed+failed==executed,
            # executed+skipped==discovered. No cross-source mixing, no
            # residual test_failure filler: every gap is attributed with
            # evidence (CoAP conditional / compiled-but-init-skipped).
            missing = max(total_audit - total, 0)
            unrun = max(total - ran, 0)
            tier = ""
            try:
                _tp = os.path.join(self.build_folder,
                                   "libest_upstream_tier.txt")
                if os.path.isfile(_tp):
                    with open(_tp, "r", encoding="utf-8",
                              errors="replace") as _th:
                        tier = _th.read().strip()
            except Exception:
                tier = ""
            gaps = []
            # Failure evidence: the log tail only shows the trailing
            # "Suite Initialization failed" list; the actual FAILED suite
            # names + assert lines are mid-log. Extract them deterministically
            # (single case-insensitive pass, no count arithmetic) so the next
            # round can target the real failures (e.g. expired test PKI vs
            # OHOS limitation). CUnit Basic prints lowercase "failed".
            fail_evidence = ""
            ran_suites = []
            try:
                _fl = []
                for _ln in log.splitlines():
                    _s = _ln.strip()
                    _low = _s.lower()
                    if "failed" in _low or "assertion" in _low:
                        _fl.append(_s)
                    _m = re.match(r"^\s*suite\s*:\s*(.+?)\s*$", _s,
                                  re.IGNORECASE)
                    if _m:
                        _nm = _m.group(1).strip()
                        if _nm and _nm not in ran_suites:
                            ran_suites.append(_nm)
                fail_evidence = "\n".join(_fl[:30])[-1500:]
                ran_suites = ran_suites[:15]
            except Exception:
                fail_evidence = ""
                ran_suites = []
            if failed > 0:
                gaps.append(
                    {
                        "count": failed,
                        "category": "test_failure",
                        "detail": (
                            "CUnit suites reported failures; ran_suites="
                            + str(ran_suites)),
                        "evidence": (
                            f"failed lines: {fail_evidence[:1000]} | "
                            f"log tail: {log.strip()[-500:]}"),
                    }
                )
            if unrun > 0:
                gaps.append(
                    {
                        "count": unrun,
                        "category": "ohos_feature",
                        "detail": (
                            "CUnit suites compiled but not run on OHOS "
                            f"(Suite Initialization failed - Suite Skipped; "
                            f"tier={tier or 'full-brski'} total={total} "
                            f"ran={ran} inactive={inactive} source={src})"),
                        "evidence": f"log tail: {log.strip()[-500:]}",
                    }
                )
            coap_n = 19 if missing >= 19 else max(missing, 0)
            if coap_n > 0:
                gaps.append(
                    {
                        "count": coap_n,
                        "category": "ohos_feature",
                        "detail": (
                            "upstream-conditional CoAP suites not "
                            "compiled without LIBCOAP_DIR "
                            f"(tier={tier or 'full-brski'} runtest "
                            f"suites total={total} of audited "
                            f"{total_audit}, source={src}); "
                            "upstream Makefile requires "
                            "LIBCOAP_DIR + -DHAVE_LIBCOAP"),
                        "evidence": f"log tail: {log.strip()[-500:]}",
                    }
                )
            rest = missing - coap_n
            if rest > 0:
                # Crash attribution (cycle-3 fix): when the run died early
                # (no Run Summary, crash signal in the log), the unstarted
                # suites are run victims, not "unregistered" suites. Report
                # them as test_failure with the crash evidence so the next
                # round targets the abort instead of re-auditing the suite
                # list. Genuinely unregistered suites (no crash) keep the
                # ohos_feature taxonomy. The count is unchanged either way,
                # so the gaps-sum identity still holds.
                _crash = self._crash_hint(log)
                if _crash:
                    gaps.append(
                        {
                            "count": rest,
                            "category": "test_failure",
                            "detail": (
                                "run aborted before these suites started "
                                f"(crash signal: {_crash}; tier="
                                f"{tier or 'full-brski'} runtest suites "
                                f"total={total} of audited {total_audit}, "
                                f"source={src})"),
                            "evidence": (
                                f"crash: {_crash} | "
                                f"log tail: {log.strip()[-500:]}"),
                        }
                    )
                else:
                    gaps.append(
                        {
                            "count": rest,
                            "category": "ohos_feature",
                            "detail": (
                                "upstream suites not registered in this build "
                                f"(total={total} of audited {total_audit}, "
                                f"source={src}; includes US4747 extern never "
                                f"registered + version delta)"),
                            "evidence": f"log tail: {log.strip()[-500:]}",
                        }
                    )
            result = {
                # Honesty gate (cycle-3 fix for rule4 "passed contradicts
                # upstream evidence"): passed requires the full 55-suite
                # audit executed with zero failures. Anything less
                # (upstream-conditional CoAP suites, residual, crashes) is
                # failed with itemised gaps, never passed-with-skipped.
                "status": ("passed"
                           if (failed == 0 and ran == total_audit)
                           else "failed"),
                "framework": "cunit",
                "command": command,
                "discovered": total_audit,
                "executed": ran,
                "passed": passed,
                "failed": failed,
                "skipped": total_audit - ran,
                "reason": (
                    f"CUnit suites total={total} (audited "
                    f"{total_audit}, source={src}) ran={ran} "
                    f"passed={passed} failed={failed} "
                    f"inactive={inactive}; "
                    f"log tail: {log.strip()[-500:]}"),
                "gaps": gaps,
            }
        # Identities (single-source, strict): passed+failed==executed,
        # executed+skipped==discovered, gaps sum == discovered-passed.
        try:
            assert result["passed"] + result["failed"] == result["executed"]
            assert result["executed"] + result["skipped"] == result["discovered"]
            assert result["executed"] <= result["discovered"]
            _gs = sum(g["count"] for g in result.get("gaps", []))
            assert _gs == result["discovered"] - result["passed"]
        except AssertionError:
            self.output.warning(
                f"upstream count identity violated: {result}")
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            result, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8", newline="\n") as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.output.warning(f"write hmbs_upstream.json failed: {exc}")

    # --- HMBS true-machine helpers (bwm/0.6.3 pattern, adapted) ---

    def _usable_shell(self):
        # HMBS capability shell=/bin/sh; the repo profile pins HNP bash
        # which exists as a file on some hosts but is not executable
        # ("inaccessible or not found"). Hard-prefer /bin/sh and never
        # return the HNP path, even if isfile() is true for it.
        import shutil as _shutil
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        _w = _shutil.which("sh") or ""
        if _w and os.path.isfile(_w):
            return _w
        for cand in (os.environ.get("SHELL", ""),
                     os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # Priority: HMBS task-local TMPDIR/TMP/TEMP (injected writable),
        # then HMBS_TMPDIR/HMBS_INSTALL, else build-local tmp. Reuse HMBS
        # values when present (never fall back to read-only /tmp).
        for var in ("TMPDIR", "TMP", "TEMP",
                    "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            try:
                os.makedirs(tmpd, exist_ok=True)
            except Exception:
                pass
        return tmpd

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang, absent on some HMBS hosts (preflight:
        ls "No such file", conftest rc=127). Keep the conf value when the
        file exists (CI worker unchanged); otherwise search true-machine
        PATH plus SDK/harmonybrew candidate dirs. Pure isfile probing, no
        X_OK probing per R49. Returns ("", "", "unresolved") when nothing
        is found (caller keeps toolchain defaults).
        """
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
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
        for d in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if d and d not in cand_dirs:
                cand_dirs.append(d)
        # Same SDK root as LD_LIBRARY_PATH's llvm/lib: sibling bin dir.
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(
                    os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")),
                                       "bin")
                    if sib not in cand_dirs:
                        cand_dirs.append(sib)
        except Exception:
            pass

        found_cc, found_cxx = "", ""
        for name in cc_names:
            w = shutil.which(name)
            if _ok(w):
                found_cc = w
                break
        for name in cxx_names:
            w = shutil.which(name)
            if _ok(w):
                found_cxx = w
                break
        if not found_cc or not found_cxx:
            for d in cand_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for n in cc_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cc = p
                            break
                if not found_cxx:
                    for n in cxx_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cxx = p
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

    def _probe_toolchain(self, cfg_dir, prefix, shell):
        # Best-effort diagnostics only; never fail the build here.
        try:
            try:
                cc = self.conf.get(
                    "tools.build:compiler_executables:c",
                    check_type=str) or ""
            except Exception:
                cc = ""
            self.output.info(f"libest probe: conf CC={cc!r} SHELL={shell}")
            probe = (
                prefix +
                'echo "libest probe: CC=$CC CFLAGS=$CFLAGS LDFLAGS=$LDFLAGS"; '
                'echo "libest probe: LD_LIBRARY_PATH=$LD_LIBRARY_PATH TMPDIR=$TMPDIR"; '
                'ls -l "$CC" 2>&1 || ls -l /data/service/hnp/bin/clang* 2>&1 || true; '
                'which clang clang++ cc gcc 2>&1 || true; '
                'ls -l /storage/Users/currentUser/usr/local/bin/clang* 2>&1 || true; '
                '"$CC" --version 2>&1 | head -5 || true; '
                'echo \'int main(){return 0;}\' > .libest_cc_probe.c; '
                '"$CC" .libest_cc_probe.c -o .libest_cc_probe 2>&1 && '
                'echo "libest probe: plain cc OK" || '
                'echo "libest probe: plain cc FAILED rc=$?"; '
                'rm -f .libest_cc_probe.c .libest_cc_probe; '
                'echo "libest probe: tmpdir writable test:"; '
                'touch "$TMPDIR/.libest_tmp_wtest" 2>&1 && echo OK || '
                'echo "TMPDIR NOT WRITABLE rc=$?"; '
                'rm -f "$TMPDIR/.libest_tmp_wtest"'
            )
            self.run(probe, cwd=cfg_dir, env="conanbuild")
        except Exception as e:
            self.output.warning(f"libest probe failed (non-fatal): {e}")

    def _dump_config_log(self, cfg_dir):
        try:
            log = os.path.join(cfg_dir, "config.log")
            if not os.path.isfile(log):
                # configure may have run in build_folder when source
                # layout differs; check there too.
                alt = os.path.join(self.build_folder, "config.log")
                if os.path.isfile(alt):
                    log = alt
                else:
                    self.output.warning(
                        "libest: config.log not found after configure "
                        "failure")
                    return
            with open(log, "r", encoding="utf-8",
                      errors="replace") as f:
                text = f.read()
            tail = text[-12000:]
            self.output.info(
                "libest config.log tail (last 12k):\n" + tail)
            m = re.search(
                r"(checking whether the C compiler works.*)", text, re.S)
            if m:
                idx = m.start()
                self.output.info(
                    "libest config.log compiler section:\n"
                    + text[idx:idx + 8000])
        except Exception as e:
            self.output.warning(f"libest: dump config.log failed: {e}")

    def _patch_autoconf_umask(self, root):
        """Replace umask 077 with umask 022 in autoconf scripts."""
        names = {"configure", "config.status"}
        patched = 0
        try:
            walker = os.walk(root)
        except Exception:
            return 0
        for _dir, _dirs, _files in walker:
            for _name in _files:
                if _name not in names:
                    continue
                _path = os.path.join(_dir, _name)
                try:
                    with open(_path, "r", encoding="utf-8",
                              errors="surrogateescape") as _f:
                        _content = _f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                _fixed = _content.replace("umask 077", "umask 022")
                _fixed = _fixed.replace("umash 077", "umash 022")
                if _fixed != _content:
                    try:
                        with open(_path, "w", encoding="utf-8",
                                  errors="surrogateescape",
                                  newline="\n") as _f:
                            _f.write(_fixed)
                    except OSError:
                        continue
                    patched += 1
                    self.output.info(
                        f"[libest] patched umask 077->022 in {_path}")
        return patched
