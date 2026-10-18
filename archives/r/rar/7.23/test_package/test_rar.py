#!/usr/bin/env python3
"""Consumer + HarmonyOS-specific tests for rar 7.23 (RARLAB UnRAR).

Assertion inventory (counting unit: independent check items):

  A. libunrar consumer API tests (test.cpp, compiled by CMake):
       A1 RARGetDllVersion() == RAR_DLL_VERSION
       A2 opening a nonexistent archive fails gracefully (NULL + error)
       A3 fixture lists hello.txt with the expected unpacked size
       A4 RAR_TEST extraction of hello.txt passes the integrity check

  B. CLI functional tests against the packaged `unrar` binary:
       B1 `unrar t plain.rar` exits 0 and reports "All OK"
       B2 `unrar x plain.rar` extracts byte-identical content
       B3 wrong password (`-pWrongPass`) fails and extracts nothing

  C. HarmonyOS-specific (鸿蒙特有) assertions:
       C1 unrar ELF machine is AArch64 (the OHOS PC target)
       C2 PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1)
       C3 the binary carries an OHOS code signature (unsigned ELF cannot
          execve on HarmonyOS, EACCES errno 13)
       C4 password delivered via stdin extracts the encrypted fixture —
          exercises the OHOS adaptation in consio.cpp (musl libc has no
          getpass(); the patch reads the password with fgets() instead)

Fixtures are stored base64-encoded under fixtures/ (binary archives are not
allowed in the source repo) and decoded into a temp dir at test time.

Input -> expectation table (self-check per skill section 6.1):
  plain.rar     = {hello.txt: EXPECTED_HELLO, subdir/nested.txt: EXPECTED_NESTED}
  encrypted.rar = {hello.txt: EXPECTED_HELLO}, data-encrypted, pw=FIXTURE_PASSWORD
  Both fixtures were produced by the official RAR 7.23 (rarmacos-arm-723).
"""

import base64
import os
import struct
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0

OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"
EM_AARCH64 = 183

FIXTURE_PASSWORD = "ohos-rar23"
EXPECTED_HELLO = (b"Hello from HarmonyOS unrar test fixture.\n"
                  b"This file verifies real RAR5 decompression on OHOS.\n")
EXPECTED_NESTED = b"nested file content line1\nline2\n"


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"[ok] {name}{(': ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"[fail] {name}{(': ' + detail) if detail else ''}",
              file=sys.stderr)
    return ok


def elfinfo(path):
    """Return (e_machine, interp) or (None, None) when unreadable."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, None
    if data[:4] != b"\x7fELF":
        return None, None
    e_machine = struct.unpack_from("<H", data, 18)[0]
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    interp = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if struct.unpack_from("<I", data, off)[0] == 3:  # PT_INTERP
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            interp = (data[p_offset:p_offset + p_filesz]
                      .rstrip(b"\x00").decode("utf-8", "replace"))
            break
    return e_machine, interp


def decode_fixtures(work):
    here = os.path.dirname(os.path.abspath(__file__))
    out = {}
    for key in ("plain", "encrypted"):
        with open(os.path.join(here, "fixtures", f"{key}_rar.b64"),
                  "rb") as fh:
            blob = base64.b64decode(fh.read())
        path = os.path.join(work, f"{key}.rar")
        with open(path, "wb") as fh:
            fh.write(blob)
        if blob[:7] != b"Rar!\x1a\x07\x01":
            raise AssertionError(f"{key}.rar fixture magic mismatch")
        out[key] = path
    return out


def run_cli(exe, args, cwd, stdin_text=None):
    try:
        return subprocess.run([exe] + args, cwd=cwd, input=stdin_text,
                              capture_output=True, text=True, timeout=60)
    except PermissionError:
        # OHOS EACCES 诊断（不参与判定，仅留证）：区分未签名与 HMDFS 丢执行位
        try:
            st = os.stat(exe)
            with open(exe, "rb") as fh:
                payload = fh.read()
            print(f"[diag] EACCES on {exe}: mode={oct(st.st_mode)} "
                  f"size={st.st_size} "
                  f"codesign={b'codesign' in payload or b'.note.ohos' in payload}",
                  file=sys.stderr)
        except OSError as e:
            print(f"[diag] EACCES on {exe}, stat failed: {e}", file=sys.stderr)
        raise


def main():
    package_folder = os.environ.get("PACKAGE_FOLDER", "")
    test_bin = os.environ.get("TEST_BIN", "")
    exe = os.path.join(package_folder, "bin", "unrar")
    if not os.path.isfile(exe):
        raise AssertionError(f"Missing unrar executable: {exe}")
    if not os.path.isfile(test_bin):
        raise AssertionError(f"Missing libunrar consumer binary: {test_bin}")

    with tempfile.TemporaryDirectory(prefix="rar-tp-") as work:
        fixtures = decode_fixtures(work)

        # ── A. libunrar consumer API (test.cpp) ──
        print("== libunrar consumer API assertions ==")
        api = subprocess.run(
            [test_bin, fixtures["plain"], str(len(EXPECTED_HELLO))],
            capture_output=True, text=True, timeout=60)
        sys.stdout.write(api.stdout)
        if api.stderr:
            sys.stderr.write(api.stderr)
        for token in ("A1", "A2", "A3", "A4"):
            check(f"{token} (see consumer output above)",
                  api.returncode == 0 and f"[ok] {token}" in api.stdout,
                  f"rc={api.returncode}")

        # ── B. CLI functional tests ──
        print("== CLI functional assertions ==")
        t_run = run_cli(exe, ["t", fixtures["plain"]], cwd=work)
        check("B1: `unrar t plain.rar` exits 0 and reports All OK",
              t_run.returncode == 0 and "All OK" in t_run.stdout,
              f"rc={t_run.returncode}")

        out_dir = os.path.join(work, "out-plain")
        os.makedirs(out_dir)
        x_run = run_cli(exe, ["x", "-o+", fixtures["plain"]], cwd=out_dir)
        hello_path = os.path.join(out_dir, "hello.txt")
        nested_path = os.path.join(out_dir, "subdir", "nested.txt")
        hello_ok = (os.path.isfile(hello_path)
                    and open(hello_path, "rb").read() == EXPECTED_HELLO)
        nested_ok = (os.path.isfile(nested_path)
                     and open(nested_path, "rb").read() == EXPECTED_NESTED)
        check("B2: `unrar x plain.rar` extracts byte-identical files",
              x_run.returncode == 0 and hello_ok and nested_ok,
              f"rc={x_run.returncode}")

        neg_dir = os.path.join(work, "out-neg")
        os.makedirs(neg_dir)
        neg = run_cli(exe, ["x", "-o+", "-pWrongPass", fixtures["encrypted"]],
                      cwd=neg_dir)
        check("B3: wrong password fails and extracts nothing",
              neg.returncode != 0
              and not os.path.exists(os.path.join(neg_dir, "hello.txt")),
              f"rc={neg.returncode} "
              f"err={neg.stderr.strip().splitlines()[-1] if neg.stderr.strip() else ''}")

        # ── C. 鸿蒙特有测试 (HarmonyOS-specific) ──
        print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
        e_machine, interp = elfinfo(exe)
        check("C1: ELF machine is AArch64 (EM_AARCH64=183)",
              e_machine == EM_AARCH64, f"e_machine={e_machine}")
        check(f"C2: PT_INTERP is the OHOS musl loader ({OHOS_MUSL_LOADER})",
              interp is not None and OHOS_MUSL_LOADER in interp,
              f"interp={interp}")
        with open(exe, "rb") as fh:
            payload = fh.read()
        check("C3: OHOS code signature present (unsigned ELF cannot execve)",
              b"codesign" in payload or b".note.ohos" in payload)

        pw_dir = os.path.join(work, "out-pw")
        os.makedirs(pw_dir)
        pw = run_cli(exe, ["x", "-o+", fixtures["encrypted"]], cwd=pw_dir,
                     stdin_text=FIXTURE_PASSWORD + "\n")
        pw_hello = os.path.join(pw_dir, "hello.txt")
        pw_ok = (os.path.isfile(pw_hello)
                 and open(pw_hello, "rb").read() == EXPECTED_HELLO)
        check("C4: password via stdin extracts encrypted fixture "
              "(consio.cpp getpass->fgets OHOS adaptation)",
              pw.returncode == 0 and pw_ok,
              f"rc={pw.returncode}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("rar test_package OK: libunrar API + CLI + HarmonyOS traits verified")


if __name__ == "__main__":
    sys.exit(main())
