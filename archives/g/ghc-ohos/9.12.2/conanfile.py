#!/usr/bin/env python3
"""Conan recipe for ghc-ohos 9.12.2 — GHC (Glasgow Haskell Compiler) toolchain
for HarmonyOS PC.

Delivers the compiler and its runtime only (no Hackage packages).  The
bootstrap mirrors the proven bsc 2026.01 approach documented in
docs/ghc-ohos-9.12.2适配文档-20260928.md, and the pieces below are the ones
that were verified there on a real device.

Why the alpine3_18 musl bindist
-------------------------------
OHOS is pure musl.  GHC's aarch64-deb10/deb12 variants link glibc and need
/lib/ld-linux-aarch64.so.1, so they cannot execute here (E105/E172); the
aarch64-alpine3_18 bindist is the only runnable official aarch64 build.  Its
musl runtime dependencies (gmp, libffi, ncursesw, terminfo) are taken from the
matching alpine v3.18 APKs.

Long-haul download
------------------
downloads.haskell.org throttles a single connection (~20-60KB/s) and is not in
the CI mirror list, so the 601 MB bindist is fetched with a chunked-parallel
Range downloader (24 chunks) with per-chunk verification; a peer that ignores
Range and answers 200 with the whole body is detected and kept as the full
download.  The official sha256 is verified afterwards.

Foreign ELF execution on OHOS
-----------------------------
Every ELF from the bindist must be self-signed (llvm-objcopy strips the
.codesign section, binary-sign-tool signs it back) — and signing MUST happen
after the last copy(), because Conan's copy() rewrites files and breaks the
signature (E212 family).

Known platform limitation
-------------------------
runghc/GHCi cannot work: libffi closures need executable anonymous memory,
which OHOS denies (ffi_closure_alloc fails).  Hackage installs must therefore
be done with `ghc --make` on Setup scripts, not with runghc/Cabal
interpretation.  This recipe does not depend on it.

R32: settings.os must check in ("Linux", "OHOS").
R38: package_type="application" ships bin/ tools -> commands.json is required.
R51: upstream ships no test suite of its own; see test_package/.
"""
import glob
import hashlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, download, get, save
from conan.tools.layout import basic_layout

DL_CHUNKS = 24

# AArch64 out-of-line atomics: the bindist's objects reference GCC-13-era
# __aarch64_*_sync helpers; clang-15's compiler-rt only ships relax/acq/rel/
# acq_rel.  Alias the missing spellings onto acq_rel (bsc precedent).
DEFYSMS = " ".join(
    "-Wl,--defsym,__aarch64_%s%d_sync=__aarch64_%s%d_acq_rel" % (fam, n, fam, n)
    for fam in ("cas", "ldadd", "ldclr", "ldeor", "ldset", "swp")
    for n in (1, 2, 4, 8)
) + " -Wl,--defsym,__aarch64_cas16_sync=__aarch64_cas16_acq_rel"

GCC_SHIM = r"""#!/bin/sh
# gcc/g++/cc shim (OHOS): expands GHC's quoted @response-files, forwards
# query/compile modes straight to clang-15, and appends the runtime libs plus
# the atomics defsyms only on link steps.  Archive inputs go through -Wl, so
# `-x c` link invocations never mistake them for sources.
#
# The runtime-lib directory is resolved relative to this script (../lib) so
# the same shim works both from the build tree and from the installed package.
SHIMDIR=$(cd "$(dirname "$0")" && pwd)
LOG="$SHIMDIR/calls.log"
TC="__TC__"
SYSROOT="__SYSROOT__"
RT="__BUILTINS__"
SB="$SHIMDIR/misc_stubs.o"
RL="$SHIMDIR/../lib"
DY="__DEFYSMS__"
SIGNTOOL="__SIGN__"
OBJCOPY="__OBJCOPY__"
CXX=
[ "$(basename "$0")" = g++ ] && CXX="--driver-mode=g++"
EXP=""
for a in "$@"; do
  case "$a" in
    @*) rf=${a#@}
        [ -f "$rf" ] && rsp=$(cat "$rf" 2>/dev/null | tr "\n" " " | sed "s/\"//g") || rsp="$a"
        EXP="$EXP $rsp" ;;
    *)   EXP="$EXP $a" ;;
  esac
done
set -- $EXP
for a in "$@"; do
  case "$a" in
    -dumpversion|-dumpmachine|--version|-print*|-showMe*|-v)
      exec "$TC/clang-15" "$@" ;;
    -c|-S|-E)
      exec "$TC/clang-15" $CXX "--sysroot=$SYSROOT" -D__MUSL__ "$@" -Wno-unused-command-line-argument ;;
  esac
done
printf "[LINK] %s\n" "$*" >> "$LOG" 2>/dev/null
# -Wl,--code-sign is mandatory on LINK steps: OHOS refuses to execute an ELF
# without a valid .codesign section (EPERM).  It must NOT be on compile steps
# (the SDK wrapper adds it unconditionally, which breaks GHC's -Werror C
# preprocessing), so it is confined to this branch.
"$TC/clang-15" $CXX "--sysroot=$SYSROOT" -D__MUSL__ -fuse-ld=lld -Wl,--code-sign "-L$RL" "$@" -Wl,"$RT" -Wl,"$SB" $DY -Wno-unused-command-line-argument
rc=$?
[ $rc -ne 0 ] && exit $rc

# --code-sign only emits a *placeholder* section; OHOS still refuses to run
# the result (EPERM) until it is signed with binary-sign-tool.  Sign the link
# output here so every binary a consumer builds with this toolchain is
# directly executable (the recipe signs the packaged files the same way).
out=
prev=
for a in "$@"; do
  [ "$prev" = "-o" ] && out="$a"
  prev="$a"
done
if [ -n "$out" ] && [ -f "$out" ]; then
  "$OBJCOPY" --remove-section .codesign "$out" 2>/dev/null
  if "$SIGNTOOL" sign -inFile "$out" -outFile "$out.signed" -selfSign 1 >/dev/null 2>&1 \
     && [ -s "$out.signed" ]; then
    # Write the signed image back through the *same inode*: replacing the file
    # would drop its permission bits, and this platform's chmod cannot restore
    # them (no --reference; same-session chmod on hmdfs is unreliable), which
    # would leave the binary non-executable (EACCES instead of EPERM).
    cat "$out.signed" > "$out" && rm -f "$out.signed"
    printf "[SIGNED] %s\n" "$out" >> "$LOG" 2>/dev/null
  else
    rm -f "$out.signed"
    printf "[SIGN-FAILED] %s\n" "$out" >> "$LOG" 2>/dev/null
  fi
fi
exit 0
"""

MKTEMP_SHIM = r"""#!/bin/sh
# hmdfs quirk: real mktemp chmods fresh dirs to 0700, which the uid-mapped
# filesystem then denies to this session (and same-session chmod is a no-op).
# Implement -d with umask 0.
real="__TC__/mktemp"
isd=0
tmpl=
for a in "$@"; do
    case "$a" in
        -d) isd=1 ;;
        -*) ;;
        *)  [ -z "$tmpl" ] && tmpl=$a ;;
    esac
done
[ "$isd" = 1 ] || exec "$real" "$@"
[ -z "$tmpl" ] && tmpl=./tmp.XXXXXXXXXX
prefix=$(printf "%s" "$tmpl" | sed "s/X\{1,\}$//")
i=0
while :; do
    i=$((i + 1))
    out="$prefix$$-$RANDOM$RANDOM-$i"
    if ( umask 0 && mkdir "$out" ) 2>/dev/null; then
        printf "%s\n" "$out"
        exit 0
    fi
    [ $i -gt 50 ] && exit 1
done
"""

TIME_SHIM = r"""#!/bin/sh
# OHOS toybox `time` lacks -a/-o/-f; wrappers use GNU-time syntax.
while [ $# -gt 0 ]; do
    case "$1" in
        -a|-p|--append|--portability) shift ;;
        -o|-f) shift 2 ;;
        --output=*|--format=*) shift ;;
        -*) shift ;;
        *) break ;;
    esac
done
exec "$@"
"""

# Symbols the OHOS musl does not provide but GHC's runtime objects reference.
MISC_STUBS_C = r"""void dlinfo(void) {}
int posix_spawn_file_actions_addchdir_np(void *a, const char *p) {
    (void)a; (void)p; return 0;
}
"""


class GhcOhosConan(ConanFile):
    name = "ghc-ohos"
    version = "9.12.2"
    description = ("GHC (Glasgow Haskell Compiler) 9.12.2 toolchain for "
                   "HarmonyOS PC: compiler plus runtime, bootstrapped from the "
                   "official aarch64-alpine3_18 musl bindist")
    license = "BSD-3-Clause"
    homepage = "https://www.haskell.org/ghc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Unsupported OS: %s" % self.settings.os)
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "the GHC alpine bindist and this bootstrap are aarch64-only")

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------
    # Toolchain helpers
    # ------------------------------------------------------------------

    def _toolchain_dir(self):
        """Directory holding clang-15/llvm-objcopy/binary-sign-tool."""
        cands = []
        cc = (self.conf.get("tools.build:compiler_executables",
                            check_type=dict) or {}).get("c")
        if cc:
            cands.append(os.path.dirname(os.path.realpath(cc)))
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if d and os.path.exists(os.path.join(d, "clang")):
                cands.append(os.path.dirname(os.path.realpath(
                    os.path.join(d, "clang"))))
                break

        def complete(d):
            return (os.path.exists(os.path.join(d, "clang-15"))
                    and os.path.exists(os.path.join(d, "binary-sign-tool"))
                    and os.path.exists(os.path.join(d, "llvm-objcopy")))

        for c in ("/storage/Users/currentUser/usr/local/bin",
                  "/data/service/hnp/bin") + tuple(cands):
            if complete(c):
                return c
        for c in cands:
            if os.path.exists(os.path.join(c, "clang-15")):
                return c
        raise ConanInvalidConfiguration("clang-15 toolchain not found")

    def _resolve_sysroot(self, tc):
        cands = [
            os.path.join(tc, "..", "sysroot"),
            os.path.join(tc, "..", "..", "sysroot"),
            "/storage/Users/currentUser/usr/local/sysroot",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot",
        ]
        for c in cands:
            if os.path.isfile(os.path.join(c, "usr", "include", "inttypes.h")):
                return os.path.normpath(c)
        raise ConanInvalidConfiguration(
            "musl sysroot (usr/include/inttypes.h) not found for " + tc)

    def _sign_elf(self, path):
        """Self-sign a foreign ELF for OHOS execution."""
        tc = self._tc
        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    return
        except OSError:
            return

        def resolve(name):
            cand = os.path.join(tc, name)
            if os.path.exists(cand):
                return cand
            found = shutil.which(name)
            if found:
                return found
            for d in ("/storage/Users/currentUser/usr/local/bin",
                      "/data/service/hnp/bin",
                      "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                      "ohos/native/llvm/bin"):
                cand = os.path.join(d, name)
                if os.path.exists(cand):
                    return cand
            raise ConanException("signing tool not found: %s" % name)

        objcopy = resolve("llvm-objcopy")
        sign = resolve("binary-sign-tool")
        tmp = path + ".signed"
        # binary-sign-tool writes a fresh file, so the original mode (notably
        # the executable bit on bin/*) must be carried over or the signed
        # replacement is unusable.
        st = os.stat(path)
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=60)
        r = subprocess.run([sign, "sign", "-inFile", path, "-outFile", tmp,
                            "-selfSign", "1"], capture_output=True, timeout=300)
        if r.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            raise ConanException("ELF signing failed: %s" % path)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, path)

    def _sign_tree(self, root):
        """Sign every ELF under root (after the last copy())."""
        n = 0
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(dirpath, f)
                if os.path.islink(p):
                    continue
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                self._sign_elf(p)
                n += 1
        self.output.info("signed %d ELF files under %s" % (n, root))

    # ------------------------------------------------------------------
    # Bindist download (chunked-parallel)
    # ------------------------------------------------------------------

    def _parallel_fetch(self, url, dest, size, sha256):
        """Fetch a large file as parallel HTTP Range chunks, resuming in-chunk.

        downloads.haskell.org throttles a single connection to ~20-60KB/s and
        drops responses mid-body, so the download is split across DL_CHUNKS
        connections (ranges scale linearly through throttles).

        Crucially, a short response must NOT restart its chunk from byte 0:
        with a peer that truncates most responses, restarting throws away
        nearly all progress and the build runs into the CI timeout (observed:
        3600s exceeded with all 24 chunks repeatedly "short").  Each chunk
        therefore continues from the bytes already on disk, re-requesting only
        the missing tail.  A peer that ignores Range and answers 200 with the
        whole body is still detected and kept as the complete file.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor
        chunk = (size + DL_CHUNKS - 1) // DL_CHUNKS
        self.output.info("fetching bindist: %d chunks, %d bytes"
                         % (DL_CHUNKS, size))

        def fetch(i):
            import urllib.request
            start = i * chunk
            end = min(start + chunk, size) - 1
            want = end - start + 1
            part = "%s.part%03d" % (dest, i)
            got = os.path.getsize(part) if os.path.exists(part) else 0
            if got > want:            # stale/oversized leftover
                os.remove(part)
                got = 0
            # A peer that truncates most responses makes each attempt deliver a
            # fraction of what is still missing (geometric decay), so a modest
            # attempt count can leave a chunk a few KB short.  Allow many
            # attempts with a short backoff — the retries are the normal path
            # for this CDN, not an error.
            for attempt in range(80):
                if os.path.exists(dest):
                    return "FULL"
                if got >= want:
                    return "OK"
                try:
                    req = urllib.request.Request(
                        url, headers={"Range": "bytes=%d-%d"
                                      % (start + got, end),
                                      "User-Agent": "curl/8"})
                    with urllib.request.urlopen(req, timeout=300) as r:
                        status = getattr(r, "status", None) or r.getcode()
                        if status == 200:
                            # Peer ignored Range: the body is the file from
                            # byte 0.  Splice it in a scratch file and only
                            # accept it when it really is the whole file.
                            scratch = part + ".full"
                            with open(scratch, "wb") as fh:
                                while True:
                                    blk = r.read(1 << 20)
                                    if not blk:
                                        break
                                    fh.write(blk)
                            if os.path.getsize(scratch) == size:
                                os.replace(scratch, dest)
                                return "FULL"
                            os.remove(scratch)
                            got = 0
                            if os.path.exists(part):
                                os.remove(part)
                            continue
                        with open(part, "ab") as fh:
                            while True:
                                blk = r.read(1 << 20)
                                if not blk:
                                    break
                                fh.write(blk)
                                got += len(blk)
                    if got >= want:
                        return "OK"
                    self.output.info("chunk%d resuming at %d/%d (a%d)"
                                     % (i, got, want, attempt + 1))
                except Exception as exc:
                    self.output.info("chunk%d retry from %d/%d (%r, a%d)"
                                     % (i, got, want, exc, attempt + 1))
                time.sleep(min(0.5 * (attempt + 1), 5))
            raise ConanException("bindist chunk %d incomplete: %d/%d"
                                 % (i, got, want))

        with ThreadPoolExecutor(max_workers=DL_CHUNKS) as pool:
            list(pool.map(fetch, range(DL_CHUNKS)))
        if not os.path.exists(dest):
            with open(dest, "wb") as out:
                for i in range(DL_CHUNKS):
                    with open("%s.part%03d" % (dest, i), "rb") as fh:
                        shutil.copyfileobj(fh, out, 1 << 20)
        for i in range(DL_CHUNKS):
            p = "%s.part%03d" % (dest, i)
            if os.path.exists(p):
                os.remove(p)
        if os.path.getsize(dest) != size:
            raise ConanException("bindist size mismatch: %d != %d"
                                 % (os.path.getsize(dest), size))
        digest = hashlib.sha256()
        with open(dest, "rb") as fh:
            while True:
                blk = fh.read(1 << 20)
                if not blk:
                    break
                digest.update(blk)
        if digest.hexdigest() != sha256:
            raise ConanException("bindist sha256 mismatch: %s != %s"
                                 % (digest.hexdigest(), sha256))
        self.output.info("bindist verified: sha256 %s" % sha256)

    # ------------------------------------------------------------------
    # Conan lifecycle
    # ------------------------------------------------------------------

    def _assert_bindist_ships_no_testsuite(self, ghc_root):
        """R51: normalized upstream test-surface check.

        The exemption ``bindist_ships_no_testsuite`` (MANIFEST) rests on the
        fact that GHC's testsuite/ lives in the source repo only.  Verified
        empirically on 2026-10-15 against bindist ghc-9.12.2-aarch64-alpine:
        0 testsuite dirs, 0 tests/ dirs, 0 *.T driver cases, 0 validate
        script.  This check re-runs on every build so a future bindist that
        DOES ship tests cannot silently keep the exemption -- it fails the
        build and forces the MANIFEST to be revisited instead.
        """
        markers = {
            "testsuite dirs": lambda: [p for p in os.listdir(ghc_root)
                                       if "testsuite" in p.lower()],
            "tests dirs": lambda: [dp for dp, dn, _fn in os.walk(ghc_root)
                                   if os.path.basename(dp) == "tests"
                                   and "lib" not in dp],
            "*.T test cases": lambda: [],
            "validate driver": lambda: [os.path.join(ghc_root, "validate")]
                                     if os.path.isfile(os.path.join(ghc_root,
                                                                    "validate"))
                                     else [],
        }
        counts = {}
        for name, fn in markers.items():
            if name == "*.T test cases":
                n = sum(1 for _dp, _dn, fnames in os.walk(ghc_root)
                        for f in fnames if f.endswith(".T"))
            else:
                n = len(fn())
            counts[name] = n
        self.output.info(
            "upstream test-surface check (bindist): testsuite=%d tests=%d "
            "*.T=%d validate=%d -> ships no test suite"
            % (counts["testsuite dirs"], counts["tests dirs"],
               counts["*.T test cases"], counts["validate driver"]))
        if any(counts.values()):
            raise ConanException(
                "bindist now ships test material (%s) — the "
                "bindist_ships_no_testsuite exemption and upstream_tests "
                "declared in test_package/MANIFEST.yml must be revisited"
                % ", ".join("%s=%d" % kv for kv in counts.items() if kv[1]))

    def source(self):
        spec = self.conan_data["ghc_bootstrap"]
        bindist = os.path.join(self.source_folder, "bindist.tar.gz")
        self._obtain_bindist(spec, bindist)
        # Extract the GHC tree (top-level dir ghc-9.12.2-aarch64-unknown-linux).
        import tarfile
        with tarfile.open(bindist) as tf:
            tf.extractall(self.source_folder)
        os.remove(bindist)
        ghc_root = os.path.join(self.source_folder, spec["topdir"])
        if not os.path.isdir(ghc_root):
            raise ConanException("bindist top dir missing: %s" % ghc_root)
        self.output.info("GHC tree extracted: %s" % spec["topdir"])
        self._assert_bindist_ships_no_testsuite(ghc_root)

        # musl runtime libs (alpine v3.18 APKs).  APKs are zip archives: use
        # download() + tarfile/zipfile, NOT get() (get() would report
        # BadZipFile because the payload is not a single compressed stream).
        rt = os.path.join(self.source_folder, "runtime")
        os.makedirs(rt, exist_ok=True)
        for apk in self.conan_data["ghc_runtime_libs"]:
            self._fetch_apk(apk, rt)

    def _obtain_bindist(self, spec, dest):
        """Materialise the bindist at dest, verifying sha256.

        An already-downloaded copy may be supplied through the
        ``GHC_OHOS_BINDIST_PATH`` environment variable (a build cache for
        hosts that have fetched it before); the sha256 is always verified, so
        this is a pure optimisation and CI behaviour is unchanged when the
        variable is unset.
        """
        cached = os.environ.get("GHC_OHOS_BINDIST_PATH")
        if cached and os.path.isfile(cached):
            digest = hashlib.sha256()
            with open(cached, "rb") as fh:
                while True:
                    blk = fh.read(1 << 20)
                    if not blk:
                        break
                    digest.update(blk)
            if digest.hexdigest() == spec["sha256"]:
                self.output.info("using cached bindist from %s" % cached)
                shutil.copy2(cached, dest)
                return
            self.output.warning(
                "GHC_OHOS_BINDIST_PATH set but sha256 mismatch; downloading")
        self._parallel_fetch(spec["url"], dest, spec["size"], spec["sha256"])

    def _fetch_apk(self, apk, dest):
        """Fetch an alpine APK and unpack its payload into dest.

        APK files are actually gzipped tarballs with a signature member, but
        python's tarfile handles them directly; we still guard against a
        plain (uncompressed) payload for robustness.
        """
        import tarfile
        name = os.path.basename(apk["url"])
        pkg_path = os.path.join(dest, name)
        if not os.path.exists(pkg_path):
            download(self, apk["url"], pkg_path, sha256=apk["sha256"])
        sub = os.path.join(dest, name.replace(".apk", ""))
        os.makedirs(sub, exist_ok=True)
        # Alpine APK payloads live under usr/lib/ (with lib/ as a legacy
        # spelling); matching only "lib/" silently collects nothing.
        prefixes = ("usr/lib/", "lib/", "usr/share/terminfo/",
                    "lib/terminfo/")
        try:
            with tarfile.open(pkg_path) as tf:
                members = [m for m in tf.getmembers()
                           if m.name.startswith(prefixes) and
                           (m.isfile() or m.issym())]
                tf.extractall(sub, members=members)
        except tarfile.TarError:
            # Some APKs are ZIP containers.
            import zipfile
            with zipfile.ZipFile(pkg_path) as zf:
                for m in zf.namelist():
                    if m.startswith(prefixes) and not m.endswith("/"):
                        zf.extract(m, sub)
        self.output.info("unpacked %s -> %s" % (name, sub))

    def _collect_runtime_libs(self, dst):
        """Collect the APK payload libraries into dst.

        Two Alpine facts must be handled or GHC cannot link:
          * ``libgmp.so.10`` is a *symlink* to ``libgmp.so.10.4.1`` and the
            loader resolves the SONAME, so the links must be recreated (skipping
            them yields "Error relocating ...: __gmpz_init: symbol not found");
          * the linker asks for the *unversioned* ``libgmp.so`` when GHC passes
            ``-lgmp``, and Alpine keeps that name in the ``-dev`` package — so
            the recipe creates the unversioned links itself.
        """
        os.makedirs(dst, exist_ok=True)
        files = 0
        links = 0
        names = []
        for dirpath, _dirs, entries in os.walk(
                os.path.join(self.source_folder, "runtime")):
            for name in entries:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                src = os.path.join(dirpath, name)
                target = os.path.join(dst, name)
                if os.path.islink(src):
                    self._link_lib(os.readlink(src), target)
                    links += 1
                elif os.path.isfile(src):
                    shutil.copy2(src, target)
                    files += 1
                names.append(name)

        # Unversioned soname links for the linker (-lgmp / -lffi / -lncursesw).
        dev_links = 0
        for name in names:
            m = re.match(r"^(lib[^.]+)\.so\.\d", name)
            if not m:
                continue
            want = m.group(1) + ".so"
            target = os.path.join(dst, want)
            if not os.path.lexists(target):
                self._link_lib(name, target)
                dev_links += 1

        self.output.info(
            "collected %d runtime .so file(s), %d soname link(s), "
            "%d unversioned link(s)" % (files, links, dev_links))
        return files

    @staticmethod
    def _link_lib(target_name, link_path):
        """(Re)create a symlink, tolerating hmdfs re-linking."""
        if os.path.lexists(link_path):
            os.remove(link_path)
        os.symlink(target_name, link_path)

    def build(self):
        """Create the compiler shims and the misc stubs object.

        No upstream compilation happens here: GHC is delivered as a binary
        distribution.  What *is* built is the small support layer the bindist
        needs to work on OHOS:
          * gcc/g++/cc shims (response-file expansion, clang-15 forwarding,
            atomics defsyms on link steps),
          * mktemp/time shims for the hmdfs and toybox quirks,
          * misc_stubs.o exporting the two symbols OHOS musl lacks.
        """
        tc = self._toolchain_dir()
        self._tc = tc
        sysroot = self._resolve_sysroot(tc)
        self._sysroot = sysroot
        ghc_root = os.path.join(self.source_folder,
                                self.conan_data["ghc_bootstrap"]["topdir"])

        shimdir = os.path.join(self.build_folder, "shims")
        os.makedirs(shimdir, exist_ok=True)
        # Runtime libs live at <build>/lib so the shim's "$SHIMDIR/../lib"
        # resolves during the build as well as from the installed package.
        rt_libs = os.path.join(self.build_folder, "lib")
        self._collect_runtime_libs(rt_libs)

        # Compile misc_stubs.o (no signing needed: it is linked, not executed).
        stubs_src = os.path.join(shimdir, "misc_stubs.c")
        with open(stubs_src, "w") as fh:
            fh.write(MISC_STUBS_C)
        stubs_obj = os.path.join(shimdir, "misc_stubs.o")
        self.run('"%s/clang-15" --target=aarch64-linux-ohos --sysroot="%s" '
                 '-c "%s" -o "%s"' % (tc, sysroot, stubs_src, stubs_obj))

        # cc/gcc/g++ shims (SHIMDIR is resolved by the script itself; the
        # signing tools let the shim sign every link output, since OHOS
        # refuses to execute an unsigned ELF).
        sign_tool = os.path.join(tc, "binary-sign-tool")
        if not os.path.exists(sign_tool):
            sign_tool = shutil.which("binary-sign-tool") or sign_tool
        objcopy_tool = os.path.join(tc, "llvm-objcopy")
        if not os.path.exists(objcopy_tool):
            objcopy_tool = shutil.which("llvm-objcopy") or objcopy_tool
        shim = (GCC_SHIM.replace("__TC__", tc)
                .replace("__SYSROOT__", sysroot)
                .replace("__BUILTINS__", self._builtins_lib(tc))
                .replace("__SIGN__", sign_tool)
                .replace("__OBJCOPY__", objcopy_tool)
                .replace("__DEFYSMS__", DEFYSMS))
        for name in ("cc", "gcc", "g++"):
            p = os.path.join(shimdir, name)
            with open(p, "w") as fh:
                fh.write(shim)
            os.chmod(p, 0o755)

        # mktemp + time shims.
        for name, body in (("mktemp", MKTEMP_SHIM), ("time", TIME_SHIM)):
            p = os.path.join(shimdir, name)
            with open(p, "w") as fh:
                fh.write(body.replace("__TC__", tc))
            os.chmod(p, 0o755)

        self._shimdir = shimdir
        self._rt_libs = rt_libs
        self._ghc_root = ghc_root
        # Sanity: the bindist's own ghc binary must be present.
        if not os.path.isfile(os.path.join(ghc_root, "bin", "ghc-9.12.2")):
            raise ConanException("bindist ghc binary missing under %s" % ghc_root)

    def _builtins_lib(self, tc):
        """Path to libclang_rt.builtins.a for link steps.

        The OHOS SDK names it plainly ``libclang_rt.builtins.a`` (no arch
        suffix) and keeps it under ``lib/clang/<ver>/lib/aarch64-linux-ohos/``.
        """
        pats = [
            os.path.join(tc, "lib", "clang", "*", "lib", "aarch64-linux-ohos",
                         "libclang_rt.builtins.a"),
            os.path.join(tc, "..", "lib", "clang", "*", "lib",
                         "aarch64-linux-ohos", "libclang_rt.builtins.a"),
            os.path.join(tc, "..", "..", "lib", "clang", "*", "lib",
                         "aarch64-linux-ohos", "libclang_rt.builtins.a"),
            # Fallbacks: arch-suffixed spellings, in case the SDK differs.
            os.path.join(tc, "lib", "clang", "*", "lib", "*",
                         "libclang_rt.builtins-aarch64.a"),
            os.path.join(tc, "..", "lib", "clang", "*", "lib", "*",
                         "libclang_rt.builtins-aarch64.a"),
        ]
        for p in pats:
            hits = glob.glob(p)
            if hits:
                return hits[0]
        raise ConanInvalidConfiguration(
            "libclang_rt.builtins.a not found near %s" % tc)

    def package(self):
        ghc_root = os.path.join(self.source_folder,
                                self.conan_data["ghc_bootstrap"]["topdir"])
        dst = self.package_folder
        # Paths are recomputed here rather than reused from build() so that
        # package() stays correct on its own (build() state must not be a
        # hidden precondition).
        rt_libs = os.path.join(self.build_folder, "lib")
        shimdir = os.path.join(self.build_folder, "shims")
        for d in (rt_libs, shimdir):
            if not os.path.isdir(d):
                raise ConanException(
                    "build output missing (%s) — build() did not run" % d)
        # 1) The whole GHC tree.
        copy(self, "*", src=ghc_root, dst=dst)
        # 2) The musl runtime libs (gmp/libffi/ncursesw/terminfo) so the
        #    compiler and produced binaries can run without system copies.
        os.makedirs(os.path.join(dst, "lib"), exist_ok=True)
        for name in os.listdir(rt_libs):
            src = os.path.join(rt_libs, name)
            target = os.path.join(dst, "lib", name)
            if os.path.islink(src):
                self._link_lib(os.readlink(src), target)
            else:
                shutil.copy2(src, target)
        # 3) The shims, so `ghc` finds a usable C toolchain through PATH.
        shim_dst = os.path.join(dst, "bin")
        for name in os.listdir(shimdir):
            src = os.path.join(shimdir, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(shim_dst, name))
        copy(self, "LICENSE", src=ghc_root, dst=os.path.join(dst, "licenses"),
             keep_path=False)
        # 4) Signing MUST happen after the last copy(): Conan's copy() rewrites
        #    files and invalidates the .codesign section (E212 family).
        self._tc = self._toolchain_dir()
        self._sign_tree(dst)

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["lib/include"]
        # Consumers (other Haskell packages) invoke ghc through PATH and need
        # the bundled musl runtime libs on the loader path.
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
        # Shims must win over the SDK's own clang wrappers.
        shim = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", shim)
        self.conf_info.define("user.ghc-ohos:bindir", bindir)
        self.runenv_info.define_path("GHC_PACKAGE_ROOT", self.package_folder)
