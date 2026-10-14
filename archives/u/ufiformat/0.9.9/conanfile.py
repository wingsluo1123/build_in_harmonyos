#!/usr/bin/env python3
"""Conan recipe — ufiformat 0.9.9 (Autotools).

ufiformat is a command-line formatter for floppy disks in UFI-compatible USB
floppy drives (single bin/ufiformat, no library). Upstream ships a generated
configure + Makefile.in (automake 1.11 era) and three C files.

OHOS notes:

  * libext2fs comes from the already-published ``e2fsprogs/1.47.4`` package
    (zerofree/1.1.1 precedent). e2fsprogs defaults to static libraries, so the
    configure probe (AC_CHECK_LIB ext2fs) and the final link both need
    ``-lcom_err -luuid`` to close the static link. The flags travel as
    configure ``VAR=value`` arguments (abiword-plugin/aamath precedent);
    upstream configure declares no AC_CANONICAL_BUILD/HOST triplet handling,
    so no --build/--host is passed (native build, R1).
  * R26: terminal tool (zerofree/1.1.1 precedent: dynamic binary;
    libext2fs itself stays static via e2fsprogs default, so no system-lib
    pollution). No full "-static" link: it broke configure's very first
    sanity link on the OHOS sysroot (Error 77).
  * R33: compilers/flags come from AutotoolsToolchain + explicit dependency
    paths; build() never reads bare shell $CC/$CFLAGS.
  * Upstream has no test suite (no TESTS/check target, audited in
    test_package/MANIFEST.yml), so build() runs no make check; the no_tests
    evidence marker is re-emitted by test_package on every run.
  * OHOS ELF self-sign (llvm-objcopy + binary-sign-tool) after make and after
    install (dkjson/backuppc-rsync precedent): unsigned binaries are SIGKILLed
    by the HongMeng kernel on exec.

License: GPL-2.0-or-later
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UfiformatConan(ConanFile):
    name = "ufiformat"
    version = "0.9.9"
    description = ("ufiformat - command-line formatter for floppy disks "
                   "in UFI-compatible USB floppy drives")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tedigh/ufiformat"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("usb", "floppy", "ufi", "format", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libext2fs lives in the already-published e2fsprogs package
        # (tarsnap/zerofree precedent: conan download verified binary).
        self.requires("e2fsprogs/1.47.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _writable_tmpdir(self):
        """E002: OHOS /tmp is a read-only erofs mount.

        Probe candidates with a real file write (HMDFS ignores chmod /
        os.access, so only open(w)+unlink counts); fall back to a
        package-isolated dir under $HOME, then build_folder/.tmp which
        conan already proved writable (mkcue/1 precedent).
        """
        candidates = []
        for var in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                candidates.append(value)
        candidates.append(os.path.join(os.path.expanduser("~"), "tmp",
                                       "ufiformat-0.9.9"))
        if self.build_folder:
            candidates.append(os.path.join(self.build_folder, ".tmp"))
        for tmpdir in candidates:
            try:
                os.makedirs(tmpdir, exist_ok=True)
                probe = os.path.join(tmpdir, ".ufiformat-tmp-write-probe")
                with open(probe, "w") as pf:
                    pf.write("ok")
                os.unlink(probe)
                return tmpdir
            except OSError:
                continue
        return self.build_folder or os.getcwd()

    def _probe_compiler(self, cc):
        """Link a hello-world with *cc* (dynamic, no -static).

        Existence + X_OK is not enough: round 2 picked harmonybrew clang
        by existence and configure still failed Error 77. Only a driver
        that really creates executables is accepted.

        CI #90634 change: distinguish permanent rejection (False) from
        transient fork pressure (None). A clang that reports
        "posix_spawn failed: Resource temporarily unavailable" is not a
        bad driver -- the worker is out of processes. Treating it as a
        hard reject wastes N more heavy forks and ends in a false
        "no usable clang found".
        """
        try:
            tmpdir = self._writable_tmpdir()
        except Exception:
            return False
        src = os.path.join(tmpdir, ".ufiformat-cc-probe.c")
        out = os.path.join(tmpdir, ".ufiformat-cc-probe")
        try:
            with open(src, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
        except OSError:
            return False
        try:
            r = subprocess.run([cc, src, "-o", out],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               timeout=120)
            ok = r.returncode == 0 and os.path.isfile(out)
            if ok:
                return True
            err = (r.stderr or b"").decode("utf-8", "replace")
            lowered = err.lower()
            transient_marks = ("resource temporarily unavailable",
                               "posix_spawn failed",
                               "can't fork", "cannot fork", "try again")
            if any(m in lowered for m in transient_marks):
                self.output.warning(
                    "ufiformat compiler probe transient (EAGAIN) on %s: %s"
                    % (cc, err.splitlines()[:2]))
                return None
            self.output.info("ufiformat compiler probe-link rejected %s: "
                             "rc=%s err=%s"
                             % (cc, r.returncode,
                                err.splitlines()[:3]))
            return False
        except Exception as exc:
            lowered = repr(exc).lower()
            if ("temporarily unavailable" in lowered
                    or "try again" in lowered
                    or "enomem" in lowered):
                self.output.warning(
                    "ufiformat compiler probe transient (EAGAIN) on %s: %r"
                    % (cc, exc))
                return None
            self.output.info("ufiformat compiler probe-link rejected %s: %r"
                             % (cc, exc))
            return False
        finally:
            for p in (src, out):
                try:
                    if os.path.isfile(p):
                        os.unlink(p)
                except OSError:
                    pass

    def _find_ohos_compilers(self):
        """Return (cc, cxx) absolute paths or (None, None).

        mkcue/1 precedent adapted: the profile conf points at
        /data/service/hnp/bin/clang which is missing on the preflight
        worker, while hmbs-prepended tool dirs on PATH hold other
        drivers. Round-3 change: candidates are accepted only after a
        real hello-world link probe (existence alone picked a driver
        that still failed configure Error 77).

        CI #90634 change (differs from CI #89570 which only lightened
        build() logging): generate() itself forked up to ~12 heavy
        clang links with duplicated candidates
        (cc_candidates listed /data/service/hnp/bin/clang three times),
        amplifying the worker's fork/EAGAIN pressure, then reported a
        false "no usable clang found". New route: dedupe candidates,
        probe the profile-canonical driver first (zero-cost isfile skip
        on preflight where it is missing, one probe on CI where it is
        canonical), and stop probing on the first transient EAGAIN
        signal -- falling back to the profile driver without further
        forks instead of sweeping the whole list.
        """
        try:
            execs = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        except Exception:
            execs = {}
        profile_c = (execs or {}).get("c")
        profile_cpp = (execs or {}).get("cpp")

        def _dedupe(items):
            seen = set()
            out = []
            for p in items:
                if not p or p in seen:
                    continue
                seen.add(p)
                out.append(p)
            return out

        candidates_cc = _dedupe([
            profile_c,
            os.environ.get("CC"),
            shutil.which("clang"),
            "/storage/Users/currentUser/usr/local/bin/clang",
            "/data/service/hnp/bin/clang",
            "/usr/bin/clang",
            "/usr/local/bin/clang",
        ] + sorted(glob.glob(
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang")))
        candidates_cxx = _dedupe([
            profile_cpp,
            os.environ.get("CXX"),
            shutil.which("clang++"),
            "/storage/Users/currentUser/usr/local/bin/clang++",
            "/data/service/hnp/bin/clang++",
            "/usr/bin/clang++",
            "/usr/local/bin/clang++",
        ] + sorted(glob.glob(
            "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang++")))

        def _pick(candidates, label):
            transient = False
            for p in candidates:
                if not (os.path.isfile(p) and os.access(p, os.X_OK)):
                    continue
                res = self._probe_compiler(p)
                if res is True:
                    return p, False
                if res is None:
                    transient = True
                    break
            if transient:
                fb = next((p for p in candidates
                           if p and os.path.isfile(p)
                           and os.access(p, os.X_OK)), None)
                self.output.warning(
                    "ufiformat compiler discovery %s transient "
                    "(EAGAIN): stop probing, fallback to %s "
                    "without further forks" % (label, fb))
                return fb, True
            return None, False

        cc, cc_transient = _pick(candidates_cc, "cc")
        cxx, cxx_transient = _pick(candidates_cxx, "cxx")
        self.output.info("ufiformat compiler discovery: cc_candidates=%s -> %s"
                         % (candidates_cc, cc))
        self.output.info("ufiformat compiler discovery: cxx_candidates=%s -> %s"
                         % (candidates_cxx, cxx))
        return cc, cxx

    def _fix_autoconf_tmpdir_for_ohos(self, path):
        """HMBS [unsafe_local_mktemp]: mktemp-made ./conf* dir unwritable.

        Round-6 change (differs from round-5): round-5 gated the whole fix
        on HMBS_AUTOCONF_MKTEMP_FALLBACK=="1" and the preflight still failed
        with an identical signature and no "tmpdir fix applied" line in the
        log -- the gate caused a silent no-op (the variable can carry a
        path form, cf. xlslib/2.5.0, or be absent on some workers). New
        route: relax umask 077->022 UNCONDITIONALLY (xylib/1.6 precedent:
        unconditional 0003-config-umask.patch, safe on every host because
        the mkdir fallback with 022 works everywhere) and force the
        conf-template mktemp probe to fail via regex (catches quoted and
        unquoted conf templates, keeps shell parens valid). Still scoped
        to configure/config.status files only (configure stage), never
        skips tests. Always logs applied/skipped with the env value so the
        next preflight proves whether the patch ran.
        """
        fb_val = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("ufiformat tmpdir fix skipped, unreadable %s: %r"
                                % (path, exc))
            return False
        original = content
        n_umask = content.count("umask 077")
        if n_umask:
            content = content.replace("umask 077", "umask 022")
        # Regex over the conf-template mktemp probe only (not every mktemp
        # on the system): `mktemp -d "./confXXXXXX"` or unquoted variants.
        # Replacement `false` keeps `(umask 022 && false)` syntactically
        # valid so the `|| { tmp=./conf$-$RANDOM; mkdir }` fallback runs.
        pattern = re.compile(r'mktemp\s+-d\s+["\']?\.?/?conf[A-Za-z0-9_.\-]*["\']?')
        content, n_mktemp = pattern.subn("false", content)
        if content == original:
            self.output.info("ufiformat tmpdir fix: no pattern in %s "
                             "(fb=%r umask077=%d)" % (path, fb_val, n_umask))
            return False
        try:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning("ufiformat tmpdir fix skipped, unwritable %s: %r"
                                % (path, exc))
            return False
        self.output.info("ufiformat tmpdir fix applied to %s "
                         "(fb=%r umask077x%d mktemp_probesx%d -> mkdir fallback)"
                         % (path, fb_val, n_umask, n_mktemp))
        return True

    def _patch_config_status_trees_for_ohos(self):
        """Patch generated config.status copies (make re-invokes them)."""
        seen = set()
        candidates = []
        for base in (self.build_folder, self.source_folder):
            if base:
                candidates.append(os.path.join(base, "config.status"))
        try:
            candidates.extend(glob.glob(
                os.path.join(self.build_folder or ".", "**", "config.status"),
                recursive=True))
        except Exception:
            pass
        for path in candidates:
            if not path or path in seen:
                continue
            seen.add(path)
            if os.path.isfile(path):
                self._fix_autoconf_tmpdir_for_ohos(path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Round-3 change: NO "-static" in extra_ldflags. Rounds 1-2 kept a
        # full-static link (backuppc-rsync precedent) and configure died in
        # its very first sanity link ("checking whether the C compiler
        # works... no", Error 77) even after a working driver was found —
        # LDFLAGS (hence -static) participates in that test link, and the
        # OHOS sysroot has no static libc to close it. zerofree/1.1.1 (same
        # e2fsprogs dep, same CLI type, already published) ships a dynamic
        # binary; libext2fs itself stays static (e2fsprogs default), so no
        # system-lib pollution (R26 core) is introduced.
        # ext2fs include/lib from the e2fsprogs package folder (never from a
        # shared system prefix). Round-4 fix: pass them as environment
        # variables (tc.environment), NOT as configure VAR=\"value\" args.
        # Preflight 2026-10-12 evidence proves the quoted-args form leaks
        # literal double quotes into the compiler invocation:
        #   clang ... \"-I/.../include\" \"-L/.../lib\" conftest.c \"-lext2fs ...\"
        #   error: no such file or directory: '\"-I/...'
        #   error: no such file or directory: '\"-lext2fs'
        # Paths contain no spaces so quotes are unnecessary; LIBS contains
        # spaces so a single configure arg cannot survive shell splitting
        # without quotes, and with quotes they leak. Environment passing
        # avoids shell quoting entirely; configure probes (AC_CHECK_LIB /
        # AC_CHECK_HEADER) and the final link read CPPFLAGS/LDFLAGS/LIBS
        # from the environment identically.
        e2fs_pkg = self.dependencies["e2fsprogs"].package_folder
        inc = os.path.join(e2fs_pkg, "include")
        lib = os.path.join(e2fs_pkg, "lib")
        _e2fs_cppflags = "-I%s" % inc
        _e2fs_ldflags = "-L%s" % lib
        _e2fs_libs = "-lext2fs -lcom_err -luuid"
        # Preflight 2026-10-12 evidence (mkcue/1 precedent): profile buildenv
        # exports SHELL/CONFIG_SHELL as /data/service/hnp/bin/bash, which is
        # inaccessible on the worker ("configure: /data/service/hnp/bin/bash:
        # inaccessible or not found") while /bin/sh is canonical. Pass SHELL
        # as configure precious-var arguments (immune to conanbuild.sh
        # sourcing order).
        tc.configure_args.extend(["SHELL=/bin/sh", "CONFIG_SHELL=/bin/sh"])
        tc.make_args.append("SHELL=/bin/sh")
        # Same round evidence: profile conf points CC at
        # /data/service/hnp/bin/clang but "checking whether the C compiler
        # works... no" (Error 77). Pass the real driver as configure
        # precious vars CC=/real/clang (CXX too for completeness).
        # Discovery prefers PATH (hmbs-prepended tool dirs), then env, then
        # the OHOS SDK llvm tree the profile LD_LIBRARY_PATH proves.
        _cc, _cxx = self._find_ohos_compilers()
        if _cc:
            tc.configure_args.append("CC=%s" % _cc)
            self.output.info("ufiformat compiler override: CC=%s" % _cc)
        else:
            self.output.warning(
                "ufiformat compiler override skipped: no usable clang found")
        if _cxx:
            tc.configure_args.append("CXX=%s" % _cxx)
        # E002: keep configure/make/mktemp temporary files off read-only /tmp.
        env = tc.environment()
        # Static libext2fs.a needs com_err + uuid to close the link; the same
        # LIBS also lets the configure-time -lext2fs probe succeed. Appended
        # (not defined-overwrite) so toolchain defaults are preserved.
        env.append("CPPFLAGS", _e2fs_cppflags)
        env.append("LDFLAGS", _e2fs_ldflags)
        env.append("LIBS", _e2fs_libs)
        self.output.info("ufiformat flags via env: CPPFLAGS+=%s LDFLAGS+=%s "
                         "LIBS+=%s" % (_e2fs_cppflags, _e2fs_ldflags,
                                       _e2fs_libs))
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # E002: process-level writable TMPDIR (write-probed).
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self.output.info("ufiformat TMPDIR probe: using %s" % tmpdir)
        if self.settings.os == "OHOS":
            # HMDFS getcwd ".." walk-up fails; export a valid PWD so shell
            # pwd trusts it instead of calling getcwd (nspr/backuppc-rsync
            # precedent). hmbs also injects SHELL + mktemp fallback.
            os.environ["PWD"] = self.build_folder
        # Log the effective C driver before configure so the next CI log
        # shows whether the failure is driver-missing or link-time.
        # generate() already passed the discovered driver as configure args;
        # this phase resolves for logging WITHOUT a hello-world link probe:
        # CI #89570 died in configure[33] with "can't fork - try again"
        # before any compiler check (true-machine preflight with the same
        # tree passed), i.e. transient fork/EAGAIN pressure. A second full
        # link-probe sweep here would fork several more clang compiles
        # immediately before configure, so only a single --version fork
        # is kept for diagnostics.
        try:
            _execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        except Exception:
            _execs = {}
        _cc = ((_execs or {}).get("c") or os.environ.get("CC")
               or shutil.which("clang") or "/data/service/hnp/bin/clang")
        self.output.info("ufiformat compiler probe: CC=%s "
                         "PATH=%s" % (_cc,
                                      os.environ.get("PATH", "")[:400]))
        try:
            _ver = subprocess.run([_cc, "--version"], capture_output=True,
                                  text=True, errors="replace", timeout=60)
            self.output.info("ufiformat compiler probe rc=%s: %s"
                             % (_ver.returncode,
                                (_ver.stdout or "").splitlines()[:1]))
        except Exception as exc:
            self.output.warning("ufiformat compiler probe failed: %r" % exc)
        # HMBS [unsafe_local_mktemp]: patch Autoconf tmpdir creation before
        # configure so ./conf* uses mkdir fallback (umask 022). Unconditional
        # file edit scoped to configure/config.status (xylib precedent).
        try:
            _conf = os.path.join(self.source_folder, "configure")
            if os.path.isfile(_conf):
                self._fix_autoconf_tmpdir_for_ohos(_conf)
        except Exception as exc:
            self.output.warning("ufiformat tmpdir pre-patch skipped: %r" % exc)
        try:
            os.umask(0o022)
        except Exception:
            pass
        os.chdir(self.build_folder)
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            # Surface the real first error: configure only prints the summary
            # line while config.log holds the failing command.
            _logs = []
            for _pat in (os.path.join(self.build_folder, "config.log"),
                         os.path.join(self.build_folder, "**", "config.log"),
                         os.path.join(self.source_folder, "config.log")):
                _logs.extend(glob.glob(_pat, recursive=True))
            _seen = set()
            for _log in _logs:
                if _log in _seen:
                    continue
                _seen.add(_log)
                try:
                    with open(_log, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _lines = _fh.read().splitlines()
                    # The tail alone ("configure: exit 77") hid the cause in
                    # round 2: first dump the failing sanity-link section,
                    # then a short tail. Bounded (~55 lines max).
                    _idx = next((i for i, l in enumerate(_lines)
                                 if "cannot create executables" in l), None)
                    if _idx is not None:
                        self.output.info("ufiformat config.log failing "
                                         "section (%s, around line %d):"
                                         % (_log, _idx + 1))
                        for _line in _lines[max(0, _idx - 35):_idx + 10]:
                            self.output.info("ufiformat-config-log| %s"
                                             % _line)
                    self.output.info("ufiformat config.log tail (%s, last 20):"
                                     % _log)
                    for _line in _lines[-20:]:
                        self.output.info("ufiformat-config-log| %s" % _line)
                except OSError as exc:
                    self.output.warning("ufiformat config.log unreadable %s: "
                                        "%r" % (_log, exc))
            if not _seen:
                self.output.warning(
                    "ufiformat config.log not found under build/source "
                    "folders; searched build/config.log, build/**/config.log,"
                    " source/config.log")
            raise
        # config.status re-creates ./conf* during make; patch its copies too.
        try:
            self._patch_config_status_trees_for_ohos()
        except Exception as exc:
            self.output.warning("ufiformat tmpdir post-patch skipped: %r" % exc)
        # -j1 per OHOS platform constraint (hmbs injects tools.build:jobs=1).
        autotools.make(args=["-j1", "SHELL=/bin/sh"])
        # Upstream ships no test suite (audited): no make check here; the
        # no_tests evidence marker is emitted by test_package instead.
        if self.settings.os == "OHOS":
            candidate = os.path.join(self.build_folder, "ufiformat")
            if os.path.isfile(candidate):
                self._sign_ohos_binary(candidate)
            else:
                raise ConanException(
                    "ufiformat binary not produced by make: %s" % candidate)

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["SHELL=/bin/sh"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if self.settings.os == "OHOS":
            pkg_bin = os.path.join(self.package_folder, "bin", "ufiformat")
            if os.path.isfile(pkg_bin):
                self._sign_ohos_binary(pkg_bin)

    def package_info(self):
        # CLI package (bin/ufiformat), no library to link.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _sign_ohos_binary(self, bin_path):
        """OHOS ELF self-sign (dkjson/backuppc-rsync precedent).

        Idempotent: strip a stale .codesign section, then self-sign with
        binary-sign-tool. chmod is best-effort (HMDFS may report
        HMBS_CAP_CHMOD=0).
        """
        for tool in ("/data/service/hnp/bin/llvm-objcopy",
                     shutil.which("llvm-objcopy") or "llvm-objcopy"):
            try:
                subprocess.run([tool, "--remove-section", ".codesign",
                                bin_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               check=False, timeout=10)
                break
            except Exception:
                continue
        signed = False
        for tool in ("/data/service/hnp/bin/binary-sign-tool",
                     shutil.which("binary-sign-tool") or "binary-sign-tool"):
            try:
                result = subprocess.run(
                    [tool, "sign", "-inFile", bin_path,
                     "-outFile", bin_path, "-selfSign", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=15)
                if result.returncode == 0:
                    signed = True
                    self.output.info("OHOS self-signed %s with %s"
                                     % (bin_path, tool))
                    break
            except Exception:
                continue
        if not signed:
            self.output.warning("OHOS signing failed for %s "
                                "(binary-sign-tool not found or error)"
                                % bin_path)
        try:
            os.chmod(bin_path, 0o755)
        except OSError:
            pass
