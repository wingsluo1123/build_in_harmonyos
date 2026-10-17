#!/usr/bin/env python3
"""Conan recipe — xdffileio 0.3 (Autotools).

xdffileio — MindMaze unified EEG file-format I/O library (EDF/BDF/GDF1/GDF2).
Upstream 0.3 is an autotools-only GNU package (configure + Makefile.in ship in
the Debian orig tarball, no autoreconf/gnulib bootstrap needed on device).

OHOS aarch64 notes:
- xdffileio 0.3 has NO mmlib dependency: upstream 0.3 configure.ac and all
  .c/.h/.am sources contain zero references to mmlib/MM_CHECK_LIB (verified
  against the xdffileio-0.3 tag tarball); mmlib is only required by modern
  xdffileio >= 1.0. No requires() and no vendoring needed.
  Upstream configure is probed via AutotoolsToolchain with vendored
  OHOS-aware build-aux/config.guess+config.sub (E007: the shipped 2012
  scripts cannot guess HarmonyOS) and identical --build/--host native
  triplets (es-shell/0.9.2 precedent).
- Upstream test suite (automake TESTS in tests/Makefile.am) runs in build()
  via `make check`; results are parsed from tests/test-suite.log and emitted
  as HMBS_UPSTREAM_TEST_RESULT. `make check` is never removed.
- Static default (shared=False) avoids libtool versioned-soname symlinks on
  hmdfs; shared builds are still supported and re-signed after install.
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XdffileioConan(ConanFile):
    name = "xdffileio"
    version = "0.3"
    description = "Unified interface to read/write EEG data file formats (EDF, BDF, GDF)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/mmlabs-mindmaze/xdffileio"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("eeg", "bdf", "edf", "gdf", "biosignal")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Vendored OHOS-aware build-aux scripts (full-file replacements,
        # not diffs): toybox patch on device applies new-file diffs for
        # real, so ship them via copy like es-shell/0.9.2 (same files).
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xdffileio/0.3 only supports Linux/OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E007: the 2012 build-aux/config.guess cannot recognize HarmonyOS
        # (uname -s), so configure dies with "cannot guess build type".
        # Pass identical --build/--host (native, NOT cross: build == host,
        # same as es-shell/0.9.2) once build-aux is refreshed below; the
        # refreshed config.sub canonicalizes both spellings to
        # aarch64-unknown-linux-ohos.
        for triplet in ("--build=aarch64-unknown-linux-ohos",
                        "--host=aarch64-unknown-linux-ohos"):
            if triplet not in tc.configure_args:
                tc.configure_args.append(triplet)
        # DESTDIR install (bwm/0.6.3 precedent): normalize prefix to / so
        # `make install DESTDIR=<package_folder>` lands in
        # <package_folder>/lib + <package_folder>/include instead of the
        # toolchain-default absolute prefix (which would nest) or an empty
        # prefix (which installs to /lib on device, Read-only FS). Plain
        # `make install` without DESTDIR is forbidden here.
        tc.configure_args = [
            a for a in tc.configure_args if not str(a).startswith("--prefix")
        ]
        tc.configure_args.append("--prefix=/")
        # Keep toolchain args for build(): configure is run explicitly
        # through the usable shell (see build()), not via direct exec.
        self._my_configure_args = list(tc.configure_args)
        tc.generate()
        # True-machine guard: the repo profile pins
        # SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash, which is
        # inaccessible on some HMBS hosts (configure dies with
        # "inaccessible or not found", then
        # "cannot run /data/service/hnp/bin/bash .../build-aux/config.sub",
        # Error 127). HMBS injects SHELL=/bin/sh (capabilities
        # shell=/bin/sh). Save a build-scope env script so every
        # conanbuild aggregation (configure/make) sees a usable shell
        # plus a writable TMPDIR. Generated scripts win over the profile
        # [buildenv], while inline os.environ tweaks in build() alone
        # do not (bwm/0.6.3 precedent).
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
        env.vars(self, scope="build").save_script("xdffileio_hmos_fix")
        self.output.info(
            "xdffileio_hmos_fix: SHELL/CONFIG_SHELL=%s TMPDIR=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, _lbl, _cc, _cxx)
        )
        # Refresh stale 2012 build-aux scripts with the vendored OHOS-aware
        # ones (same files as es-shell/0.9.2). Idempotent: safe to repeat
        # in build() for cached-source runs.
        self._stage_build_aux()

    def _usable_shell(self):
        # HMBS capability shell=/bin/sh; the repo profile pins HNP bash
        # which exists as a file on some hosts but is not executable
        # ("inaccessible or not found"). Hard-prefer /bin/sh and never
        # return the HNP path, even if isfile() is true for it.
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
        # Priority: HMBS task-local TMPDIR/TMP/TEMP (injected writable),
        # then HMBS_TMPDIR/HMBS_INSTALL, else build-local tmp. Reuse HMBS
        # values when present (never fall back to read-only /tmp).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Keep the profile tools.build:compiler_executables value when the
        file exists (CI worker unchanged); otherwise search PATH plus
        SDK/harmonybrew candidate dirs. Pure isfile probing, no X_OK
        probing. Returns ("", "", "unresolved") when nothing is found
        (caller keeps toolchain defaults).
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
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
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

    def _fixed_env_prefix(self, shell, tmpdir, cc, cxx):
        # Inline exports that run AFTER conanbuild.sh is sourced, so the
        # good values win over the profile's stale HNP bash in the same
        # shell invocation (juise-style, bwm/0.6.3 precedent). Do NOT use
        # Autotools.configure()/make(): the helper re-exports the stale
        # CONFIG_SHELL via env="conanbuild" after a plain os.environ
        # override. Run everything explicitly via the usable shell.
        prefix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
        ) % (shell, shell, tmpdir, tmpdir, tmpdir)
        if cc:
            prefix += 'export CC="%s" && ' % cc
            os.environ["CC"] = cc
        if cxx:
            prefix += 'export CXX="%s" && ' % cxx
            os.environ["CXX"] = cxx
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        return prefix

    def _stage_build_aux(self):
        """Overwrite stale 2012 build-aux/config.guess+config.sub.

        The Debian orig tarball ships 2012-02-10 scripts whose config.guess
        has no HarmonyOS branch (E007): `unable to guess system type` /
        `cannot guess build type`. The vendored replacements (byte-identical
        to es-shell/0.9.2's OHOS-aware FSF 2023 scripts) map
        *:HarmonyOS:* to aarch64-unknown-linux-ohos and teach config.sub
        the linux-ohos OS. No conandata diff entries: full-file vendoring
        via export_sources copy (es-shell precedent).
        """
        aux_dir = os.path.join(self.source_folder, "build-aux")
        if not os.path.isdir(aux_dir):
            try:
                entries = sorted(os.listdir(self.source_folder))
            except OSError as e:
                entries = ["<unlistable: %s>" % e]
            raise ConanException(
                "xdffileio: build-aux dir missing in %s (entries: %s); "
                "cannot refresh config.guess/config.sub" % (self.source_folder, entries)
            )
        staged = os.path.join(self.export_sources_folder, "patches", "build-aux")
        for name in ("config.guess", "config.sub"):
            src = os.path.join(staged, name)
            dst = os.path.join(aux_dir, name)
            if not os.path.isfile(src):
                raise ConanException("xdffileio: vendored script missing: %s" % src)
            shutil.copyfile(src, dst)
            # CRLF guard: Windows checkouts may carry CRLF into the vendored
            # scripts (config.sub/config.guess fail under /bin/sh with
            # "inaccessible or not found" + "syntax error: unexpected 'in\r'").
            # Normalize to LF at stage time so device runs are immune to the
            # checkout's line endings (plus .gitattributes eol=lf long-term).
            try:
                with open(dst, "rb") as f:
                    data = f.read()
                norm = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                if norm != data:
                    with open(dst, "wb") as f:
                        f.write(norm)
                    self.output.info(
                        "xdffileio: normalized CRLF->LF in build-aux/%s" % name
                    )
            except OSError as e:
                raise ConanException(
                    "xdffileio: failed to normalize line endings in %s: %s" % (dst, e)
                )
            try:
                os.chmod(dst, 0o755)
            except OSError:
                pass  # HMDFS chmod=0: scripts run via explicit shell, no +x needed
            self.output.info("xdffileio: refreshed build-aux/%s (%d bytes)" % (name, os.path.getsize(dst)))

    def _verify_build_aux(self, shell):
        """Prove the refreshed scripts work before configure runs."""
        aux_dir = os.path.join(self.source_folder, "build-aux")
        # config.sub must canonicalize the ohos triplet (raises otherwise).
        self.run(
            '"%s" "%s" aarch64-unknown-linux-ohos' % (shell, os.path.join(aux_dir, "config.sub")),
            cwd=self.source_folder,
        )
        # config.guess output is device evidence (expect ...-linux-ohos).
        self.run(
            '"%s" "%s"' % (shell, os.path.join(aux_dir, "config.guess")),
            cwd=self.source_folder,
        )

    def _configure_args(self):
        """Rebuild the configure CLI deterministically in build().

        generate()'s self._my_configure_args may not survive when Conan
        runs generate/build on separate instances, so union fresh toolchain
        defaults with the stored extras plus the mandatory OHOS triplets
        and static flags (deduped). build == host stays native.
        """
        args = list(AutotoolsToolchain(self).configure_args)
        for extra in getattr(self, "_my_configure_args", []):
            if extra not in args:
                args.append(extra)
        # Same DESTDIR normalization as generate(): drop any toolchain-default
        # absolute --prefix and enforce --prefix=/ (deduped). Guarantees the
        # build-tree configure matches the package() DESTDIR install even when
        # generate() was skipped (cached-source runs).
        args = [a for a in args if not str(a).startswith("--prefix")]
        args.append("--prefix=/")
        for triplet in ("--build=aarch64-unknown-linux-ohos",
                        "--host=aarch64-unknown-linux-ohos"):
            if triplet not in args:
                args.append(triplet)
        if not self.options.shared:
            for flag in ("--enable-static", "--disable-shared"):
                if flag not in args:
                    args.append(flag)
        return args

    def _dump_config_log(self, cfg_dir):
        try:
            log = os.path.join(cfg_dir, "config.log")
            if not os.path.isfile(log):
                self.output.warning("xdffileio: config.log not found after configure failure")
                return
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            tail = text[-12000:]
            self.output.info("xdffileio config.log tail (last 12k):\n" + tail)
        except Exception as e:
            self.output.warning("xdffileio: dump config.log failed: %s" % e)

    def _parse_autotools_suite(self, build_folder):
        """Parse automake test-suite.log for deterministic HMBS counts.

        Reads the `# TOTAL/# PASS/# FAIL/# SKIP/# XFAIL/# XPASS/# ERROR`
        summary block (never counts stdout substrings). Returns a dict with
        discovered/executed/passed/failed/skipped plus the raw block.
        Returns (None, searched, "") when no test-suite.log exists so the
        caller can fall back to the serial-harness check log.
        """
        candidates = [
            os.path.join(build_folder, "tests", "test-suite.log"),
            os.path.join(self.source_folder, "tests", "test-suite.log"),
            os.path.join(build_folder, "test-suite.log"),
        ]
        logfile = next((p for p in candidates if os.path.isfile(p)), None)
        searched = candidates
        if logfile is None:
            return None, searched, ""
        with open(logfile, encoding="utf-8", errors="replace") as f:
            content = f.read()
        vals = {}
        for key in ("TOTAL", "PASS", "SKIP", "XFAIL", "FAIL", "XPASS", "ERROR"):
            m = re.search(r"^#\s+%s:\s+(\d+)\s*$" % key, content, re.M)
            vals[key] = int(m.group(1)) if m else 0
        total = vals["TOTAL"]
        passed = vals["PASS"] + vals["XFAIL"]
        failed = vals["FAIL"] + vals["XPASS"] + vals["ERROR"]
        skipped = vals["SKIP"]
        executed = passed + failed
        ok = (
            total >= 0 and passed >= 0 and failed >= 0 and skipped >= 0
            and executed >= 0 and passed + failed == executed
            and executed + skipped <= total and executed <= total
        )
        result = {
            "logfile": logfile,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "executed": executed,
            "raw": vals,
            "consistent": ok,
        }
        return result, searched, content

    def _parse_serial_check_log(self, check_log):
        """Parse old automake serial-harness `make check` output.

        xdffileio 0.3 ships 2012-era generated Makefiles (pre parallel-tests
        harness): `make check` prints one `PASS: <name>` / `FAIL: <name>`
        line per TEST and never writes test-suite.log. The tee'd
        upstream-check.log is therefore the single deterministic source here
        (one regex, one pass, no substring counting, no arithmetic repair).
        """
        if not os.path.isfile(check_log):
            return None
        with open(check_log, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        prog = re.compile(r"^\s*(PASS|FAIL|XFAIL|XPASS|SKIP|ERROR):\s+(\S+)\s*$")
        passed_names, failed_names, skipped_names = [], [], []
        for line in lines:
            m = prog.match(line)
            if not m:
                continue
            kind, name = m.group(1), m.group(2)
            if kind in ("PASS", "XFAIL"):
                passed_names.append(name)
            elif kind in ("FAIL", "XPASS", "ERROR"):
                failed_names.append(name)
            else:
                skipped_names.append(name)
        total = len(passed_names) + len(failed_names) + len(skipped_names)
        passed = len(passed_names)
        failed = len(failed_names)
        skipped = len(skipped_names)
        executed = passed + failed
        ok = (
            total > 0 and passed + failed == executed
            and executed + skipped <= total and executed <= total
        )
        result = {
            "logfile": check_log,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "executed": executed,
            "raw": {
                "passed_names": passed_names,
                "failed_names": failed_names,
                "skipped_names": skipped_names,
            },
            "consistent": ok,
        }
        return result

    def _run_upstream_tests(self):
        """Run `make check` and emit the HMBS upstream marker.

        Falsifiability: reference fixtures must exist and be non-empty before
        running; an empty-fixture run would print PASS on empty-vs-empty
        comparisons, so abort early instead.
        """
        for ref in (
            "ref128-13-97-50-11-7-1.bdf",
            "ref128-13-97-50-11-7-1.edf",
            "ref128-13-97-50-11-7-1.gdf1",
            "ref128-13-97-50-11-7-1.gdf2",
        ):
            for base in (self.source_folder, self.build_folder):
                cand = os.path.join(base, "tests", ref)
                if os.path.isfile(cand):
                    size = os.path.getsize(cand)
                    self.output.info("upstream fixture %s size=%d" % (cand, size))
                    if size == 0:
                        raise ConanException(
                            "upstream fixture %s is empty; refusing empty-vs-empty run" % cand
                        )
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        cc, cxx, lbl = self._resolve_compiler()
        prefix = self._fixed_env_prefix(shell, tmpdir, cc, cxx)
        self.output.info(
            "xdffileio make check shell=%s tmpdir=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, lbl, cc, cxx)
        )
        check_failed = None
        check_log = os.path.join(self.build_folder, "upstream-check.log")
        # POSIX-sh portable tee: no pipes/PIPESTATUS (dash-incompatible), so
        # redirect to a deterministic file, replay it to stdout for the
        # preflight log, and preserve make's exit code.
        check_cmd = (
            prefix + 'make -j1 check >"%s" 2>&1; rc=$?; cat "%s"; exit $rc'
            % (check_log, check_log)
        )
        try:
            self.run(check_cmd, cwd=self.build_folder, env="conanbuild")
        except ConanException as e:
            check_failed = e
            self.output.warning("make check reported failures; parsing logs: %s" % e)
        parsed, searched, _content = self._parse_autotools_suite(self.build_folder)
        source_note = ""
        if parsed is None:
            # 2012-era serial harness: no test-suite.log exists by design.
            # Fall back to the teed check log as the single source.
            serial = self._parse_serial_check_log(check_log)
            if serial is not None and serial["consistent"]:
                parsed = serial
                source_note = " (serial harness)"
            else:
                detail = "no PASS/FAIL lines" if serial is not None else "check log missing"
                marker = {
                    "status": "failed",
                    "framework": "automake",
                    "command": "make check",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "test-suite.log not found; searched: %s; %s in %s" % (
                        "; ".join(searched), detail, check_log),
                }
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
                if check_failed is not None:
                    raise check_failed
                raise ConanException(marker["reason"])
        if source_note:
            self.output.info(
                "xdffileio upstream counts from%s %s: total=%d passed=%d failed=%d skipped=%d" % (
                    source_note, parsed["logfile"], parsed["total"],
                    parsed["passed"], parsed["failed"], parsed["skipped"]))
        if not parsed["consistent"]:
            marker = {
                "status": "failed",
                "framework": "automake",
                "command": "make check",
                "discovered": parsed["total"],
                "executed": parsed["executed"],
                "passed": parsed["passed"],
                "failed": parsed["failed"],
                "skipped": parsed["skipped"],
                "reason": "inconsistent counts from %s: %s" % (
                    parsed["logfile"], json.dumps(parsed["raw"])),
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise ConanException(marker["reason"])
        status = "passed" if parsed["failed"] == 0 else "failed"
        marker = {
            "status": status,
            "framework": "automake",
            "command": "make check",
            "discovered": parsed["total"],
            "executed": parsed["executed"],
            "passed": parsed["passed"],
            "failed": parsed["failed"],
            "skipped": parsed["skipped"],
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False)
        self.output.info("persisted upstream test result to %s" % result_path)
        if check_failed is not None:
            raise check_failed
        return marker

    def _fix_configure_umask(self):
        # Same [unsafe_local_mktemp] family: autoconf emits
        # "(umask 077 && mktemp -d ./confXXXXXX)" and its mkdir fallback
        # "(umask 077 && mkdir $tmp)". On this device FS the 077 dir
        # (0700 + setgid -> drwx--S---) is owner-unwritable for the
        # follow-up writes (integrit/inoticoming precedent). Relax to
        # 022 in the source configure so the generated config.status
        # inherits it. Operates on the conan-cache copy, not git.
        path = os.path.join(self.source_folder, "configure")
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        patched = content.replace("umask 077", "umask 022")
        try:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(patched)
            self.output.info("xdffileio: relaxed umask 077->022 in configure")
        except OSError as e:
            raise ConanException(
                "xdffileio: failed to patch umask in configure: %s" % e)

    def _mktemp_fallback_shim(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory
        # created by mktemp on the current device filesystem cannot be
        # written by Autoconf afterwards (config.status fails with
        # "can't create ./confXXXXXX/subs1.awk: Permission denied").
        # When HMBS injects HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow
        # mktemp during the configure step only so calls for "./conf*"
        # fail and Autoconf falls back to its `mkdir` path. All other
        # mktemp calls delegate to the real binary (cyrus-sasl precedent).
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /bin/mktemp /usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def build(self):
        apply_conandata_patches(self)
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        cc, cxx, lbl = self._resolve_compiler()
        prefix = self._fixed_env_prefix(shell, tmpdir, cc, cxx)
        self.output.info(
            "xdffileio build shell=%s tmpdir=%s compiler=%s CC=%s CXX=%s"
            % (shell, tmpdir, lbl, cc, cxx)
        )
        # build-aux refresh is idempotent; repeat here so cached-source
        # runs (generate skipped) also get the OHOS-aware scripts, then
        # prove config.sub/guess work before configure consumes them.
        self._stage_build_aux()
        self._fix_configure_umask()
        self._verify_build_aux(shell)
        cfg_args = " ".join(self._configure_args())
        self.output.info("xdffileio configure args: %s" % cfg_args)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            # Out-of-source (basic_layout): run src configure from build dir
            # explicitly through the usable shell to avoid shebang exec
            # and the stale profile CONFIG_SHELL.
            cfg_dir = self.build_folder
            configure_cmd = '"%s" "%s" %s' % (shell, configure_path, cfg_args)
        else:
            cfg_dir = self.build_folder
            configure_cmd = '"%s" ./configure %s' % (shell, cfg_args)
        try:
            # [unsafe_local_mktemp] minimal adaptation: shadow mktemp only
            # for the configure step when HMBS asks for the mkdir fallback.
            # The shim forces "./conf*" mktemp calls to fail so Autoconf
            # uses mkdir; make/check below run without it.
            mktemp_shim = self._mktemp_fallback_shim(tmpdir)
            self.output.info(
                "xdffileio mktemp fallback shim=%s fallback=%s"
                % (mktemp_shim or "<off>",
                   os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "<unset>"))
            )
            # NOTE (round 3): `PATH="dir:$PATH" export ...` only scopes
            # PATH to that single export builtin, so the previous round's
            # shim never reached configure (same conf*/subs1.awk failure).
            # Use `export PATH=...` so it persists for configure+config.status.
            path_prefix = (("export PATH=\"%s:$PATH\" && " % mktemp_shim)
                           if mktemp_shim else "")
            self.run("umask 022 && " + path_prefix + prefix + configure_cmd,
                     cwd=cfg_dir, env="conanbuild")
        except Exception:
            self._dump_config_log(cfg_dir)
            raise
        self.run(prefix + "make -j1", cwd=cfg_dir, env="conanbuild")
        self._run_upstream_tests()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = ["/data/service/hnp/bin/llvm-objcopy", shutil.which("llvm-objcopy") or ""]
        if cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('%s --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, so))
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, so, so))

    def package(self):
        # Same stale-CONFIG_SHELL reason as build(): run make install
        # explicitly with inline good-shell/TMPDIR exports instead of
        # Autotools.install() which inherits the profile's bad HNP bash
        # via env="conanbuild". DESTDIR install with --prefix=/ (bwm/0.6.3
        # precedent): without DESTDIR `make install` writes to /lib on
        # device and dies with "Read-only file system".
        #
        # Preflight evidence (2026-10-10): build + `make check` (6/6) pass,
        # but full `make install` dies in doc/install-man3:
        #   <runtime>/bin/install -c -m 644 <23 xdf_*.3> '<pkg>/share/man/man3'
        #   make[2]: *** [Makefile:530: install-man3] Error 64
        # The lib install (single-file `install -c` via libtool, earlier in
        # install-recursive) succeeded; only the multi-file man-page install
        # hits EX_USAGE(64) from the device install(1). Man pages are optional
        # Conan artifacts (consumers need lib + xdfio.h only), so install just
        # the exec part via make and handle headers/man with pure-Python
        # copies that never exec install(1) (idsgrep/0.6 precedent: targeted
        # install + copy optional products as-found, error when the primary
        # binary is missing).
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            'export SHELL="%s" && export CONFIG_SHELL="%s" && '
            'export TMPDIR="%s" && export TMP="%s" && export TEMP="%s" && '
        ) % (shell, shell, tmpdir, tmpdir, tmpdir)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        cfg_dir = self.build_folder
        if not os.path.isfile(os.path.join(cfg_dir, "Makefile")) and os.path.isfile(
            os.path.join(self.source_folder, "Makefile")
        ):
            cfg_dir = self.source_folder
        # Libs (+ bins, none here) only: doc/install-man3 is not traversed.
        self.run(fix + f'make install-exec DESTDIR="{self.package_folder}"', cwd=cfg_dir, env="conanbuild")
        # --- headers (required): upstream public header is xdfio.h; copy any
        # xdf*.h found at the top of source/build trees (never gnulib libgnu
        # internals) into <package>/include with plain Python I/O.
        inc_dst = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dst, exist_ok=True)
        header_bases = [
            self.source_folder,
            os.path.join(self.source_folder, "src"),
            os.path.join(self.source_folder, "include"),
            cfg_dir,
            os.path.join(cfg_dir, "src"),
        ]
        found_headers = []
        for base in header_bases:
            for hdr in glob.glob(os.path.join(base, "xdf*.h")):
                try:
                    shutil.copy2(hdr, os.path.join(inc_dst, os.path.basename(hdr)))
                    found_headers.append(hdr)
                except OSError as e:
                    raise ConanException(
                        "xdffileio: failed to stage header %s: %s" % (hdr, e)
                    )
        if not found_headers:
            raise ConanException(
                "xdffileio: public header xdfio.h not found under %s or %s; "
                "refusing to pack a header-less library" % (self.source_folder, cfg_dir)
            )
        self.output.info(
            "xdffileio: staged %d public header(s) into %s: %s"
            % (len(found_headers), inc_dst,
               ", ".join(sorted(os.path.basename(h) for h in found_headers)))
        )
        # --- man pages (optional): keep package contents equivalent to a full
        # install when the sources exist; missing pages stay missing.
        man_dst = os.path.join(self.package_folder, "share", "man", "man3")
        man_pages = []
        for base in (os.path.join(self.source_folder, "doc"),
                     os.path.join(cfg_dir, "doc")):
            man_pages.extend(glob.glob(os.path.join(base, "*.3")))
        if man_pages:
            os.makedirs(man_dst, exist_ok=True)
            for page in sorted(set(man_pages)):
                try:
                    shutil.copy2(page, os.path.join(man_dst, os.path.basename(page)))
                except OSError as e:
                    raise ConanException(
                        "xdffileio: failed to stage man page %s: %s" % (page, e)
                    )
            self.output.info(
                "xdffileio: staged %d man page(s) into %s"
                % (len(set(man_pages)), man_dst)
            )
        else:
            self.output.info("xdffileio: no doc/*.3 man pages found; shipping without man")
        # --- primary artifact guard: the static/shared library must exist.
        lib_cands = glob.glob(os.path.join(self.package_folder, "lib", "libxdffileio.*"))
        lib_cands = [p for p in lib_cands if not p.endswith(".la")]
        if not lib_cands:
            raise ConanException(
                "xdffileio: no libxdffileio.* staged under %s after install-exec; "
                "refusing to pack an empty library" % os.path.join(self.package_folder, "lib")
            )
        self.output.info(
            "xdffileio: staged library artifact(s): %s"
            % ", ".join(sorted(os.path.basename(p) for p in lib_cands))
        )
        for pattern in ("*.la", "*.dylib"):
            # remove libtool archives / macOS stubs if installed
            # (no conan copy() here: src==dst self-copy raises
            # "copy() 'src' and 'dst' arguments must have different values").
            for f in glob.glob(os.path.join(self.package_folder, "lib", pattern)):
                try:
                    os.remove(f)
                except OSError:
                    pass
        res_dir = os.path.join(self.package_folder, "res")
        os.makedirs(res_dir, exist_ok=True)
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            shutil.copy(result_path, os.path.join(res_dir, "upstream_test_result.json"))
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["xdffileio"]
        self.cpp_info.set_property("cmake_file_name", "xdffileio")
        self.cpp_info.set_property("cmake_target_name", "xdffileio::xdffileio")
        self.cpp_info.set_property("pkg_config_name", "xdffileio")
        # xdffileio 0.3 links only libc/math/pthread; no mmlib requirement.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
