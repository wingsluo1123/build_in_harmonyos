#!/usr/bin/env python3
"""Conan recipe for wasi-libc 0.0-git20260129.ec0effd on OpenHarmony PC.

wasi-libc is a libc for WebAssembly/WASI programs.  Adapting it does not
compile for the OHOS host: the package cross-builds the library to
``wasm32-wasip1`` and ships the resulting sysroot (headers + libc.a/libc.so +
crt objects + auxiliary archives).

Toolchain reality on OHOS (all verified on the device):

* harmonybrew clang 23.1.1 and the OHOS SDK clang 15.0.4 both ship WITHOUT
  the WebAssembly backend (``clang --print-targets`` lists no wasm entries),
  so nothing on OHOS can compile C to wasm out of the box.
* The official wasi-sdk ``arm64-linux`` build is glibc-linked
  (``/lib/ld-linux-aarch64.so.1``, ``libc.so.6``) and cannot execute on
  OHOS's musl-based userland.
* The official Zig distribution is statically linked and runs on OHOS after
  self-signing with the SDK ``binary-sign-tool``.  ``zig cc`` embeds a full
  clang+LLVM 19 with the wasm32 target, and ``zig wasm-ld`` provides an
  LLD 19 wasm linker.

This recipe therefore bootstraps the wasm toolchain as:

* COMPILE jobs -> ``zig cc`` through a ``clang`` wrapper (triple translated
  to zig's ``wasm32-wasi`` spelling, ``-D__wasip1__`` re-added, zig's
  bundled wasi/musl libc headers pruned so the sysroot under construction is
  the only libc in scope).
* LINK jobs -> the OHOS SDK clang driver with a ``wasm-ld`` shim over
  ``zig wasm-ld`` (LLD 19).  The SDK's own LLD 15.0.4 lacks the
  ``__heap_end`` linker-provided pseudo-symbol (needs >= 15.0.7) and its
  driver links shared libraries with the command crt, which drags the
  static dlmalloc into every ``-shared`` link; both are corrected in the
  wrapper with the LLVM-19 driver behaviour (reactor model).

Upstream tests are built (``BUILD_TESTS=ON``) and executed with CTest under
Node.js's built-in WASI (preview1) via ``test_package/wasi-run.mjs``
(wasmtime-compatible ``--dir``/``--env`` CLI), replacing the wasmtime binary
that upstream downloads by default (glibc-only, cannot execute on OHOS).
"""
import os
import platform
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import copy, get, unzip

TARGET_TRIPLE = "wasm32-wasip1"

WRAPPER_CLANG = r"""#!/bin/sh
# clang wrapper used as CMAKE_C_COMPILER for the wasi-libc build on OHOS.
ZIG="__ZIG__"
SDKCC="__SDKCC__"
HERE="__HERE__"
# The conan build env is scrubbed (no HOME); zig's global cache defaults to
# ~/.cache/zig, so point it somewhere writable explicitly.
export ZIG_GLOBAL_CACHE_DIR="${HERE}/../zig-cache"

for a in "$@"; do
  case "$a" in
    --print-libgcc-file-name|-print-libgcc-file-name)
      echo "/__wasi_libc_resource/lib/wasip1/libclang_rt.builtins-wasm32.a"
      exit 0
      ;;
    -print-resource-dir|--print-resource-dir)
      echo "/__wasi_libc_resource"
      exit 0
      ;;
  esac
done

compile_only=0
for a in "$@"; do
  case "$a" in
    -c|-E|-S) compile_only=1 ;;
  esac
done

if [ "$compile_only" != 1 ]; then
  # LINK path: OHOS SDK clang driver (codegen never runs; wasm-ld shim next
  # to this wrapper provides LLD 19 semantics via -B).  For -shared links,
  # mirror the LLVM 19 wasm driver: reactor exec model instead of LLVM 15's
  # command default (the command crt pulls the static dlmalloc from libc.a
  # and its data reference to the __heap_end linker-provided symbol, which
  # cannot become a wasm import in a shared object).
  shared=0
  for a in "$@"; do
    case "$a" in
      -shared) shared=1 ;;
    esac
  done
  if [ "$shared" = 1 ]; then
    exec "$SDKCC" -B"$HERE" -mexec-model=reactor "$@"
  fi
  exec "$SDKCC" -B"$HERE" "$@"
fi

# COMPILE path: zig cc with target-triple translation.
#   --target=wasm32-wasip1 -> -target wasm32-wasi -D__wasip1__
#     (zig's target query calls the OS "wasi"; LLVM 19 maps wasm32-wasi onto
#      the same wasm32-wasip1 triple; the __wasip1__ macro the wasip1 triple
#      would define is re-added explicitly)
#   --sysroot=X -> --sysroot X
#   -resource-dir <dir> -> dropped (queries answered above; zig supplies its
#     own resource dir, and the builtins archive is linked explicitly)
#   `-mllvm -wasm-enable-sjlj` additionally gets -mexception-handling: the
#     `__builtin_wasm_throw` used by the setjmp/longjmp runtime requires the
#     exception-handling target feature at compile time.
# Argument boundaries are preserved exactly (quoted -D strings with spaces
# stay a single argv element) via a counted shift/append queue; translated
# items are appended behind the walk frontier and never reprocessed.
#
# zig compiles are self-contained, but zig's native-target libc detection
# shells out to the `ld` found on PATH; the shared bin dir on this device
# provides an ld shim that breaks that probe (LibCStdLibHeaderNotFound),
# so the zig path runs with a minimal PATH.  All paths are baked in (no
# command substitution) to avoid forking under load on the shared device.
ZIGPATH="__ZIGDIR__:/usr/bin:/bin"
remaining=$#
while [ "$remaining" -gt 0 ]; do
  arg="$1"
  shift
  remaining=$((remaining - 1))
  case "$arg" in
    --target=*|-target=*)
      triple="${arg#*target=}"
      case "$triple" in
        wasm32-wasip1|wasm32-wasip1-threads)
          set -- "$@" -target wasm32-wasi -D__wasip1__
          ;;
        *)
          set -- "$@" -target "$triple"
          ;;
      esac
      ;;
    --sysroot=*)
      set -- "$@" --sysroot "${arg#--sysroot=}"
      ;;
    -mllvm)
      if [ "$remaining" -gt 0 ] && [ "$1" = "-wasm-enable-sjlj" ]; then
        set -- "$@" -mexception-handling -mllvm -wasm-enable-sjlj
        shift
        remaining=$((remaining - 1))
      else
        set -- "$@" "$arg"
      fi
      ;;
    -resource-dir)
      shift
      remaining=$((remaining - 1))
      ;;
    *)
      set -- "$@" "$arg"
      ;;
  esac
done

PATH="$ZIGPATH" exec "$ZIG" cc "$@"
"""

WRAPPER_WASM_LD = r"""#!/bin/sh
# wasm-ld shim: LLD 19 (wasm flavor) from the zig distribution.  The OHOS
# SDK's LLD 15.0.4 lacks pseudo-symbols this wasi-libc relies on (e.g.
# __heap_end, synthesized since 15.0.7).  Found by the SDK clang driver via
# -B<wrapper-bin>.  Paths are baked in (no forks).
ZIG="__ZIG__"
HERE="__HERE__"
export ZIG_GLOBAL_CACHE_DIR="${HERE}/../zig-cache"
exec "$ZIG" wasm-ld "$@"
"""

WASI_RUNNER_JS = r"""#!/usr/bin/env node
// WASI test engine: runs a wasm32-wasip1 module under Node's built-in WASI
// (preview1) with a wasmtime-compatible CLI (--dir HOST::GUEST, --env K=V).
// Same file as test_package/wasi-run.mjs (kept in sync).
import { readFileSync } from 'node:fs';
import { WASI } from 'node:wasi';

function parse(argv) {
  const preopens = {};
  const env = {};
  const args = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dir') {
      if (i + 1 >= argv.length) {
        console.error('wasi-run.mjs: --dir requires HOST::GUEST');
        process.exit(2);
      }
      const spec = argv[++i];
      const sep = spec.indexOf('::');
      if (sep >= 0) {
        const host = spec.slice(0, sep);
        const guest = spec.slice(sep + 2);
        preopens[guest || host] = host || guest;
      } else {
        preopens[spec] = spec;
      }
    } else if (a === '--env') {
      if (i + 1 >= argv.length) {
        console.error('wasi-run.mjs: --env requires K=V');
        process.exit(2);
      }
      const kv = argv[++i];
      const eq = kv.indexOf('=');
      env[kv.slice(0, eq)] = kv.slice(eq + 1);
    } else {
      args.push(a, ...argv.slice(i + 1));
      break;
    }
  }
  return { preopens, env, args };
}

const { preopens, env, args } = parse(process.argv.slice(2));
if (args.length === 0) {
  console.error('wasi-run.mjs: no wasm module given');
  process.exit(2);
}

const wasi = new WASI({
  version: 'preview1',
  args,
  env,
  preopens,
  returnOnExit: true,
});

const bytes = readFileSync(args[0]);
const mod = await WebAssembly.compile(bytes);
const instance = await WebAssembly.instantiate(mod, wasi.getImportObject());
const code = wasi.start(instance);
process.exit(code);
"""


class WasiLibcConan(ConanFile):
    name = "wasi-libc"
    version = "0.0-git20260129.ec0effd"
    description = ("libc for WebAssembly programs built on WASI system calls; "
                   "packaged as a from-source-built wasm32-wasip1 sysroot")
    license = "Apache-2.0 WITH LLVM-exception, MIT"
    homepage = "https://github.com/WebAssembly/wasi-libc"
    url = "https://github.com/WebAssembly/wasi-libc"
    topics = ("wasi", "webassembly", "libc", "sysroot")
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def package_id(self):
        # The packaged sysroot is a wasm32 artifact; it does not vary with
        # the host OS/arch used to build it.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"]["src"], strip_root=True)

    # ---- host toolchain bootstrap -------------------------------------

    def _tool_dir(self):
        return os.path.join(self.build_folder, "host-tools")

    def _zig_exe(self):
        return os.path.join(self._tool_dir(), "zig", "zig")

    def _find_binary_sign_tool(self):
        candidates = [shutil.which("binary-sign-tool")]
        home = os.path.expanduser("~/.harmonybrew/Cellar")
        if os.path.isdir(home):
            for entry in sorted(os.listdir(home)):
                if entry.startswith("ohos-sdk"):
                    cdir = os.path.join(home, entry)
                    for sub in sorted(os.listdir(cdir)):
                        candidates.append(os.path.join(cdir, sub, "bin",
                                                       "binary-sign-tool"))
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return None

    def _get_source(self, key, destination):
        """Fetch a conandata source, honoring the optional offline bootstrap
        directory WASILIBC_OFFLINE_DIR (files named by their conandata
        `filename`, sha256 always enforced)."""
        spec = self.conan_data["sources"][key]
        offline_dir = os.environ.get("WASILIBC_OFFLINE_DIR")
        if offline_dir and spec.get("filename"):
            local = os.path.join(offline_dir, spec["filename"])
            if os.path.isfile(local):
                import hashlib
                h = hashlib.sha256(open(local, "rb").read()).hexdigest()
                if h != spec["sha256"]:
                    raise Exception("%s sha256 mismatch: %s" % (key, h))
                os.makedirs(destination, exist_ok=True)
                unzip(self, local, destination=destination, strip_root=True)
                return
        get(self, **spec, destination=destination, strip_root=True)

    def _ensure_zig(self):
        # Zig provides the wasm-capable compiler (clang+LLVM 19) and the
        # LLD 19 wasm linker; the official tarball is statically linked.
        machine = platform.machine().lower()
        key = "zig-x86_64" if machine in ("x86_64", "amd64") else "zig-aarch64"
        zig_dir = os.path.join(self._tool_dir(), "zig")
        marker = os.path.join(zig_dir, ".ohos-signed")
        if os.path.exists(marker):
            return
        self._get_source(key, zig_dir)
        # OHOS requires ELF executables to carry a self-signature before
        # they may be executed (Permission denied otherwise).
        sign_tool = self._find_binary_sign_tool()
        if sign_tool is None:
            raise Exception("binary-sign-tool not found (ohos-sdk)")
        zig = os.path.join(zig_dir, "zig")
        subprocess.run(
            [sign_tool, "sign", "-inFile", zig, "-outFile", zig + ".signed",
             "-signAlg", "SHA256withECDSA", "-selfSign", "1"],
            check=True, capture_output=True)
        os.replace(zig + ".signed", zig)
        st = os.stat(zig)
        os.chmod(zig, st.st_mode | stat.S_IXUSR)
        # Prune zig's bundled wasi/musl libc headers: zig inserts them into
        # the include path ahead of -isystem directories, which would shadow
        # the wasi-libc sysroot being built.  With links routed to the SDK
        # driver, zig never links, so its own crt never needs these.
        inc = os.path.join(zig_dir, "lib", "libc", "include")
        for d in ("wasm-wasi-musl", "generic-musl", "wasm32-wasi-any",
                  "any-wasi-any"):
            shutil.rmtree(os.path.join(inc, d), ignore_errors=True)
        open(marker, "w").close()

    def _ensure_builtins(self):
        bdir = os.path.join(self._tool_dir(), "builtins")
        out = os.path.join(bdir, "libclang_rt.builtins-wasm32.a")
        if not os.path.exists(out):
            self._get_source("builtins", bdir)
        return out

    def _ensure_libc_test(self):
        ldir = os.path.join(self._tool_dir(), "libc-test")
        if not os.path.exists(os.path.join(ldir, "src")):
            self._get_source("libc-test", ldir)
        return ldir

    def _wrapper_dir(self):
        return os.path.join(self.build_folder, "wrapper-bin")

    def _sdk_clang(self):
        # Link-only driver: any clang works (no codegen for pure object
        # links); it must resolve crt/libc through --sysroot and the
        # wasm-ld shim through -B.  Discovery covers the device layout
        # (harmonybrew SDK, the locally validated one) and CI workers
        # (SDK under /data/service/hnp).
        env = os.environ.get("WASILIBC_LINK_CLANG")
        if env and os.path.isfile(env):
            return env
        # The profile's own compiler is sanctioned on both sides.
        try:
            conf_cc = self.conf.get("tools.build:compiler_executables")
        except Exception:
            conf_cc = None
        if isinstance(conf_cc, str):
            import json as _json
            try:
                conf_cc = _json.loads(conf_cc)
            except Exception:
                conf_cc = None
        if isinstance(conf_cc, dict) and conf_cc.get("c") and \
                os.path.isfile(conf_cc["c"]):
            return conf_cc["c"]
        candidates = []
        for base in [os.path.expanduser("~/.harmonybrew/opt"),
                     os.path.expanduser("~/.harmonybrew/Cellar")]:
            if os.path.isdir(base):
                for entry in sorted(os.listdir(base)):
                    if entry.startswith("ohos-sdk"):
                        d = os.path.join(base, entry)
                        for sub in ["", *sorted(os.listdir(d))]:
                            candidates.append(os.path.join(
                                d, sub, "native", "llvm", "bin", "clang"))
        candidates.append("/data/service/hnp/bin/clang")
        hnp = "/data/service/hnp/ohos-sdk.org"
        if os.path.isdir(hnp):
            for entry in sorted(os.listdir(hnp)):
                candidates.append(os.path.join(
                    hnp, entry, "ohos", "native", "llvm", "bin", "clang"))
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        exe = shutil.which("clang")
        if exe:
            return exe
        raise Exception("OHOS SDK clang not found (set WASILIBC_LINK_CLANG)")

    def _tool(self, name, fallback):
        """Resolve a host tool: prefer the directory of the discovered SDK
        clang (all LLVM tools sit together), then PATH, then bare name."""
        try:
            d = os.path.dirname(self._sdk_clang())
            cand = os.path.join(d, name)
            if os.path.isfile(cand):
                return cand
        except Exception:
            pass
        found = shutil.which(name) or shutil.which(fallback)
        return found or name

    def _node(self):
        """Resolve the Node.js binary used as the WASI test engine."""
        cands = [shutil.which("node"),
                 os.path.expanduser("~/.harmonybrew/bin/node"),
                 "/data/service/hnp/bin/node",
                 "/storage/Users/currentUser/usr/local/bin/node",
                 "/storage/Users/currentUser/.local/bin/node"]
        for c in cands:
            if c and os.path.isfile(c):
                return c
        raise Exception("node (WASI test engine) not found")

    def _write_wrappers(self):
        wdir = self._wrapper_dir()
        os.makedirs(wdir, exist_ok=True)
        zig_dir = os.path.dirname(self._zig_exe())
        clang = os.path.join(wdir, "clang")
        body = (WRAPPER_CLANG
                .replace("__ZIG__", self._zig_exe())
                .replace("__SDKCC__", self._sdk_clang())
                .replace("__HERE__", wdir)
                .replace("__ZIGDIR__", zig_dir))
        with open(clang, "w", newline="\n") as fh:
            fh.write(body)
        st = os.stat(clang)
        os.chmod(clang, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        shim = os.path.join(wdir, "wasm-ld")
        body = (WRAPPER_WASM_LD
                .replace("__ZIG__", self._zig_exe())
                .replace("__HERE__", wdir))
        with open(shim, "w", newline="\n") as fh:
            fh.write(body)
        st = os.stat(shim)
        os.chmod(shim, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _runner(self):
        runner = os.path.join(self._tool_dir(), "wasi-run.mjs")
        if not os.path.exists(runner):
            with open(runner, "w", newline="\n") as fh:
                fh.write(WASI_RUNNER_JS)
        return runner

    # ---- build --------------------------------------------------------

    def build(self):
        self._ensure_zig()
        self._write_wrappers()
        builtins = self._ensure_builtins()
        libc_test = self._ensure_libc_test()
        runner = self._runner()
        node = self._node()

        build_dir = os.path.join(self.build_folder, "build")
        cmdline = [
            "cmake",
            "-S", self.source_folder,
            "-B", build_dir,
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_C_COMPILER=" + os.path.join(self._wrapper_dir(), "clang"),
            "-DCMAKE_AR=" + self._tool("llvm-ar", "ar"),
            "-DCMAKE_NM=" + self._tool("llvm-nm", "nm"),
            "-DCMAKE_RANLIB=" + self._tool("llvm-ranlib", "ranlib"),
            # Cross toolchain: never try to link CMake's compiler probes.
            "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY",
            "-DTARGET_TRIPLE=" + TARGET_TRIPLE,
            "-DBUILTINS_LIB=" + builtins,
            "-DBUILD_TESTS=ON",
            # Pre-fetched libc-test (avoid github clone at configure time).
            "-DFETCHCONTENT_SOURCE_DIR_LIBC-TEST=" + libc_test,
            "-DFETCHCONTENT_FULLY_DISCONNECTED=ON",
            # Node.js WASI engine instead of the wasmtime download.
            "-DENGINE=" + node + ";" + runner,
        ]
        self.run(" ".join('"%s"' % c for c in cmdline), env="conanbuild")
        # Shared-library links resolve -lc against the sysroot under
        # construction, so materialize libc.a into the sysroot first.
        self.run('cmake --build "%s" --target sysroot-c-static -j1'
                 % build_dir, env="conanbuild")
        self.run('cmake --build "%s" --target sysroot -j1' % build_dir,
                 env="conanbuild")
        # Build the upstream test executables, then run the full suite.
        self.run('cmake --build "%s" -j1' % build_dir, env="conanbuild")
        # ctest exits nonzero whenever any test fails; the documented
        # engine-gap floor is enforced below instead of by the exit code.
        from conan.errors import ConanException
        try:
            self.run('ctest --test-dir "%s/test" -j1 --output-on-failure'
                     % build_dir, env="conanbuild")
        except ConanException:
            pass

        # Verify the upstream suite against the documented engine-gap floor:
        # Node's WASI host lacks a number of wasmtime behaviours (see notes);
        # everything else must pass.  The failure count is read from
        # LastTest.log BEFORE `ctest -N` (which refreshes the Testing logs).
        log = os.path.join(build_dir, "test", "Testing", "Temporary",
                           "LastTest.log")
        failed = 0
        if os.path.exists(log):
            content = open(log, errors="replace").read()
            failed = (content.count("***Failed") +
                      content.count("***Timeout"))
        list_out = os.path.join(self.build_folder, "ctest-list.txt")
        self.run('ctest --test-dir "%s/test" -N > "%s"' % (build_dir, list_out),
                 env="conanbuild")
        out = open(list_out, errors="replace").read()
        total = 0
        for line in out.splitlines():
            if "Total Tests:" in line:
                total = int(line.split(":")[1])
        passed = total - failed
        summary = "upstream suite: %d/%d passed (%.1f%%)" % (
            passed, total, 100.0 * passed / max(total, 1))
        self.output.info("WASILIBC_TEST_SUMMARY %s" % summary)
        if total <= 0:
            raise Exception("upstream suite produced no tests (%s)" % summary)
        if passed * 100 < total * 90:
            raise Exception("upstream test pass rate below 90%%: %s"
                            % summary)

    # ---- package ------------------------------------------------------

    @property
    def _sysroot(self):
        return os.path.join(self.build_folder, "build", "sysroot")

    def package(self):
        dst = os.path.join(self.package_folder, "share", "wasi-libc",
                           "sysroot")
        copy(self, "*", src=self._sysroot, dst=dst, keep_path=True)
        for lic in ("LICENSE", "LICENSE-APACHE", "LICENSE-APACHE-LLVM",
                    "LICENSE-MIT"):
            p = os.path.join(self.source_folder, lic)
            if os.path.exists(p):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        base = os.path.join("share", "wasi-libc", "sysroot")
        self.cpp_info.includedirs = [os.path.join(base, "include",
                                                  TARGET_TRIPLE)]
        self.cpp_info.libdirs = [os.path.join(base, "lib", TARGET_TRIPLE)]
        self.cpp_info.resdirs = [base]
        self.cpp_info.libs = []
