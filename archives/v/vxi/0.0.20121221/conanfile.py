#!/usr/bin/env python3
"""Conan recipe — vxi 0.0.20121221 (VXI-11 RPC protocol, autotools).

VXI-11 is the TCP/IP instrument control protocol used by LXI test and
measurement equipment. The Debian vxi source package ships two RPC
specification files (vxi.x, vxi_intr.x) plus autotools inputs; the build
generates C stubs with rpcgen and archives two static libraries:

  libvxiclient.a  (DEVICE_CORE/DEVICE_ASYNC client stubs + XDR codecs)
  libvxiserver.a  (interrupt server stubs + XDR codecs)

Headers installed: vxi.h, vxi_intr.h (both rpcgen-generated).

OHOS adaptations:
  - Requires libtirpc/1.3.7 for <rpc/rpc.h> XDR runtime (Debian
    Build-Depends libtirpc-dev equivalent); CPPFLAGS carry the conan
    tirpc include dir (Debian rules pass -I/usr/include/tirpc).
  - Upstream Makefile invokes rpcgen at build time (Debian Build-Depends
    rpcsvc-proto equivalent). The recipe prefers a system rpcgen but falls
    back to a private native build from the rpcsvc-proto sources in
    conandata.yml (build-time-only tool, never packaged); OHOS workers
    provide no system rpcgen, so the fallback is the normal path there.
    No vendored pre-generated files: the .x inputs stay the canonical
    source, matching Debian's from-source build.
  - E011 HMDFS trap: configure's "umask 077" is rewritten to "umask 000"
    before running (libtirpc/gadap precedent).
  - R26: static-only libraries (--enable-static/--disable-shared).
  - Upstream has no test suite (audited: 14-file tarball, no tests/ dir,
    no TESTS in Makefile.am; see test_package/MANIFEST.yml
    upstream_test_audit). build() does not run make check
    (upstream_test_in_build: false); HMBS_UPSTREAM_TEST_RESULT
    status=no_tests is emitted by test_package every run.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VxiConan(ConanFile):
    name = "vxi"
    version = "0.0.20121221"
    description = "VXI-11 RPC protocol client/server static libraries for LXI instruments"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/vxi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("vxi", "vxi-11", "lxi", "rpc", "instrument")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def _gnu_build_triplet(self):
        # Explicit GNU triplet for the native OHOS build (serf/1.3.10,
        # adms/2.3.7, zzuf/0.15 precedent): the shipped vintage
        # config.guess scripts (vxi 2012, rpcsvc-proto 2017-05-27) predate
        # HarmonyOS (uname -s = "HarmonyOS") and abort with "unable to guess
        # system type / cannot guess build type". Passing --build/--host
        # with build == host skips the guess entirely. Use the plain
        # *-unknown-linux-gnu form (NOT *-linux-ohos): these old config.sub
        # files do not know the ohos vendor/kernel and would reject it,
        # while aarch64-unknown-linux-gnu is accepted everywhere.
        # arch=armv8 is conan's enum for AArch64 (see
        # ci/conan/profiles/ohos-aarch64).
        arch = str(self.settings.arch)
        if arch in ("armv8", "aarch64", "armv8.0", "armv8_32"):
            return "aarch64-unknown-linux-gnu"
        if arch in ("x86_64", "amd64"):
            return "x86_64-pc-linux-gnu"
        if arch.startswith("armv7"):
            return "armv7-unknown-linux-gnueabihf"
        return "aarch64-unknown-linux-gnu"

    def _run_fork_tolerant(self, cmd, **kwargs):
        # CI #91983 (worker CI-010): conanautotoolstoolchain.sh[13] failed
        # with "can't fork - try again" on two consecutive self.run() calls
        # (cpp-shim compile, rpcgen-priv configure) while the vxi + rpcgen
        # downloads had already succeeded. The same worker also failed KC3
        # with "fork: retry: Resource temporarily unavailable" before this
        # package even started, i.e. transient PID/memory pressure from the
        # worker (20 parallel download threads + shared host), not a recipe
        # bug. Previous round changed nothing and the fingerprint repeated,
        # so this round retries transient fork failures with backoff instead
        # of failing the whole build on the first EAGAIN. Permanent errors
        # (real compile/configure failures) still raise after retries.
        import time as _time
        attempts = 4
        delays = (5, 15, 30)
        last_exc = None
        for i in range(attempts):
            try:
                return self.run(cmd, **kwargs)
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                # ConanException from self.run is generic ("Error 1"); the
                # fork signature lives in the worker log, not the exception.
                # For these build-host tool steps any early Error 1 is worth
                # one backoff cycle, but never mask the final failure.
                self.output.warning(
                    f"vxi: run attempt {i + 1}/{attempts} failed: {msg}; "
                    f"backing off (fork/resource tolerance, CI #91983)")
                if i == attempts - 1:
                    break
                try:
                    _time.sleep(delays[min(i, len(delays) - 1)])
                except Exception:
                    pass
        raise last_exc

    def _ohos_clean_shell(self):
        # [shell_getcwd] HNP bash (/data/service/hnp/bin/bash, via profile
        # SHELL/CONFIG_SHELL) fails getcwd() on the deep conan build path on
        # HMFS/HMDFS, aborting configure with "working directory cannot be
        # determined" (cvechecker/4, aldo/0.7.8, zephyr/3.1.2 precedent).
        # Prefer the HMBS-injected SHELL when it is not the HNP bash,
        # otherwise fall back to the getcwd-clean vendor shells.
        for cand in (os.environ.get("SHELL", ""), "/bin/sh",
                     "/system/bin/sh"):
            if cand and os.path.isfile(cand.split()[0]) and "hnp" not in cand:
                return cand.split()[0]
        return "/bin/sh"

    def _patch_configure_hmdfs(self, conf_path):
        # Make a generated configure survive the HMFS getcwd bug: fall back
        # to $PWD when `pwd` cannot resolve getcwd() (aldo/0.7.8 pattern),
        # relax umask 077 (E011 HMDFS trap), and redirect autoconf temp dirs
        # to $TMPDIR (HMBS injects a writable task TMPDIR; /tmp may be
        # read-only). Idempotent; warns when no literal matches.
        if not os.path.isfile(conf_path):
            self.output.warning(
                f"vxi: configure not found at {conf_path}, skipping HMDFS patch")
            return
        with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
        orig = data
        if "ac_pwd=" in data:
            data = data.replace(
                "ac_pwd=`pwd`", 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
            data = data.replace(
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"'
                ' 2>/dev/null || ac_pwd="$PWD"',
                'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
        if "umask 077" in data:
            data = data.replace("umask 077", "umask 000")
        if 'mktemp -d "./confXXXXXX"' in data:
            data = data.replace(
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"')
        # NOTE: autoconf uses PID marker (dollar-dollar) in tmp names; built
        # via chr(36) to avoid patch-channel collapsing it.
        _dd = chr(36) + chr(36)
        _old_tmp = "tmp=./conf" + _dd + "-$RANDOM"
        _new_tmp = "tmp=${TMPDIR:-.}/conf" + _dd + "-$RANDOM"
        if _old_tmp in data:
            data = data.replace(_old_tmp, _new_tmp)
        if data != orig:
            with open(conf_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(data)
            self.output.info(
                f"vxi: patched HMDFS getcwd/umask/tmpdir in {conf_path}")
        else:
            self.output.warning(
                f"vxi: HMDFS patch found no literals in {conf_path}")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"vxi is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Debian Build-Depends: libtirpc-dev (XDR runtime + rpc headers).
        self.requires("libtirpc/1.3.7", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        # retry/retry_wait: transient gateway/proxy failures must not fail
        # the whole build on the first timeout (true preflight 2026-10-14:
        # github.com connect timeout after 2 retries inside conan).
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=3, retry_wait=10)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Old config.guess (vxi 2012, rpcsvc-proto 2017) cannot identify
        # HarmonyOS, so strip any auto triplets and pass an explicit native
        # triplet (build == host) to skip the guess entirely (serf/1.3.10
        # experience #1; adms/zzuf precedent). Keep the TMPDIR/shell
        # hardening below.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        if str(self.settings.os) == "OHOS":
            _triplet = self._gnu_build_triplet()
            tc.configure_args.append(f"--build={_triplet}")
            tc.configure_args.append(f"--host={_triplet}")
        # R26: upstream only produces static archives (lib_LIBRARIES).
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # R33: explicit compiler from Conan conf (CI clean env needs it).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if compilers.get("c"):
            tc.configure_args.append(f"CC={compilers['c']}")
        # Debian rules: -fPIC + tirpc include dir.
        tirpc = self.dependencies["libtirpc"]
        tirpc_incs = []
        for inc in tirpc.cpp_info.includedirs:
            p = inc if os.path.isabs(inc) else os.path.join(tirpc.package_folder, inc)
            tirpc_incs.append(p)
        flags = ["-fPIC", "-O2" if self.settings.build_type == "Release" else "-O0"]
        flags += [f"-I{p}" for p in tirpc_incs]
        tc.extra_cflags.extend(flags)
        # [shell_getcwd] force the getcwd-clean vendor shell for
        # configure/config.status (cvechecker/4 precedent) and keep autoconf
        # temp files in the HMBS writable TMPDIR (E002).
        env = tc.environment()
        clean_sh = self._ohos_clean_shell()
        env.define("SHELL", clean_sh)
        env.define("CONFIG_SHELL", clean_sh)
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        tc.generate(env=env)

    def _ensure_rpcgen(self):
        # Debian Build-Depends rpcsvc-proto equivalent. OHOS workers have no
        # system rpcgen, so fall back to a private native build from the
        # rpcsvc-proto sources declared in conandata.yml (same upstream that
        # Debian uses). The binary is a build-time-only tool: it runs on the
        # build host to turn vxi.x/vxi_intr.x into C stubs, hence an explicit
        # native triplet (build == host, see _gnu_build_triplet) and no
        # package/install.
        priv_bin = os.path.join(
            self.build_folder, "rpcgen-priv", "src", "rpcgen", "rpcgen")
        if os.path.isfile(priv_bin):
            os.environ["PATH"] = (
                os.path.dirname(priv_bin) + os.pathsep
                + os.environ.get("PATH", ""))
            self.output.info(f"vxi: reusing private rpcgen: {priv_bin}")
            _reuse_cpp = os.path.join(
                self.build_folder, "rpcgen-priv", "bin", "cpp")
            self._vxi_cpp_dir = os.path.dirname(_reuse_cpp) \
                if os.path.isfile(_reuse_cpp) else None
            return priv_bin
        rpcgen = shutil.which("rpcgen")
        if rpcgen:
            self.output.info(f"vxi: using system rpcgen: {rpcgen}")
            self._vxi_cpp_dir = None
            return rpcgen
        self.output.info(
            "vxi: system rpcgen NOT FOUND, building private rpcgen "
            "from rpcsvc-proto sources")
        priv = os.path.join(self.build_folder, "rpcgen-priv")
        src_dir = os.path.join(priv, "src")
        os.makedirs(priv, exist_ok=True)
        get(self, **self.conan_data["rpcgen_sources"],
            destination=src_dir, strip_root=True, retry=3, retry_wait=10)
        # OHOS libc (musl-based) provides index/strchr but NOT the legacy
        # BSD rindex() used by rpcsvc-proto rpcgen (rpc_main.c mkfile_output).
        # True error: `ld.lld: error: undefined symbol: rindex`. Map the
        # whole-word rindex -> strrchr in the private-tool sources only
        # (build-host tool, never packaged). strrchr is declared in
        # <string.h> which these files already include.
        _patched = 0
        for _root, _, _files in os.walk(src_dir):
            for _fn in _files:
                if not _fn.endswith((".c", ".h", ".y", ".l")):
                    continue
                _p = os.path.join(_root, _fn)
                try:
                    with open(_p, "r", encoding="utf-8", errors="replace") as f:
                        _c = f.read()
                except Exception:
                    continue
                _nc, _n = re.subn(r"\brindex\b", "strrchr", _c)
                if _n:
                    with open(_p, "w", encoding="utf-8", newline="\n") as f:
                        f.write(_nc)
                    _patched += _n
        self.output.info(f"vxi: rindex->strrchr compat patch: {_patched} occurrence(s)")
        # E011: same HMDFS umask trap as the main package.
        for fname in ("configure", "config.status"):
            path = os.path.join(src_dir, fname)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 000")
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                    self.output.info(
                        f"vxi: fixed umask 077 -> 000 in rpcsvc-proto/{fname}")
        # [shell_getcwd] the rpcsvc-proto configure runs in the same deep
        # HMFS path, so it needs the same ac_pwd/$PWD fallback + TMPDIR
        # redirect as the main package (aldo/0.7.8 pattern).
        self._patch_configure_hmdfs(os.path.join(src_dir, "configure"))
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "clang"
        # Native build tool: plain configure with an explicit native triplet
        # (build == host) so the vintage config.guess never runs (see
        # _gnu_build_triplet). Run under the getcwd-clean shell
        # (zephyr/dosfstools precedent) with logical $PWD so `pwd` failures
        # fall back instead of aborting (aldo precedent).
        clean_sh = self._ohos_clean_shell()
        _triplet = self._gnu_build_triplet()
        # rpcgen shells out to `cpp` to preprocess .x inputs (true CI
        # error 2026-10-14, rpcgen-priv/src/rpcsvc:
        # `../rpcgen/rpcgen -h -o klm_prot.h klm_prot.x` ->
        # `cannot find C preprocessor: cpp`). OHOS workers provide
        # clang but no `cpp` binary, so stage a build-host `cpp -> $CC -E`
        # wrapper on PATH (+ $CPP) before configure/make. The wrapper
        # stays on PATH for the later vxi.x pre-grow rpcgen calls.
        # LANGUAGE TRAP (true preflight 2026-10-14, empty 241-char vxi.h):
        # a bare `CC -E` driver call does NOT preprocess a `.x` file: the
        # driver treats the unknown `.x` suffix as linker input, skips
        # preprocessing entirely, and still exits 0 (local proof with
        # MinGW gcc on the real vxi.x: `gcc -E -C -DRPC_HDR vxi.x` ->
        # rc=0, 139 bytes, no `program` line, warning "linker input file
        # unused because linking not done"; `cpp` on the same file ->
        # 4576 bytes with `program DEVICE_CORE`). rpcgen then parses zero
        # definitions and emits a boilerplate-only 241-char header with
        # exit 0, so nothing ever fails loudly. The shim therefore forces
        # the language with `-x c` (`CC -E -x c ...`), which restores the
        # full 4576-byte preprocessed output. Verified locally:
        # `gcc -E -x c -C -DRPC_HDR vxi.x` -> 4576 bytes, has program.
        # NOTE (chmod): the earlier shell-script shim needed `chmod +x`,
        # but HMBS reports chmod:0 on HMDFS so the shim stayed
        # non-executable. Build a tiny compiled C wrapper instead:
        # compiler output is executable without chmod.
        try:
            _shim_dir = os.path.join(priv, "bin")
            os.makedirs(_shim_dir, exist_ok=True)
            _cpp_shim = os.path.join(_shim_dir, "cpp")
            _cc_esc = cc.replace("\\", "\\\\").replace('"', '\\"')
            _cpp_c = os.path.join(_shim_dir, "cpp_shim.c")
            with open(_cpp_c, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(
                    '#include <unistd.h>\n'
                    'int main(int argc, char *argv[]) {\n'
                    '  static char *nargv[4096];\n'
                    '  if (argc + 5 >= 4096) return 127;\n'
                    f'  nargv[0] = "{_cc_esc}";\n'
                    '  nargv[1] = "-E";\n'
                    '  nargv[2] = "-x";\n'
                    '  nargv[3] = "c";\n'
                    '  for (int i = 1; i < argc; i++) nargv[i + 3] = argv[i];\n'
                    '  nargv[argc + 3] = (char *)0;\n'
                    f'  execvp("{_cc_esc}", nargv);\n'
                    '  return 127;\n'
                    '}\n')
            self._run_fork_tolerant(f'"{cc}" -O2 -o "{_cpp_shim}" "{_cpp_c}"')
            os.environ["PATH"] = (
                _shim_dir + os.pathsep + os.environ.get("PATH", ""))
            os.environ["CPP"] = _cpp_shim
            self.output.info(f"vxi: cpp wrapper ready: {_cpp_shim} -> {cc} -E")
            self.run(f'"{_cpp_shim}" --version 2>&1 | head -3',
                     ignore_errors=True)
            self._vxi_cpp_dir = _shim_dir
        except Exception as _exc:
            self.output.warning(f"vxi: cpp wrapper setup skipped: {_exc}")
            self._vxi_cpp_dir = None
        prev_pwd = os.environ.get("PWD")
        os.environ["PWD"] = src_dir
        os.environ["SHELL"] = clean_sh
        os.environ["CONFIG_SHELL"] = clean_sh
        try:
            self._run_fork_tolerant(f'env -u CONFIG_SHELL SHELL="{clean_sh}" '
                     f'"{clean_sh}" ./configure --build={_triplet} '
                     f'--host={_triplet} CC="{cc}"', cwd=src_dir)
        finally:
            if prev_pwd is None:
                os.environ.pop("PWD", None)
            else:
                os.environ["PWD"] = prev_pwd
        try:
            make_path = self.conf.get("user.hmbs:make_path", check_type=str)
        except Exception:
            make_path = None
        make_cmd = f'"{make_path}"' if make_path else "make"
        os.environ["PWD"] = src_dir
        try:
            # Only the rpcgen binary is needed (build-host tool); skip
            # the rpcsvc libs whose header generation is what required
            # `cpp` in the CI log. With the shim above even a full make
            # would pass, but building just rpcgen avoids extra
            # cross-compile failure modes in unused libs.
            self._run_fork_tolerant(f'env -u CONFIG_SHELL SHELL="{clean_sh}" '
                     f"{make_cmd} -j1 -C rpcgen", cwd=src_dir)
        finally:
            try:
                os.chdir(self.build_folder)
            except Exception:
                pass
            os.environ["PWD"] = self.build_folder
        cand = priv_bin
        if not os.path.isfile(cand):
            found = None
            for root, _, files in os.walk(src_dir):
                if "rpcgen" in files:
                    p = os.path.join(root, "rpcgen")
                    if os.path.isfile(p) and not p.endswith(".c"):
                        found = p
                        break
            if found:
                cand = found
        if not os.path.isfile(cand):
            raise ConanInvalidConfiguration(
                "vxi: private rpcgen build did not produce rpcgen binary "
                "(Debian Build-Depends rpcsvc-proto equivalent)")
        bindir = os.path.dirname(cand)
        os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")
        self.output.info(f"vxi: private rpcgen ready: {cand}")
        return cand

    def _pregrow_rpcgen_stubs(self, rpcgen):
        # VPATH/rpcgen pre-grow (replaces the failed Makefile-inline-sed
        # attempt of 2026-10-14, which was a no-op: the sed-append lines
        # were nested under an unconditional `continue` so `changed` never
        # became True and no Makefile was ever patched, hence the identical
        # `fatal error: '.../b/vxi.h' file not found` reappeared at
        # build()/line 528). Strategy change: do NOT parse/patch Makefiles
        # at all. Instead, run rpcgen OURSELVES with a bare basename input
        # so the embedded #include is already `"vxi.h"` (no directory),
        # write the 8 stubs into every configured output dir BEFORE make,
        # and touch them newer than srcdir/*.x so the pattern rules
        # (`%.h: %.x` / `%_xdr.c` / `%_clnt.c` / `%_svr.c`, all
        # `rpcgen -h/-c/-l/-m -o $@ $<`) consider them up-to-date and skip
        # regeneration. A python regex sweep normalizes any residual
        # absolute include right after generation (no sed/chmod needed).
        import shutil as _shutil
        import subprocess as _sp
        import time as _time
        xnames = ("vxi", "vxi_intr")
        # (suffix, rpcgen flag): mirrors Makefile.am pattern rules.
        variants = ((".h", "-h"), ("_xdr.c", "-c"),
                    ("_clnt.c", "-l"), ("_svr.c", "-m"))
        # Configured output dirs = every dir under build_folder holding a
        # generated Makefile; fall back to build_folder itself.
        out_dirs = []
        broot = getattr(self, "build_folder", None)
        if broot and os.path.isdir(broot):
            for dirpath, _, files in os.walk(broot):
                # The private rpcgen tool tree lives under build_folder
                # (rpcgen-priv/src/... has its own Makefiles). Never stage
                # vxi.x or run rpcgen there: it pollutes the build-host tool
                # sources and can shadow real headers in later harvests.
                if "rpcgen-priv" in dirpath:
                    continue
                if "Makefile" in files:
                    out_dirs.append(dirpath)
        if not out_dirs and broot:
            out_dirs = [broot]
        if not out_dirs:
            self.output.warning("vxi: no build output dir for pre-grow")
            return
        # rpcgen picks its preprocessor as stat("/lib/cpp") else a PATH
        # lookup of "cpp", overridable with `-Y dir` (rpcsvc-proto 1.4.4
        # rpcgen/rpc_main.c find_cpp: CPP="/lib/cpp", fallback "cpp").
        # True preflight 2026-10-14 produced a 241-char boilerplate-only
        # vxi.h with exit 0 across TWO PATH-shim generations (shell shim,
        # then compiled shim): PATH ordering under the conanbuild env can
        # resolve "cpp" to a non-functional binary ahead of our shim, and
        # an exit-0 empty output means the parser saw zero definitions.
        # Strategy change: pass `-Y <shim_dir>` explicitly so cpp selection
        # is deterministic (with cppDefined=1 a missing shim file fails
        # loudly instead of silently falling back), and smoke-test the
        # preprocessor on each staged .x so the next log shows real byte
        # counts instead of another silent empty file.
        cpp_dir = getattr(self, "_vxi_cpp_dir", None)
        y_args = []
        if cpp_dir and os.path.isfile(os.path.join(cpp_dir, "cpp")):
            y_args = ["-Y", cpp_dir]
            self.output.info(f"vxi: rpcgen -Y {cpp_dir} (deterministic cpp)")
        else:
            self.output.warning(
                "vxi: no deterministic cpp dir; rpcgen falls back to "
                "PATH lookup for cpp")
        try:
            _which_cpp = _shutil.which("cpp")
        except Exception:
            _which_cpp = None
        self.output.info(f"vxi: PATH cpp resolution: {_which_cpp}")
        for out_dir in dict.fromkeys(out_dirs):
            for xname in xnames:
                src_x = os.path.join(str(self.source_folder), xname + ".x")
                if not os.path.isfile(src_x):
                    continue
                # Stage a basename input in the output dir so rpcgen embeds
                # no directory component into #include lines.
                staged = os.path.join(out_dir, xname + ".x")
                try:
                    if (not os.path.isfile(staged) or
                            os.path.getmtime(staged) < os.path.getmtime(src_x)):
                        _shutil.copyfile(src_x, staged)
                except Exception as exc:
                    self.output.warning(
                        f"vxi: stage {xname}.x -> {out_dir} skipped: {exc}")
                    continue
                try:
                    _staged_sz = os.path.getsize(staged)
                except Exception:
                    _staged_sz = -1
                self.output.info(f"vxi: staged {xname}.x: {_staged_sz} B")
                # Smoke-test the exact preprocessor rpcgen will use, with
                # the same -C/-DRPC_HDR flags rpcgen passes (see
                # open_input: putarg CPP/CPPFLAGS/"-C"/define). A healthy
                # run must emit kilobytes containing "program".
                if y_args:
                    try:
                        _smoke = _sp.run(
                            [os.path.join(cpp_dir, "cpp"), "-C",
                             "-DRPC_HDR", staged],
                            cwd=out_dir, stdout=_sp.PIPE,
                            stderr=_sp.STDOUT, timeout=60)
                        _sout = _smoke.stdout or b""
                        _txt = _sout.decode("utf-8", "replace")
                        self.output.info(
                            f"vxi: cpp smoke {xname}.x: rc={_smoke.returncode} "
                            f"{len(_sout)} bytes, "
                            f"has_program={'program' in _txt}")
                    except Exception as exc:
                        self.output.warning(
                            f"vxi: cpp smoke {xname}.x skipped: {exc}")
                for suffix, flag in variants:
                    out_file = os.path.join(out_dir, xname + suffix)
                    # vxi_clnt.c / vxi_svr.c are generated for vxi.x but not
                    # linked into either archive (see Makefile.am); still
                    # pre-grow them so no rule ever fires.
                    # rpcgen refuses to overwrite an existing outfile
                    # ("already exists and may be overwritten" -> crash),
                    # so drop any stale file from a previous create reusing
                    # this build folder BEFORE invoking rpcgen.
                    try:
                        if os.path.isfile(out_file):
                            os.remove(out_file)
                    except Exception:
                        pass
                    cmd = [rpcgen] + y_args + [
                        flag, "-o", xname + suffix, xname + ".x"]
                    try:
                        _res = _sp.run(cmd, cwd=out_dir, check=True,
                                       stdout=_sp.PIPE, stderr=_sp.STDOUT,
                                       timeout=120)
                        _out = _res.stdout.decode(
                            "utf-8", "replace") if isinstance(
                            _res.stdout, bytes) else str(_res.stdout or "")
                        if _out.strip():
                            self.output.info(
                                f"vxi: rpcgen {xname + suffix} says: "
                                f"{_out[:400]}")
                        self.output.info(
                            f"vxi: pre-grew {xname + suffix} in {out_dir}")
                    except Exception as exc:
                        self.output.warning(
                            f"vxi: pre-grow {xname + suffix} failed: {exc}")
                        try:
                            if os.path.isfile(out_file):
                                os.remove(out_file)
                        except Exception:
                            pass
                        continue
                    # Verify generated headers actually expose the API;
                    # a silent rpcgen failure (e.g. missing cpp) leaves a
                    # boilerplate-only file that compiles to an empty
                    # archive. Never touch such files: let make retry and
                    # fail loudly with the real error instead of packaging
                    # empty headers (true preflight 2026-10-14: packaged
                    # vxi.h lacked DEVICE_CORE/Create_LinkParms).
                    if suffix == ".h":
                        try:
                            with open(out_file, "r", encoding="utf-8",
                                      errors="replace") as _f:
                                _hd = _f.read()
                            _need = ("DEVICE_CORE", "Create_LinkParms") \
                                if xname == "vxi" else ("DEVICE_INTR",)
                            _absent = [s for s in _need if s not in _hd]
                            self.output.info(
                                f"vxi: verify {xname + suffix}: "
                                f"{len(_hd)} chars, absent={_absent}")
                            if _absent:
                                self.output.warning(
                                    f"vxi: pre-grow {xname + suffix} "
                                    f"content BAD, head: {_hd[:300]!r}; "
                                    f"removing so make retries")
                                try:
                                    os.remove(out_file)
                                except Exception:
                                    pass
                                continue
                        except Exception as exc:
                            self.output.warning(
                                f"vxi: verify {xname + suffix} skipped: "
                                f"{exc}")
                    # Normalize any absolute include immediately (same
                    # regex as the post-make sweep; rpcgen versions differ).
                    try:
                        with open(out_file, "r", encoding="utf-8",
                                   errors="replace") as f:
                            data = f.read()
                        new, n = re.subn(
                            r'#\s*include\s*"/[^"\n]*/([^"/\n]+\.h)"',
                            r'#include "\1"', data)
                        if n:
                            with open(out_file, "w", encoding="utf-8",
                                       newline="\n") as f:
                                f.write(new)
                            self.output.info(
                                f"vxi: normalized {n} include(s) in {out_file}")
                    except Exception as exc:
                        self.output.warning(
                            f"vxi: normalize {out_file} skipped: {exc}")
                # Touch all 8 stubs + staged .x newer than srcdir .x so
                # VPATH pattern rules skip regeneration during make.
                try:
                    now = _time.time()
                    targets = [os.path.join(out_dir, xname + s)
                               for s, _ in variants for xname in xnames]
                    targets.append(staged)
                    for tf in targets:
                        if os.path.isfile(tf):
                            os.utime(tf, (now, now + 1))
                except Exception:
                    pass

    def _fix_rpcgen_absolute_includes(self):
        # VPATH/rpcgen trap (true preflight error 2026-10-14): this vintage
        # Makefile.am runs `rpcgen -o $@ $<` where $< is srcdir-qualified
        # (e.g. /abs/src/vxi.x) in an out-of-source (VPATH) build. Modern
        # rpcsvc-proto rpcgen embeds the input directory into the generated
        # C stub as `#include "/abs/src/vxi.h"`, while `-o` writes vxi.h
        # into the build dir. The compile then dies with
        # `fatal error: '.../b/vxi.h' file not found` even though
        # build-release/vxi.h exists. Normalizing the absolute include to
        # the basename lets `-I.` (DEFAULT_INCLUDES) resolve the build-dir
        # header. Idempotent; scans build + source trees for rpcgen outputs.
        fixed = 0
        roots = []
        for cand in (getattr(self, "build_folder", None),
                     getattr(self, "source_folder", None)):
            if cand and os.path.isdir(cand) and cand not in roots:
                roots.append(cand)
        for root in roots:
            for dirpath, _, files in os.walk(root):
                if "rpcgen-priv" in dirpath:
                    continue
                # Only rpcgen outputs of this package.
                for fn in files:
                    if fn not in ("vxi.h", "vxi_intr.h", "vxi_clnt.c",
                                  "vxi_svr.c", "vxi_xdr.c", "vxi_intr_clnt.c",
                                  "vxi_intr_svr.c", "vxi_intr_xdr.c"):
                        continue
                    fp = os.path.join(dirpath, fn)
                    try:
                        with open(fp, "r", encoding="utf-8",
                                   errors="replace") as f:
                            data = f.read()
                    except Exception:
                        continue
                    new, n = re.subn(
                        r'#\s*include\s*"/[^"\n]*/([^"/\n]+\.h)"',
                        r'#include "\1"', data)
                    new2, n2 = re.subn(
                        r"#\s*include\s*'/[^'\n]*/([^'/\n]+\.h)'",
                        r"#include '\1'", new)
                    if (n + n2) > 0:
                        with open(fp, "w", encoding="utf-8",
                                   newline="\n") as f:
                            f.write(new2)
                        fixed += (n + n2)
                        self.output.info(
                            f"vxi: normalized {n + n2} absolute include(s)"
                            f" in {fp}")
        # Belt-and-braces: ensure the headers also exist at the legacy
        # absolute location's directory (source tree) so even an
        # un-normalized stub still compiles. Never overwrites newer files.
        try:
            for hdr in ("vxi.h", "vxi_intr.h"):
                dst = os.path.join(str(self.source_folder), hdr)
                if os.path.isfile(dst):
                    continue
                found = None
                for root, _, files in os.walk(str(self.build_folder)):
                    if "rpcgen-priv" in root:
                        continue
                    if hdr in files:
                        found = os.path.join(root, hdr)
                        break
                if found:
                    shutil.copyfile(found, dst)
                    self.output.info(
                        f"vxi: mirrored {hdr} build->source for legacy"
                        f" absolute include: {found} -> {dst}")
        except Exception as exc:
            self.output.warning(f"vxi: header mirror skipped: {exc}")
        if fixed == 0:
            self.output.info("vxi: no absolute rpcgen includes found")

    def build(self):
        # [shell_getcwd] logical PWD so bash pwd falls back instead of
        # failing getcwd() on HMFS (aldo/libuio precedent).
        try:
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        clean_sh = self._ohos_clean_shell()
        os.environ["SHELL"] = clean_sh
        # cxref precedent: a stale CONFIG_SHELL pointing at the HNP bash
        # re-execs configure under the getcwd-broken shell; drop it so the
        # conanbuild SHELL (clean vendor sh, see generate()) wins.
        os.environ.pop("CONFIG_SHELL", None)
        apply_conandata_patches(self)
        # E011: config.status/configure use "umask 077" which yields an
        # unwritable temp dir on HMDFS. Rewrite before running.
        for fname in ("configure", "config.status"):
            path = os.path.join(self.source_folder, fname)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 000")
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                    self.output.info(f"vxi: fixed umask 077 -> 000 in {fname}")
        # [shell_getcwd] ac_pwd fallback + TMPDIR redirect for the main
        # configure (same helper as the private rpcgen configure above).
        self._patch_configure_hmdfs(
            os.path.join(self.source_folder, "configure"))
        os.environ["PWD"] = self.build_folder
        # rpcgen is a hard build requirement (Debian Build-Depends
        # rpcsvc-proto). Prefer the worker system binary; otherwise build a
        # private native rpcgen so `make` finds `rpcgen` on PATH.
        rpcgen = self._ensure_rpcgen()
        self.output.info(f"vxi: rpcgen probe: {rpcgen}")
        self.run(f"{rpcgen} --version 2>&1 || {rpcgen} -h 2>&1 | head -3", ignore_errors=True)
        autotools = Autotools(self)
        autotools.configure()
        # Pre-grow rpcgen stubs with basename inputs BEFORE make so the
        # VPATH pattern rules see up-to-date targets and skip regeneration
        # (which would re-embed the absolute srcdir path into #include).
        self._pregrow_rpcgen_stubs(rpcgen)
        autotools.make(args=["-j1"])
        # Belt-and-braces sweep (no-op when pre-grow held).
        self._fix_rpcgen_absolute_includes()
        # Post-build diagnostics: dump generated header sizes + symbol
        # presence so an empty rpcgen output is visible here, not only
        # as 20 cascading test errors later.
        try:
            for _hdr, _syms in (("vxi.h", ("DEVICE_CORE", "Create_LinkParms",
                                           "xdr_Create_LinkParms")),
                                ("vxi_intr.h", ("DEVICE_INTR",
                                                "Device_SrqParms"))):
                for _root, _, _files in os.walk(str(self.build_folder)):
                    if "rpcgen-priv" in _root or _hdr not in _files:
                        continue
                    _fp = os.path.join(_root, _hdr)
                    try:
                        with open(_fp, "r", encoding="utf-8",
                                  errors="replace") as _f:
                            _c = _f.read()
                        _miss = [s for s in _syms if s not in _c]
                        self.output.info(
                            f"vxi: built {_hdr} at {_fp}: {len(_c)} chars, "
                            f"missing={_miss}")
                    except Exception as _e:
                        self.output.warning(
                            f"vxi: dump {_fp} skipped: {_e}")
        except Exception as _e:
            self.output.warning(f"vxi: post-build dump skipped: {_e}")
        # No `make check`: upstream ships no test suite (see
        # test_package/MANIFEST.yml upstream_test_audit).

    def package(self):
        # OHOS `make install` is unusable here (true preflight error
        # 2026-10-14, package()/line 549): the automake install rule runs
        # `.../runtime/.../bin/install -c -m 644 libvxiclient.a
        # libvxiserver.a .../p//lib` which dies with `Error 64`
        # (install-libLIBRARIES). Known platform defect: toybox/HMBS
        # install -c fails on HMDFS and INSTALL_DATA's `-m 644` walks
        # chmod, which HMDFS does not support (E596/E087 pattern; HMBS
        # reports install_shim:true + chmod:0). Upstream `make install`
        # would only place 4 files (2 static archives + 2 headers, see
        # Makefile.am lib_LIBRARIES/nodist_include_HEADERS), so package
        # them directly with conan copy(): deterministic, no install(1),
        # no chmod. Fail loudly when any artifact is missing (never an
        # empty package).
        wanted_libs = ("libvxiclient.a", "libvxiserver.a")
        wanted_hdrs = ("vxi.h", "vxi_intr.h")
        found = {}

        def _harvest(folder):
            for name in wanted_libs + wanted_hdrs:
                if name in found:
                    continue
                src = os.path.join(folder, name)
                if os.path.isfile(src):
                    if name in wanted_libs:
                        copy(self, name, src=folder,
                             dst=os.path.join(self.package_folder, "lib"))
                    else:
                        copy(self, name, src=folder,
                             dst=os.path.join(self.package_folder, "include"))
                    found[name] = src
                    self.output.info(f"vxi: packaged {name} from {src}")

        # Harvest the build tree FIRST: it holds the authoritative
        # rpcgen outputs for a VPATH build. The source tree is only a
        # fallback (mirrored headers). Source-first previously risked
        # packaging a stale header while the main build compiled fine.
        for folder in (getattr(self, "build_folder", None),
                       getattr(self, "source_folder", None)):
            if folder and os.path.isdir(folder):
                _harvest(folder)
        # Out-of-source artifacts live in build subdirs (build-release/);
        # walk the whole build tree (excluding the private rpcgen tool
        # dir, which never holds package artifacts).
        try:
            broot = str(self.build_folder)
            for dirpath, _, files in os.walk(broot):
                if "rpcgen-priv" in dirpath:
                    continue
                if not any(f in files for f in wanted_libs + wanted_hdrs):
                    continue
                _harvest(dirpath)
                if len(found) == 4:
                    break
        except Exception as exc:
            self.output.warning(f"vxi: build-tree harvest skipped: {exc}")
        # Verify the harvested headers really expose the VXI-11 API
        # (true preflight 2026-10-14: main build compiled but test_package
        # saw DEVICE_CORE/Create_LinkParms/xdr_Create_LinkParms undeclared,
        # i.e. a stale/empty vxi.h was packaged). Fail here, not in test.
        for hdr, symbols in (("vxi.h", ("DEVICE_CORE", "Create_LinkParms",
                                        "xdr_Create_LinkParms")),
                             ("vxi_intr.h", ("DEVICE_INTR", "Device_SrqParms"))):
            src = found.get(hdr)
            if not src:
                continue
            try:
                with open(src, "r", encoding="utf-8",
                          errors="replace") as f:
                    content = f.read()
            except Exception as exc:
                raise ConanInvalidConfiguration(
                    f"vxi: cannot read harvested {hdr} at {src}: {exc}")
            absent = [s for s in symbols if s not in content]
            if absent:
                raise ConanInvalidConfiguration(
                    f"vxi: harvested {hdr} at {src} lacks {absent} "
                    f"(stale/empty rpcgen header; refusing to package; "
                    f"size={len(content)} head={content[:300]!r})")
            self.output.info(
                f"vxi: verified {hdr} defines {symbols} ({src})")
        missing = [n for n in wanted_libs + wanted_hdrs if n not in found]
        if missing:
            raise ConanInvalidConfiguration(
                f"vxi: package artifacts missing after build: {missing} "
                f"(searched source + build trees; make install bypassed "
                f"due to OHOS install Error 64)")

    def package_info(self):
        self.cpp_info.libs = ["vxiclient", "vxiserver"]
        self.cpp_info.requires = ["libtirpc::libtirpc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
