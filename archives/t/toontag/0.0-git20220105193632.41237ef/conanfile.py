#!/usr/bin/env python3
"""Conan recipe — toontag 0.0-git20220105193632.41237ef (Autotools).

TooN Algorithm Library (TaG): a grab bag of estimation / geometry algorithms
built on TooN (kalman filter, absolute orientation, five-point essential
matrix, hand-eye, RANSAC, unscented transform, ...).

Upstream: https://github.com/edrosten/tag
Commit: 41237efe686d286bc9009eae70d1758b7c6282c5 (2022-01-05, merge of PR #2
"Build fixes: Remove references to TR1").
License: BSD-2-Clause (COPYING).
Build system: GNU Autotools (configure.in + Makefile.am + libtool,
produces libtoontag.la and installs tag/*.h).

OHOS adaptations (all required for the upstream build to work on OHOS):
 1. TooN headers come from the conan package
    toon/0.0-git20240623085717.2982ecc: configure gets
    --with-TooN=<toon>/include and AutotoolsDeps injects the same -I into
    CPPFLAGS for both configure checks and the build.
 2. Upstream headers use <tr1/tuple> / <tr1/array> unless NEWCPPSTD (or
    WIN32) is defined; tr1 does not exist in libc++ / C++17, so the build
    adds -DNEWCPPSTD (same fix as Debian debian/rules for bug #1133653)
    and exports the define to consumers via package_info().
 3. Upstream ships no test suite (no TESTS / check_PROGRAMS / ctest /
    gtest / pytest anywhere; test/ holds 4 manual demo programs, see
    test_package/MANIFEST.yml audit), so build() runs no make check and
    emits the honest HMBS_UPSTREAM_TEST_RESULT status "no_tests".
 4. OHOS HMDFS getcwd fix (DRAFT-cvsgraph-bash-getcwd / E386): hnp bash
    is broken in conan build dirs, so OHOS build()/package() run
    configure explicitly via capability-probed /system/bin/sh with
    CONFIG_SHELL/SHELL pinned; Linux keeps the default Autotools path.
 5. Old (2005) config.guess cannot recognize HarmonyOS
    ("cannot guess build type"); OHOS passes explicit
    --build/--host triplets derived from settings (native build==host,
    aarch64-unknown-linux-gnu vendor accepted by stock config.sub).

R32: validate() checks settings.os in ("Linux", "OHOS").
R34: test_package/ builds and runs a consumer that really calls the
packaged library (quartic solver, absolute orientation, essential matrix).
R38: pure library package (no commands.json needed).
"""

import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, load, rm, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

REQUIRED_TOON = "toon/0.0-git20240623085717.2982ecc"
REQUIRED_LAPACK = "lapack/3.12.1"

UPSTREAM_REASON = (
    "edrosten/tag @ 41237efe686d286bc9009eae70d1758b7c6282c5 audited: "
    "Makefile.am defines only libtoontag.la (no TESTS/check_PROGRAMS); "
    "configure.in has no test macros; no CTest/gtest/pytest wiring; "
    "test/ holds 4 manual demo programs (absorient/fivepoint/handeye/sim), "
    "not a runnable suite (audit in test_package/MANIFEST.yml)"
)


class ToontagConan(ConanFile):
    name = "toontag"
    version = "0.0-git20220105193632.41237ef"
    description = "TooN Algorithm Library: estimation and geometry algorithms built on TooN"
    license = "BSD-2-Clause"
    homepage = "http://www.edwardrosten.com/cvd/tag.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # tag/*.h publicly includes <TooN/*.h>, so consumers of toontag
        # need the toon headers too: propagate them transitively.
        # Without transitive_headers=True the library itself builds
        # (its own compile sees toon) but test_package consumers fail
        # with "fatal error: 'TooN/TooN.h' file not found".
        self.requires(REQUIRED_TOON, transitive_headers=True)
        # tag/absorient.h inlines TooN::SVD (TooN/SVD.h unconditionally
        # calls Fortran dgesvd_/sgesvd_ via TooN/lapack.h; there is no
        # builtin fallback). Any consumer instantiating
        # computeOrientationScale/computeAbsoluteOrientation/computeRotation
        # must link LAPACK. True-device link proved it:
        # "undefined symbol: dgesvd_" in test_toontag. In-repo
        # lapack/3.12.1 (reference BLAS, device-native flang build)
        # closes it on OHOS; Linux consumers fall back to system libs.
        if str(self.settings.os) == "OHOS":
            self.requires(REQUIRED_LAPACK, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "toontag is adapted for Linux and OHOS, not %s" % self.settings.os
            )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        # api.github.com tarball URL has no file extension, so conan cannot
        # infer the archive type (defaults to zip -> BadZipFile). Pass an
        # explicit .tar.gz filename like sibling toon does; bytes/sha256
        # unchanged.
        get(self, filename="toontag.tar.gz",
            **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            build_triplet, host_triplet = self._hmbs_triplets()
            tc.configure_args.append("--build=%s" % build_triplet)
            tc.configure_args.append("--host=%s" % host_triplet)
        toon_include = os.path.join(
            self.dependencies["toon"].package_folder, "include"
        ).replace("\\", "/")
        tc.configure_args.append("--with-TooN=%s" % toon_include)
        # Upstream headers need NEWCPPSTD to use <tuple>/<array> instead of
        # removed TR1 headers (Debian bug #1133653, same fix as debian/rules).
        tc.extra_cxxflags.append("-DNEWCPPSTD")
        tc.generate()

    def _ensure_writable_tmp(self):
        # HMBS true-device mounts /tmp read-only; reuse the injected writable
        # TMPDIR/TMP/TEMP (plus HOME/tmp and build-local fallback) so that
        # configure/conftest probes and libtool can write temp files.
        # Only redirects the temp root, never skips any build step.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                return cand
            except Exception:
                continue
        return None

    def _hmbs_triplet_arch(self, arch):
        # Experience 1 (serf/1.3.10): derive the GNU arch from settings;
        # armv8 is conan's enum for AArch64.
        return {"armv8": "aarch64"}.get(str(arch), str(arch))

    def _hmbs_triplets(self):
        # Old (2005-02-10) config.guess cannot recognize the HongMeng
        # kernel (UNAME_SYSTEM=HarmonyOS) -> "cannot guess build type".
        # Bypass config.guess entirely with explicit --build/--host.
        # Native preflight build so build == host; linux-gnu vendor is
        # accepted by stock 2005 config.sub without patching (serf/edlin
        # precedent). Never use an -ohos vendor here: 2005 config.sub
        # predates OHOS and would reject it.
        host_arch = self._hmbs_triplet_arch(self.settings.arch)
        host = "%s-unknown-linux-gnu" % host_arch
        try:
            build_arch = self._hmbs_triplet_arch(self.settings_build.arch)
        except Exception:
            build_arch = host_arch
        try:
            build_os = str(self.settings_build.os)
        except Exception:
            build_os = str(self.settings.os)
        if build_os in ("OHOS", "Linux"):
            build = "%s-unknown-linux-gnu" % build_arch
        else:
            build = host
        return build, host

    def _drop_umask_077_in_place(self, path):
        # E114 (HMDFS): drop `umask 077 && ` from the configure temp-dir
        # branches so mktemp/mkdir create a writable group-readable dir.
        # HMDFS forces setgid on directories; `umask 077 && mktemp -d`
        # creates a drwx--S--- temp dir that is not writable even by its
        # owner, so config.status aborts with
        # "can't create ./conf*/subs1.awk: Permission denied" and
        # "could not setup config files machinery". Verbatim mechanism of
        # the gate-passing abiword-plugin-*/3.0.8, afflib, ancient and
        # argyll-cms recipes: patch the `configure` file itself (its
        # literal block is copied verbatim into the generated
        # config.status via `cat >>$CONFIG_STATUS <<\\_ACEOF`), before
        # configure runs, configure-phase only. Both branches are
        # patched: the mktemp branch AND autoconf's own
        # `(umask 077 && mkdir)` fallback, which fails identically.
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
        except OSError as exc:
            self.output.warning(
                "HMBS diag umask patch skipped (read %s: %s)" % (path, exc))
            return False
        orig = data
        data = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        if data == orig:
            if 'mktemp -d "./confXXXXXX"' in orig:
                self.output.info(
                    "HMBS diag umask patch: mktemp branch already umask-free")
            else:
                self.output.info(
                    "HMBS diag umask patch: pattern not found, nothing to do")
            return False
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(data)
        except OSError as exc:
            self.output.warning(
                "HMBS diag umask patch save failed: %s" % exc)
            return False
        self.output.info("HMBS diag dropped umask 077 in %s" % path)
        return True

    def _mktemp_conf_shim(self, tmpdir, shell):
        # HMBS platform diagnosis [unsafe_local_mktemp]: shadow mktemp
        # during the configure step only, so any
        # `mktemp ... *conf*...` call fails and autoconf takes its mkdir
        # fallback (already umask-free via _drop_umask_077_in_place, hence
        # writable). All other mktemp calls delegate to the real binary.
        # Same mechanism as the gate-passing alberta/3.1.1 recipe; the
        # shebang uses the capability-probed clean shell of this worker.
        # Best-effort under HMBS_CAP_CHMOD=0: even if chmod fails and the
        # shim stays non-executable, PATH lookup simply skips it and the
        # umask-free real mktemp still yields a writable dir.
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError as exc:
            self.output.info("HMBS diag mktemp shim skipped (mkdir: %s)" % exc)
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        real_mktemp = shutil.which("mktemp") or ""
        candidates = " ".join(
            c for c in (real_mktemp, "/system/bin/mktemp",
                        "/bin/mktemp", "/usr/bin/mktemp") if c)
        script = (
            "#!%s\n" % shell +
            "for arg in \"$@\"; do\n" +
            "  case \"$arg\" in\n" +
            "    *conf*) exit 1 ;;\n" +
            "  esac\n" +
            "done\n" +
            "for candidate in %s; do\n" % candidates +
            "  if [ -x \"$candidate\" ]; then\n" +
            "    exec \"$candidate\" \"$@\"\n" +
            "  fi\n" +
            "done\n" +
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError as exc:
                self.output.info(
                    "HMBS diag mktemp shim chmod best-effort failed: %s" % exc)
            self.output.info("HMBS diag mktemp conf shim: %s" % shim)
        except OSError as exc:
            self.output.info("HMBS diag mktemp shim write failed: %s" % exc)
            return ""
        return shim_dir

    def _probe_shell_clean(self, cand):
        # E386 capability probe: accept a shell only when `pwd` in the real
        # build directory returns 0 with no getcwd diagnostics on either
        # stream (rc alone is not sufficient on HMDFS).
        try:
            cwd = getattr(self, "build_folder", None) or os.getcwd()
            os.makedirs(cwd, exist_ok=True)
            p = subprocess.run(
                [cand, "-c", "pwd"],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
            )
            out = (p.stdout or b"").decode("utf-8", "replace")
            err = (p.stderr or b"").decode("utf-8", "replace")
            if p.returncode != 0:
                return False
            blob = out + err
            if "getcwd" in blob or "retrieving current directory" in blob:
                return False
            return True
        except Exception:
            return False

    def _select_clean_shell(self):
        # Draft DRAFT-cvsgraph-bash-getcwd: hnp bash getcwd is broken in
        # conan build dirs (HMDFS FUSE); /system/bin/sh (toybox) is clean.
        # Probe in order, never assume per-device bash works.
        for cand in ("/system/bin/sh", "/bin/sh"):
            try:
                if os.path.isfile(cand) and self._probe_shell_clean(cand):
                    return cand
            except Exception:
                continue
        for cand in (os.getenv("SHELL"), "/data/service/hnp/bin/bash"):
            try:
                if cand and os.path.isfile(cand) and self._probe_shell_clean(cand):
                    return cand
            except Exception:
                continue
        return "/system/bin/sh"

    def _ensure_autotools_executable(self):
        # CI #93950: `make install` fails with
        # `install-sh: can't execute: Permission denied` (Error 126).
        # The api.github.com tarball extracts without the +x bit on some
        # workers (preflight device kept it, CI worker did not), while
        # configure itself was invoked explicitly via `$SHELL configure`
        # so the build succeeded and only the direct `install-sh` exec
        # failed. Restore +x on all autotools helper scripts in both the
        # source tree and the (out-of-source) build tree, best-effort
        # (chmod may be unsupported on some mounts; then the shell
        # fallback in package() covers it).
        for base in (getattr(self, "source_folder", None),
                      getattr(self, "build_folder", None)):
            if not base or not os.path.isdir(base):
                continue
            for name in ("configure", "install-sh", "missing",
                          "config.guess", "config.sub", "depcomp",
                          "mkinstalldirs", "ltmain.sh"):
                path = os.path.join(base, name)
                try:
                    if os.path.isfile(path):
                        os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.info(
                        "HMBS diag chmod best-effort failed %s: %s"
                        % (path, exc))
        self.output.info("HMBS diag restored +x on autotools helpers")

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        # Dual-channel: conan output + raw stdout so preflight catches it.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning("HMBS diag persist upstream failed: %s" % e)

    def build(self):
        self._ensure_writable_tmp()
        if str(self.settings.os) == "OHOS":
            # HMDFS getcwd fix (DRAFT-cvsgraph-bash-getcwd / E386): hnp bash
            # is broken in conan build dirs, so configure must run explicitly
            # under a capability-probed /system/bin/sh with CONFIG_SHELL and
            # SHELL pinned (else autoconf bakes hnp bash into Makefile SHELL
            # and make/config.status fail again). Inline VAR=val prefix is
            # required: conanbuild.sh sourcing would overwrite os.environ.
            clean_sh = self._select_clean_shell()
            os.environ["CONFIG_SHELL"] = clean_sh
            os.environ["SHELL"] = clean_sh
            tc = AutotoolsToolchain(self)
            configure_args = list(tc.configure_args)
            if str(self.settings.os) == "OHOS":
                build_triplet, host_triplet = self._hmbs_triplets()
                if not any(a.startswith("--build=") for a in configure_args):
                    configure_args.append("--build=%s" % build_triplet)
                if not any(a.startswith("--host=") for a in configure_args):
                    configure_args.append("--host=%s" % host_triplet)
                self.output.info("HMBS diag triplets: build=%s host=%s"
                                 % (build_triplet, host_triplet))
            toon_include = os.path.join(
                self.dependencies["toon"].package_folder, "include"
            ).replace("\\", "/")
            if not any(a.startswith("--with-TooN=") for a in configure_args):
                configure_args.append("--with-TooN=%s" % toon_include)
            self._ensure_autotools_executable()
            configure_path = os.path.join(
                self.source_folder, "configure").replace("\\", "/")
            # HMDFS mktemp fix (round 2): unconditional on OHOS, no probe
            # gate that could silently skip. (a) drop `umask 077 && ` from
            # both temp-dir branches of the configure that runs (E114);
            # (b) shadow `mktemp *conf*` on PATH for the configure step
            # only so autoconf takes the now-writable mkdir fallback
            # ([unsafe_local_mktemp] platform prescription).
            try:
                self._drop_umask_077_in_place(configure_path)
            except Exception as _me:
                self.output.info("HMBS diag umask patch skipped: %s" % _me)
            _shim_dir = ""
            _saved_path = os.environ.get("PATH", "")
            try:
                _tmp_base = (os.environ.get("TMPDIR")
                             or os.path.join(self.build_folder, ".tmp"))
                _shim_dir = self._mktemp_conf_shim(_tmp_base, clean_sh)
                if _shim_dir:
                    os.environ["PATH"] = _shim_dir + os.pathsep + _saved_path
                    self.output.info(
                        "HMBS diag configure PATH shadowed: %s" % _shim_dir)
            except Exception as _me:
                self.output.info("HMBS diag mktemp shim skipped: %s" % _me)
            cmd = "CONFIG_SHELL=%s SHELL=%s %s %s %s" % (
                shlex.quote(clean_sh),
                shlex.quote(clean_sh),
                shlex.quote(clean_sh),
                shlex.quote(configure_path),
                " ".join(shlex.quote(a) for a in configure_args),
            )
            self.output.info("HMBS diag clean shell: %s" % clean_sh)
            try:
                self.run(cmd, env="conanbuild")
            finally:
                try:
                    os.environ["PATH"] = _saved_path
                except Exception:
                    pass
            # Makefile SHELL is now the clean shell; still pass SHELL
            # explicitly so make recipes never fall back to hnp bash.
            self.run("make -j1 SHELL=%s" % shlex.quote(clean_sh),
                      env="conanbuild")
        else:
            self._ensure_autotools_executable()
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()
        # Upstream ships no test suite (audited, see test_package/MANIFEST.yml):
        # honest no_tests marker, never a faked pass.
        self._hmbs_emit_upstream({
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (no check target upstream)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": UPSTREAM_REASON,
        })

    def package(self):
        self._ensure_writable_tmp()
        if str(self.settings.os) == "OHOS":
            clean_sh = os.getenv("CONFIG_SHELL") or self._select_clean_shell()
            # Upstream prefix is "/" (AutotoolsToolchain default); staging
            # must go through DESTDIR, otherwise `make install` writes to
            # the absolute prefix (//lib -> read-only on the device).
            # CI #93950: install-sh lost +x on extraction -> restore it
            # here too (package() may run from cache without build()).
            self._ensure_autotools_executable()
            dest = self.package_folder.replace("\\", "/")
            self.run("make install DESTDIR=%s SHELL=%s"
                     % (shlex.quote(dest), shlex.quote(clean_sh)),
                     env="conanbuild")
        else:
            self._ensure_autotools_executable()
            autotools = Autotools(self)
            autotools.install()
        # libtool helper archives are not shipped.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Carry the honest upstream result into the package so cache-hit
        # test_package runs can re-emit without re-running the build.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                copy(self, "hmbs_upstream.json", src=os.path.dirname(src),
                     dst=dst_dir)
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s" % e)

    def package_info(self):
        self.cpp_info.libs = ["toontag"]
        # Consumers include tag/*.h, which needs NEWCPPSTD exactly like the
        # library build itself (see generate()).
        self.cpp_info.defines = ["NEWCPPSTD"]
        self.cpp_info.requires = ["toon::toon"]
        # SVD-backed headers (absorient) need LAPACK at consumer link time
        # (dgesvd_). Propagate the in-repo lapack on OHOS so CMakeDeps
        # adds liblapack/libblas/FortranRuntime to the link line.
        # lapack/3.12.1 validates OHOS-only, so Linux keeps system libs.
        if str(self.settings.os) == "OHOS":
            self.cpp_info.requires.append("lapack::lapack")
        else:
            self.cpp_info.system_libs = ["lapack", "blas"]
        self.cpp_info.set_property("cmake_file_name", "toontag")
        self.cpp_info.set_property("cmake_target_name", "toontag::toontag")
        self.cpp_info.set_property("pkg_config_name", "toontag")
