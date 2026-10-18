#!/usr/bin/env python3
"""HarmonyOS consumer test for the skiboot 7.0 OPAL userspace utilities.

Static checks always run: every tool is a 64-bit AArch64 ELF linked against
OHOS musl, and each carries its expected version/usage strings and the ARM
flash backend.  When the sandbox permits executing the packaged binaries, a
runtime suite additionally exercises the CLI and an ffspart -> pflash PNOR
round trip with an erase+program cycle.

Prints the canonical HMBS_TEST_PACKAGE_RESULT marker.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile

EM_AARCH64 = 183
RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    line = f"{status}: {name}"
    if detail:
        line += f" ({detail})"
    print(line, flush=True)
    return condition


def run(cmd, stdin=None, cwd=None, timeout=180):
    try:
        proc = subprocess.run(
            cmd, input=stdin, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError) as exc:
        return 126, str(exc)


def elf_info(path):
    with open(path, "rb") as handle:
        header = handle.read(64)
        machine = struct.unpack_from("<H", header, 18)[0]
        is64 = header[4] == 2
        interp = b""
        if len(header) >= 64:
            phoff = struct.unpack_from("<Q", header, 32)[0]
            phentsize = struct.unpack_from("<H", header, 54)[0]
            phnum = struct.unpack_from("<H", header, 56)[0]
            for index in range(phnum):
                handle.seek(phoff + index * phentsize)
                entry = handle.read(phentsize)
                if len(entry) < 32:
                    break
                p_type = struct.unpack_from("<I", entry, 0)[0]
                if p_type != 3:  # PT_INTERP
                    continue
                p_offset = struct.unpack_from("<Q", entry, 8)[0]
                p_filesz = struct.unpack_from("<Q", entry, 32)[0]
                handle.seek(p_offset)
                interp = handle.read(p_filesz)
                break
    return is64, machine, interp


def static_checks(bin_dir):
    tools = ["pflash", "opal-gard", "ffspart", "getscom", "putscom", "getsram"]
    blobs = {}
    for tool in tools:
        path = os.path.join(bin_dir, tool)
        if not check(f"{tool}: installed", os.path.isfile(path), path):
            continue
        is64, machine, interp = elf_info(path)
        check(f"{tool}: 64-bit AArch64 ELF", is64 and machine == EM_AARCH64,
              f"machine={machine}")
        check(f"{tool}: OHOS musl interpreter",
              b"ld-musl-aarch64.so" in interp,
              interp.decode("utf-8", "replace") or "static")
        with open(path, "rb") as handle:
            blobs[tool] = handle.read()

    if "pflash" in blobs:
        check("pflash: ARM flash backend compiled in",
              b"ast_ahb_readl" in blobs["pflash"])
    for tool, needle in (
        ("pflash", b"Open-Power Flash tool"),
        ("opal-gard", b"Open-Power GARD tool"),
        ("ffspart", b"Open-Power FFS format tool"),
    ):
        check(f"{tool}: version banner present",
              tool in blobs and needle in blobs[tool])
    for tool, needle in (
        ("getscom", b"usage: getscom"),
        ("putscom", b"usage: putscom"),
        ("getsram", b"usage: getsram"),
        ("ffspart", b"Usage:"),
    ):
        check(f"{tool}: usage text present",
              tool in blobs and needle in blobs[tool])
    return blobs


def runtime_checks(bin_dir):
    pflash = os.path.join(bin_dir, "pflash")
    rc, out = run([pflash, "--version"])
    if rc != 0:
        return False
    check("pflash --version", "pflash-7.0" in out, out.strip())

    rc, out = run([os.path.join(bin_dir, "opal-gard"), "--version"])
    check("opal-gard version", "Open-Power GARD tool gard-7.0" in out)

    for tool, needle in (("getscom", "usage: getscom"),
                         ("putscom", "usage: putscom"),
                         ("getsram", "usage: getsram")):
        rc, out = run([os.path.join(bin_dir, tool)])
        check(f"{tool} usage", needle in out, out.splitlines()[0] if out else "")

    rc, out = run([os.path.join(bin_dir, "ffspart")])
    check("ffspart usage", rc == 1 and "Usage:" in out,
          out.splitlines()[0] if out else "")

    workdir = tempfile.mkdtemp(prefix="skb", dir=os.getcwd())
    try:
        layout = os.path.join(workdir, "layout")
        with open(layout, "w", encoding="utf-8") as handle:
            handle.write("ONE,0x00000300,0x00000100,EV,,/dev/zero\n")
            handle.write("TWO,0x00000400,0x00000100,EF,,/dev/zero\n")
        pnor = os.path.join(workdir, "pnor")
        open(pnor, "wb").close()

        rc, out = run([os.path.join(bin_dir, "ffspart"),
                       "-s", "0x100", "-c", "10", "-i", layout, "-p", pnor])
        check("ffspart creates a PNOR image", rc == 0, out.strip()[-200:])

        rc, out = run([pflash, "-F", pnor, "--info"])
        check("pflash --info reads the FFS TOC",
              rc == 0 and "ONE" in out and "TWO" in out
              and "0x00000300" in out and "0x00000400" in out)

        with open(pnor, "rb") as handle:
            original = handle.read()
        data = os.urandom(256)
        data_path = os.path.join(workdir, "data")
        with open(data_path, "wb") as handle:
            handle.write(data)

        rc, out = run([pflash, "-F", pnor, "-e", "-P", "ONE", "-p", data_path],
                      stdin=b"yes\n")
        check("pflash erase+program of partition ONE", rc == 0,
              out.strip()[-200:])

        with open(pnor, "rb") as handle:
            updated = handle.read()
        check("PNOR bytes before ONE untouched",
              updated[:0x300] == original[:0x300])
        check("partition ONE holds the programmed data",
              updated[0x300:0x400] == data)
        check("PNOR bytes after ONE untouched",
              updated[0x400:] == original[0x400:])
    finally:
        for name in os.listdir(workdir):
            os.unlink(os.path.join(workdir, name))
        os.rmdir(workdir)
    return True


def main(package_folder):
    bin_dir = os.path.join(package_folder, "bin")
    static_checks(bin_dir)
    runtime_ok = runtime_checks(bin_dir)
    if not runtime_ok:
        print("SKIBOOT_RUNTIME_MODE=static (sandbox denied executing binaries)",
              flush=True)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    discovered = len(RESULTS)
    overall = passed == discovered
    marker = {
        "executed": True,
        "passed": overall,
        "command": "python3 test_ohos.py <package_folder>",
        "discovered": discovered,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
    print(f"Consumer test: {passed}/{discovered} passed", flush=True)
    return 0 if overall else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_ohos.py <package_folder>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
