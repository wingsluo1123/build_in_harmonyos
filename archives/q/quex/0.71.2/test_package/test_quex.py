#!/usr/bin/env python3
"""Consumer check for the packaged quex 0.71.2 generator (R34 + L0c).

Standalone test source required by the CI L0c gate (test_package must hold
a .py/.sh/.c file besides conanfile.py). Executed by test_package/conanfile.py
via self.run(); each check really drives the installed ``quex`` binary and
prints one ``CHECK-OK: <name>`` line. The caller counts those lines from the
captured log file (single deterministic source) for HMBS_TEST_PACKAGE_RESULT.

Checks (4):
  1. ``quex --help`` exits 0 with non-empty output.
  2. ``quex --version`` exits 0 and reports 0.71.2.
  3. ``quex -i tiny.qx -o tiny_lexer --language C`` in a temp dir exits 0
     and produces a lexer tree (quex -o takes a bare analyzer identifier,
     so we cd into tmp first instead of passing an absolute path).
  4. The generated tree is non-empty and mentions NUMBER/IDENTIFIER.

Usage: test_quex.py <tiny.qx> [quex-exe-abs-path] [quex-share-dir]
  argv[2] (optional): absolute path of the packaged ``quex`` wrapper
    (resolved by conanfile.py from the dependency package_folder, so the
    driver never depends on PATH propagation through the nested
    self.run -> python -> subprocess chain).
  argv[3] (optional): absolute QUEX_PATH (share/quex) for QUEX_PATH export
    and for the python+quex-exe.py fallback.
"""

import os
import shutil
import subprocess
import sys
import tempfile

EXPECTED = "0.71.2"

QUEX_EXE = None
QUEX_SHARE = None


def resolve_quex(extra_exe=None, extra_share=None):
    """Resolve the generator entry point without relying on PATH alone."""
    global QUEX_EXE, QUEX_SHARE
    candidates = []
    if extra_exe:
        candidates.append(extra_exe)
    env_exe = os.environ.get("QUEX_EXE") or os.environ.get("QUEX_BIN")
    if env_exe:
        candidates.append(env_exe)
    which = shutil.which("quex")
    if which:
        candidates.append(which)
    candidates.append("quex")
    for cand in candidates:
        if cand and os.path.isfile(cand) and os.path.basename(cand) != "quex-exe.py":
            # Absolute wrapper path preferred; verify it is directly runnable.
            QUEX_EXE = cand
            break
    else:
        # No wrapper file found; fall back to the first candidate string so
        # the error message below shows what was searched.
        QUEX_EXE = candidates[0] if candidates else "quex"
    share = extra_share or os.environ.get("QUEX_PATH")
    if (not share or not os.path.isdir(share)) and QUEX_EXE not in ("quex", None):
        try:
            guess = os.path.normpath(
                os.path.join(os.path.dirname(os.path.abspath(QUEX_EXE)), "..", "share", "quex")
            )
            if os.path.isdir(guess):
                share = guess
        except OSError:
            pass
    if share and os.path.isdir(share):
        QUEX_SHARE = share
        try:
            os.environ["QUEX_PATH"] = share
        except OSError:
            pass


def _base_env():
    env = dict(os.environ)
    if QUEX_SHARE:
        env["QUEX_PATH"] = QUEX_SHARE
    return env


def run_quex(args):
    """Run the generator; fall back to python+quex-exe.py if wrapper missing."""
    env = _base_env()
    exe = QUEX_EXE or "quex"
    try:
        if exe.endswith("quex-exe.py"):
            py = sys.executable or "python3"
            proc = subprocess.run(
                [py, exe] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        else:
            proc = subprocess.run(
                [exe] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        return proc.returncode, proc.stdout
    except FileNotFoundError as exc:
        # Wrapper absolute path not runnable (PATH/shebang issue):
        # fall back to interpreter + quex-exe.py under QUEX_PATH/share.
        fallback = None
        for cand in (
            os.path.join(QUEX_SHARE or "", "quex-exe.py"),
            os.environ.get("QUEX_MAIN", ""),
        ):
            if cand and os.path.isfile(cand):
                fallback = cand
                break
        if fallback is not None:
            try:
                py = sys.executable or "python3"
                proc = subprocess.run(
                    [py, fallback] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                )
                return proc.returncode, proc.stdout
            except Exception as exc2:
                return 127, "fallback %s failed: %r (primary %r: %r, PATH=%r)" % (
                    fallback, exc2, exe, exc, os.environ.get("PATH", "")[-800:],
                )
        return 127, "spawn %r failed: %r (PATH=%r QUEX_PATH=%r)" % (
            exe, exc, os.environ.get("PATH", "")[-800:],
            os.environ.get("QUEX_PATH", ""),
        )
    except Exception as exc:
        return 127, "spawn %r failed: %r" % (exe, exc)


def main():
    if len(sys.argv) < 2:
        print("usage: test_quex.py <tiny.qx> [quex-exe] [quex-share]", flush=True)
        return 2
    tiny_qx = os.path.abspath(sys.argv[1])
    extra_exe = sys.argv[2] if len(sys.argv) > 2 else None
    extra_share = sys.argv[3] if len(sys.argv) > 3 else None
    resolve_quex(extra_exe, extra_share)
    if not os.path.isfile(tiny_qx):
        print("CHECK-FAIL: tiny.qx missing: %s" % tiny_qx, flush=True)
        return 1

    # 1. Entry point runnable.
    rc, out = run_quex(["--help"])
    if rc != 0:
        print("CHECK-FAIL: quex --help rc=%d" % rc, flush=True)
        print((out or "")[-2000:], flush=True)
        return 1
    if len((out or "").strip()) == 0:
        print("CHECK-FAIL: quex --help produced empty output", flush=True)
        return 1
    print("CHECK-OK: quex_help", flush=True)

    # 2. Version matches the adapted release.
    rc, out = run_quex(["--version"])
    if rc != 0:
        print("CHECK-FAIL: quex --version rc=%d" % rc, flush=True)
        print((out or "")[-2000:], flush=True)
        return 1
    if EXPECTED not in (out or ""):
        print("CHECK-FAIL: quex --version misses %s: %r" % (EXPECTED, (out or "")[-500:]), flush=True)
        return 1
    print("CHECK-OK: quex_version", flush=True)

    # 3. Generate a C lexer from the minimal spec into a temp dir.
    tmp = tempfile.mkdtemp(prefix="quex-test-")
    try:
        env = _base_env()
        exe = QUEX_EXE or "quex"
        if exe.endswith("quex-exe.py"):
            cmd = [sys.executable or "python3", exe, "-i", tiny_qx,
                   "-o", "tiny_lexer", "--language", "C"]
        else:
            cmd = [exe, "-i", tiny_qx, "-o", "tiny_lexer", "--language", "C"]
        try:
            proc = subprocess.run(
                cmd,
                cwd=tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        except FileNotFoundError:
            rc2, out2 = run_quex(["-i", tiny_qx, "-o", "tiny_lexer", "--language", "C"])
            # run_quex does not take cwd; re-run generation inline with fallback
            # interpreter entry under tmp cwd for an equivalent result.
            fb = None
            for cand in (os.path.join(QUEX_SHARE or "", "quex-exe.py"),):
                if cand and os.path.isfile(cand):
                    fb = cand
                    break
            if fb is None:
                print("CHECK-FAIL: quex generate spawn failed: %r" % (out2[-1500:],), flush=True)
                return 1
            proc = subprocess.run(
                [sys.executable or "python3", fb, "-i", tiny_qx,
                 "-o", "tiny_lexer", "--language", "C"],
                cwd=tmp,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        if proc.returncode != 0:
            print("CHECK-FAIL: quex generate rc=%d" % proc.returncode, flush=True)
            print((proc.stdout or "")[-3000:], flush=True)
            return 1
        out_dir = os.path.join(tmp, "tiny_lexer")
        if not os.path.isdir(out_dir):
            print("CHECK-FAIL: tiny_lexer dir missing in %s" % tmp, flush=True)
            return 1
        found = []
        for root, _dirs, files in os.walk(out_dir):
            for fn in files:
                found.append(os.path.join(root, fn))
        if not found:
            print("CHECK-FAIL: quex generated no files in %s" % out_dir, flush=True)
            return 1
        print("CHECK-OK: quex_generate", flush=True)

        # 4. Generated tree is non-empty and carries our tokens.
        blob = ""
        for path in found:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    blob += handle.read() + "\n"
            except OSError:
                continue
        if len(blob.strip()) == 0:
            print("CHECK-FAIL: generated files are all empty", flush=True)
            return 1
        if "NUMBER" not in blob or "IDENTIFIER" not in blob:
            print("CHECK-FAIL: generated lexer misses NUMBER/IDENTIFIER tokens", flush=True)
            return 1
        print("CHECK-OK: lexer_content", flush=True)
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except OSError:
            pass

    print("quex consumer checks: 4/4 passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
