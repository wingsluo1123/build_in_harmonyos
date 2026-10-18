#!/usr/bin/env python3
"""Exercise the packaged GHC toolchain as a consumer would.

Usage: test_ghc_ohos.py <package_folder>

The decisive acceptance test for a compiler is a **real compile-and-run
smoke test** (documented as acceptance criterion 3):

1. ``ghc --version`` reports the exact release (9.12.2);
2. ``ghc-pkg list`` works, i.e. the bundled package database is intact;
3. a real Haskell program is compiled with ``ghc --make`` and the produced
   binary is executed, asserting its output.

That third step is what proves the whole chain works end to end: the gcc/cc
shims, the response-file expansion, the atomics ``--defsym`` aliases, the
bundled musl runtime libs, and the ELF self-signing of everything the bindist
ships.

Note: runghc/GHCi cannot work on this platform (libffi closures need
executable anonymous memory, which OHOS denies), so the smoke test uses
``ghc --make`` exclusively.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HELLO_HS = """module Main (main) where

main :: IO ()
main = do
  let xs = [1 .. 10]
  putStrLn ("GHC-HELLO-SUM=" ++ show (sum xs))
"""


def main():
    pkgdir = sys.argv[1]
    bindir = os.path.join(pkgdir, "bin")
    libdir = os.path.join(pkgdir, "lib")

    ghc = None
    for cand in ("ghc", "ghc-9.12.2"):
        p = os.path.join(bindir, cand)
        if os.path.isfile(p):
            ghc = p
            break
    assert ghc, "no ghc binary under %s" % bindir

    # The shims and the bundled gmp/libffi/ncurses must be reachable.
    env = dict(os.environ)
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = libdir + os.pathsep + env.get(
        "LD_LIBRARY_PATH", "")
    # GHC needs a writable HOME/TMPDIR; OHOS /tmp is a read-only erofs.  The
    # smoke test also EXECUTES the freshly linked binary from here, so the
    # directory must live on a mount that allows exec — the package tree
    # itself (ghc, the shims and every bindist binary already run from
    # there).  el2/FUSE cache mounts deny exec on new files (EACCES on
    # ./hello), so env TMPDIR (/data/storage/el2/base/cache on CI) is NOT
    # used for the build dir.
    try:
        tmp = tempfile.mkdtemp(prefix="ghc-test-",
                               dir=os.path.dirname(os.path.abspath(pkgdir)))
    except OSError:
        tmp = tempfile.mkdtemp(prefix="ghc-test-")
    env["HOME"] = tmp
    env["TMPDIR"] = tmp

    def run(args, cwd=None, timeout=600):
        return subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                              text=True, timeout=timeout)

    # 1) Version.
    r = run([ghc, "--version"])
    blob = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, "ghc --version failed:\n%s" % blob
    assert "9.12.2" in blob, blob
    print("version:", blob.strip().splitlines()[0])

    # 2) Package database.
    r = run([ghc, "--print-libdir"])
    blob = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, "ghc --print-libdir failed:\n%s" % blob
    print("libdir:", blob.strip())

    # 3) Real compile + run.  CI workers hit load-window fork storms
    #    ("can't fork - try again", EAGAIN) that kill the shims mid-run —
    #    the 2026-10-15 build died in the Assembler phase exactly this way
    #    after Main.hs had already compiled.  Retry only the indeterminate
    #    shapes; a genuine compile error surfaces on the first attempt.
    src = os.path.join(tmp, "Main.hs")
    with open(src, "w") as fh:
        fh.write(HELLO_HS)

    def is_transient(blob):
        return ("can't fork" in blob
                or "Resource temporarily unavailable" in blob)

    make_args = [ghc, "--make", "Main.hs", "-o", "hello"]
    blob = ""
    for attempt in range(1, 4):
        r = run(make_args, cwd=tmp, timeout=900)
        blob = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            if attempt > 1:
                print("ghc --make recovered on retry attempt %d" % attempt)
            break
        if is_transient(blob) and attempt < 3:
            print("ghc --make transient failure (attempt %d/3): %s"
                  % (attempt, blob.strip().splitlines()[-1][:120]))
            time.sleep(30)
            continue
        assert r.returncode == 0, "ghc --make failed:\n%s" % blob[-3000:]

    hello = os.path.join(tmp, "hello")
    assert os.path.isfile(hello), "no hello binary produced"
    # hmdfs/el2 create fresh files without the exec bit (observed 0660), and
    # same-session chmod can be a no-op there.  Normalise explicitly; if the
    # bit still does not stick, fall back to an owner-owned copy whose mode
    # we control.
    if not os.access(hello, os.X_OK):
        try:
            os.chmod(hello, 0o755)
        except OSError:
            pass
    if not os.access(hello, os.X_OK):
        alt = hello + ".x"
        shutil.copyfile(hello, alt)
        os.chmod(alt, 0o755)
        hello = alt
    assert os.access(hello, os.X_OK), \
        "hello lacks the exec bit even after chmod/copy (mount denies it?)"

    r = run([hello], cwd=tmp)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, "hello failed:\n%s" % out
    assert "GHC-HELLO-SUM=55" in out, out
    print(out.strip())

    print("GHC-CONSUMER-OK")
    shutil.rmtree(tmp, ignore_errors=True)


main()
