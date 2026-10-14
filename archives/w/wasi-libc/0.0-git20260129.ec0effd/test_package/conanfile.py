import os
import platform
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import get

TARGET_TRIPLE = "wasm32-wasip1"

ZIG_SOURCES = {
    "zig-x86_64": {
        "url": ["https://ziglang.org/download/0.14.0/zig-linux-x86_64-0.14.0.tar.xz"],
        "sha256": "473ec26806133cf4d1918caf1a410f8403a13d979726a9045b421b685031a982",
    },
    "zig-aarch64": {
        "url": ["https://ziglang.org/download/0.14.0/zig-linux-aarch64-0.14.0.tar.xz"],
        "sha256": "ab64e3ea277f6fc5f3d723dcd95d9ce1ab282c8ed0f431b4de880d30df891e4f",
    },
}

BUILTINS_SOURCE = {
    "url": ["https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-25/libclang_rt.builtins-wasm32-wasi-25.0.tar.gz"],
    "sha256": "13aca55665321200b9659b292615adf5110ace9e891ab94511badd970553ca18",
    "filename": "libclang_rt.builtins-wasm32-wasi-25.0.tar.gz",
}

# Mirrors the wrapper built by the recipe (see conanfile.py there for the
# full rationale): compile via zig cc, link via the OHOS SDK clang driver
# with a wasm-ld shim over `zig wasm-ld` (LLD 19).
WRAPPER_CLANG = r"""#!/bin/sh
ZIG="__ZIG__"
SDKCC="__SDKCC__"
HERE=$(cd "$(dirname "$0")" && pwd)
export ZIG_GLOBAL_CACHE_DIR="${HERE}/../zig-cache"
compile_only=0
for a in "$@"; do
  case "$a" in
    -c|-E|-S) compile_only=1 ;;
  esac
done
if [ "$compile_only" != 1 ]; then
  exec "$SDKCC" -B"$HERE" "$@"
fi
remaining=$#
ZIGPATH="$(dirname "$ZIG"):/usr/bin:/bin"
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
    *)
      set -- "$@" "$arg"
      ;;
  esac
done

PATH="$ZIGPATH" exec "$ZIG" cc "$@"
"""
WRAPPER_WASM_LD = r"""#!/bin/sh
HERE=$(cd "$(dirname "$0")" && pwd)
export ZIG_GLOBAL_CACHE_DIR="${HERE}/../zig-cache"
exec "__ZIG__" wasm-ld "$@"
"""


class WasiLibcTestConan(ConanFile):
    """Consumer test: compile test_consumer.c to wasm32-wasip1 against the
    packaged sysroot (zig cc for codegen, OHOS SDK clang driver + LLD-19
    wasm-ld shim for linking, exactly as the recipe builds wasi-libc
    itself), then execute it under Node.js's built-in WASI."""
    settings = "os", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _host_dir(self):
        return os.path.join(self.build_folder, "host-tools")

    def _zig_exe(self):
        return os.path.join(self._host_dir(), "zig", "zig")

    def _find_binary_sign_tool(self):
        c = shutil.which("binary-sign-tool")
        if c:
            return c
        home = os.path.expanduser("~/.harmonybrew/Cellar")
        if os.path.isdir(home):
            for entry in sorted(os.listdir(home)):
                if entry.startswith("ohos-sdk"):
                    cdir = os.path.join(home, entry)
                    for sub in sorted(os.listdir(cdir)):
                        cand = os.path.join(cdir, sub, "bin",
                                            "binary-sign-tool")
                        if os.path.isfile(cand):
                            return cand
        return None

    def _ensure_zig(self):
        machine = platform.machine().lower()
        key = "zig-x86_64" if machine in ("x86_64", "amd64") else "zig-aarch64"
        zig_dir = os.path.join(self._host_dir(), "zig")
        marker = os.path.join(zig_dir, ".ohos-signed")
        if os.path.exists(marker):
            return
        get(self, **ZIG_SOURCES[key], destination=zig_dir, strip_root=True)
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
        inc = os.path.join(zig_dir, "lib", "libc", "include")
        for d in ("wasm-wasi-musl", "generic-musl", "wasm32-wasi-any",
                  "any-wasi-any"):
            shutil.rmtree(os.path.join(inc, d), ignore_errors=True)
        open(marker, "w").close()

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

    def _wrappers(self):
        wdir = os.path.join(self.build_folder, "wrapper-bin")
        os.makedirs(wdir, exist_ok=True)
        clang = os.path.join(wdir, "clang")
        with open(clang, "w", newline="\n") as fh:
            fh.write(WRAPPER_CLANG
                     .replace("__ZIG__", self._zig_exe())
                     .replace("__SDKCC__", self._sdk_clang()))
        st = os.stat(clang)
        os.chmod(clang, st.st_mode | stat.S_IXUSR)
        shim = os.path.join(wdir, "wasm-ld")
        with open(shim, "w", newline="\n") as fh:
            fh.write(WRAPPER_WASM_LD.replace("__ZIG__", self._zig_exe()))
        st = os.stat(shim)
        os.chmod(shim, st.st_mode | stat.S_IXUSR)
        return os.path.join(wdir, "clang")

    def _ensure_builtins_resource(self):
        """Lay out compiler-rt builtins where the SDK clang driver expects
        them inside a resource dir (lib/wasip1/libclang_rt.builtins-wasm32.a)
        and return the resource-dir path for the link step."""
        bdir = os.path.join(self.build_folder, "builtins")
        out = os.path.join(bdir, "libclang_rt.builtins-wasm32.a")
        if not os.path.exists(out):
            local_dir = os.environ.get("WASILIBC_OFFLINE_DIR")
            if local_dir:
                local = os.path.join(local_dir, BUILTINS_SOURCE["filename"])
            else:
                local = None
            if local and os.path.isfile(local):
                import hashlib
                h = hashlib.sha256(open(local, "rb").read()).hexdigest()
                if h != BUILTINS_SOURCE["sha256"]:
                    raise Exception("builtins sha256 mismatch: %s" % h)
                os.makedirs(bdir, exist_ok=True)
                from conan.tools.files import unzip
                unzip(self, local, destination=bdir, strip_root=True)
            else:
                get(self, **BUILTINS_SOURCE, destination=bdir, strip_root=True)
        res = os.path.join(self.build_folder, "resource")
        dst = os.path.join(res, "lib", "wasip1")
        os.makedirs(dst, exist_ok=True)
        shutil.copyfile(out, os.path.join(dst, "libclang_rt.builtins-wasm32.a"))
        return res

    def test(self):
        self._ensure_zig()
        clang = self._wrappers()
        resdir = self._ensure_builtins_resource()

        deps = self.dependencies["wasi-libc"]
        sysroot = deps.cpp_info.resdirs[0]
        inc = os.path.join(sysroot, "include", TARGET_TRIPLE)
        lib = os.path.join(sysroot, "lib", TARGET_TRIPLE)
        libc_a = os.path.join(lib, "libc.a")
        crt = os.path.join(lib, "crt1.o")
        for p in (inc, lib, libc_a, crt):
            if not os.path.exists(p):
                raise Exception("packaged sysroot missing: %s" % p)

        src = os.path.join(self.source_folder, "test_consumer.c")
        obj = os.path.join(self.build_folder, "test_consumer.o")
        out = os.path.join(self.build_folder, "consumer.wasm")
        # Two steps: compile (zig cc provides the wasm backend; the sysroot
        # headers live under include/<triple> and zig does not resolve
        # --sysroot include paths itself, so -I is passed explicitly) then
        # link (SDK clang driver + wasm-ld shim resolve crt/libc from the
        # packaged sysroot, not from zig's bundled libc).
        # -O2 keeps zig cc out of its debug default, which instruments the
        # object with UBSan handlers the wasm link cannot resolve.
        self.run('"%s" --target=%s --sysroot="%s" -I"%s" -O2 -c "%s" -o "%s"'
                 % (clang, TARGET_TRIPLE, sysroot, inc, src, obj),
                 env="conanbuild")
        self.run('"%s" --target=%s --sysroot="%s" -resource-dir "%s" "%s" -o "%s"'
                 % (clang, TARGET_TRIPLE, sysroot, resdir, obj, out),
                 env="conanbuild")

        tmpdir = os.path.join(self.build_folder, "fsdata")
        os.makedirs(tmpdir, exist_ok=True)
        node = self._node()
        runner = os.path.join(self.source_folder, "wasi-run.mjs")
        self.run('"%s" "%s" --env WASI_CONSUMER_ENV=ohos --dir "%s"::/ "%s"'
                 % (node, runner, tmpdir, out),
                 env="conanbuild")
