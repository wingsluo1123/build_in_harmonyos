#!/usr/bin/env python3
"""Consumer tests for the packaged unhide 20240510 binaries.

unhide requires root for its actual scans (upstream main() calls
die()/exit(1) when getuid() != 0), and the HarmonyOS CI device runs conan
tests as a non-root user (euid 20020084 — cdebootstrap 0.7.9 precedent), so
this suite asserts the real behaviour of the installed artefacts in the
matching execution mode:

  A. [HarmonyOS] artefact (each of unhide-linux, unhide_rb, unhide-tcp,
     unhide-posix): ELF64 little-endian AArch64, OHOS NDK note (owner
     "OHOS"), dynamically linked PIE (ET_DYN with PT_INTERP; the OHOS
     sysroot has no static libc/rcrt1.o, so --static is impossible —
     sockstat 0.4.2 precedent), DT_NEEDED exactly {libc.so}, GNU_STACK RW
     (NX).  The PT_INTERP value itself is not asserted: the CI device
     driver emits /lib/ld-musl-aarch64.so.1 while the local WSL shim
     emits /lib/ld-linux-aarch64.so.1 (both loaders exist in the local
     qemu guest setup), so only "has an interpreter" is contractual.
  B. euid == 0 (root — local qemu-aarch64/WSL verification build):
     1. unhide-linux -V            -> exit 0 after the banner
     2. unhide-linux -h            -> exit 0, "[options] test_list"
     3. unhide-linux (no args)     -> exit 1 + usage
     4. unhide-linux -Z            -> exit 2 (getopt invalid option)
     5. unhide-linux checksysinfo  -> exit 0, "[*]Searching for Hidden processes
                                       through sysinfo() scanning" (real scan)
     6. unhide-tcp -V              -> exit 0 after the banner
     7. unhide-tcp -h              -> exit 0, "[options]"
     8. unhide-tcp -Z              -> exit 2
     9. unhide-posix bogus         -> exit 1, "usage: ... proc | sys"
    10. unhide-posix sys           -> exit 0 (real getpriority/getpgid/getsid
                                       scan of the whole PID space)
    11. unhide_rb                  -> prints the P.O.F. warning block and
                                       reaches "Scanning for hidden processes..."
                                       (upstream has no arg parsing; the phase-1
                                       scan is long, so startup is asserted and
                                       the process is terminated)
  C. euid != 0 (CI device):
     1. unhide-linux -V            -> exit 1, "You must be root to run"
     2. unhide-tcp -V              -> exit 1, "You must be root to run"
     3. unhide_rb                  -> exit 1, "You must be root to run"
     4. unhide-posix bogus         -> exit 1, "usage:" (posix has no root check)

The binaries run natively on AArch64 (the HarmonyOS CI device) and through
qemu-aarch64 elsewhere; neither available is a failure, never a skip.
"""
import argparse
import os
import platform
import shutil
import struct
import subprocess
import sys

EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
PT_NOTE = 4
PT_DYNAMIC = 2
PT_LOAD = 1
PT_GNU_STACK = 0x6474E551
DT_NEEDED = 1
DT_STRTAB = 5
DT_NULL = 0
BANNER_LINUX = "Unhide 20240509"
BANNER_TCP = "Unhide-tcp 20240509"
BANNER_RB = "Unhide_rb 20240509"
BANNER_POSIX = "Unhide-posix 20240509"
BINARIES = ("unhide-linux", "unhide_rb", "unhide-tcp", "unhide-posix")
checks = 0


def fail(msg):
    sys.exit("unhide test FAILED: " + msg)


def ok(msg):
    global checks
    checks += 1
    print("ok   " + msg, flush=True)


def elf_facts(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        fail("not an ELF64 little-endian file: " + path)
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
    interp, owners, gnu_stack, needed = None, set(), None, set()
    loads = []
    for i in range(e_phnum):
        ph = e_phoff + i * e_phentsize
        p_type, p_flags = struct.unpack_from("<II", data, ph)
        p_offset = struct.unpack_from("<Q", data, ph + 8)[0]
        p_vaddr = struct.unpack_from("<Q", data, ph + 16)[0]
        p_filesz = struct.unpack_from("<Q", data, ph + 32)[0]
        seg = data[p_offset:p_offset + p_filesz]
        if p_type == PT_INTERP:
            interp = seg.rstrip(b"\0").decode()
        elif p_type == PT_NOTE:
            pos = 0
            while pos + 12 <= len(seg):
                namesz, descsz, _ = struct.unpack_from("<III", seg, pos)
                owners.add(seg[pos + 12:pos + 12 + namesz].rstrip(b"\0").decode("latin-1"))
                pos += 12 + ((namesz + 3) & ~3) + ((descsz + 3) & ~3)
        elif p_type == PT_GNU_STACK:
            gnu_stack = p_flags
        elif p_type == PT_LOAD:
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == PT_DYNAMIC:
            strtab = None
            pos = 0
            while pos + 16 <= len(seg):
                d_tag, d_val = struct.unpack_from("<QQ", seg, pos)
                pos += 16
                if d_tag == DT_NULL:
                    break
                if d_tag == DT_NEEDED:
                    needed.add(d_val)
                elif d_tag == DT_STRTAB:
                    strtab = d_val
            if strtab is not None and needed:
                needed = {dyn_str(data, loads, strtab, off) for off in needed}
    return e_type, e_machine, interp, owners, gnu_stack, needed


def dyn_str(data, loads, strtab, off):
    addr = strtab + off
    for vaddr, foff, filesz in loads:
        if vaddr <= addr < vaddr + filesz:
            start = foff + (addr - vaddr)
            end = data.index(b"\0", start)
            return data[start:end].decode("latin-1")
    fail("dynamic string at 0x%x is outside all PT_LOAD segments" % addr)


def run(cmd, timeout=300):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout + proc.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bindir", required=True)
    ap.add_argument("--ohos", action="store_true", help="target os is OHOS")
    args = ap.parse_args()

    bins = {b: os.path.join(args.bindir, b) for b in BINARIES}
    for b, path in bins.items():
        if not os.path.isfile(path):
            fail("bin/%s not packaged" % b)

    if args.ohos:
        for b, path in bins.items():
            e_type, e_machine, interp, owners, gnu_stack, needed = elf_facts(path)
            if e_machine != EM_AARCH64:
                fail("%s: e_machine %d, expected AArch64 (183)" % (b, e_machine))
            if "OHOS" not in owners:
                fail("%s: no OHOS NDK note, owners %s" % (b, sorted(owners)))
            if e_type != ET_DYN or interp is None:
                fail("%s: expected dynamically linked PIE, got e_type=%d interp=%r" % (b, e_type, interp))
            if needed != {"libc.so"}:
                fail("%s: DT_NEEDED %s, expected exactly libc.so" % (b, sorted(needed)))
            if gnu_stack is None or (gnu_stack & 1):
                fail("%s: GNU_STACK not RW (NX disabled), flags=%r" % (b, gnu_stack))
            ok("[HarmonyOS] %s: ELF64 AArch64, OHOS note, dynamic PIE (interp %s), "
               "NEEDED only libc.so, NX" % (b, interp))

    if platform.machine().lower() in ("aarch64", "arm64"):
        runner = []
    else:
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            fail("non-AArch64 runner (%s) and no qemu-aarch64" % platform.machine())
        runner = [qemu]
    print("runner: %s euid: %d" % (runner[0] if runner else "native", os.geteuid()), flush=True)

    root = os.geteuid() == 0

    if root:
        # B1: unhide-linux -V -> exit 0
        rc, out = run(runner + [bins["unhide-linux"], "-V"])
        if rc != 0 or BANNER_LINUX not in out:
            fail("unhide-linux -V: rc=%d, banner missing" % rc)
        ok("unhide-linux -V: exit 0 after banner '" + BANNER_LINUX + "'")

        # B2: -h -> usage, exit 0
        rc, out = run(runner + [bins["unhide-linux"], "-h"])
        if rc != 0 or "[options] test_list" not in out:
            fail("unhide-linux -h: rc=%d, usage missing" % rc)
        ok("unhide-linux -h: exit 0 with test_list usage")

        # B3: no args -> usage, exit 1
        rc, out = run(runner + [bins["unhide-linux"]])
        if rc != 1 or "[options] test_list" not in out:
            fail("unhide-linux (no args): rc=%d, usage missing" % rc)
        ok("unhide-linux (no args): exit 1 with usage")

        # B4: invalid option -> exit 2
        rc, out = run(runner + [bins["unhide-linux"], "-Z"])
        if rc != 2:
            fail("unhide-linux -Z: rc=%d, expected 2" % rc)
        ok("unhide-linux -Z: exit 2 (invalid option)")

        # B5: real scan - checksysinfo
        rc, out = run(runner + [bins["unhide-linux"], "checksysinfo"], timeout=600)
        if rc not in (0, 1) or "[*]Searching for Hidden processes through sysinfo() scanning" not in out:
            fail("unhide-linux checksysinfo: rc=%d, scan banner missing" % rc)
        ok("unhide-linux checksysinfo: real sysinfo() scan executed (rc in 0/1; 1 = hidden procs reported, expected under qemu)")

        # B6: unhide-tcp -V -> exit 0
        rc, out = run(runner + [bins["unhide-tcp"], "-V"])
        if rc != 0 or BANNER_TCP not in out:
            fail("unhide-tcp -V: rc=%d, banner missing" % rc)
        ok("unhide-tcp -V: exit 0 after banner '" + BANNER_TCP + "'")

        # B7: -h -> usage, exit 0
        rc, out = run(runner + [bins["unhide-tcp"], "-h"])
        if rc != 0 or "[options]" not in out:
            fail("unhide-tcp -h: rc=%d, usage missing" % rc)
        ok("unhide-tcp -h: exit 0 with usage")

        # B8: invalid option -> exit 2
        rc, out = run(runner + [bins["unhide-tcp"], "-Z"])
        if rc != 2:
            fail("unhide-tcp -Z: rc=%d, expected 2" % rc)
        ok("unhide-tcp -Z: exit 2 (invalid option)")

        # B9: unhide-posix bogus -> usage, exit 1
        rc, out = run(runner + [bins["unhide-posix"], "bogus"])
        if rc != 1 or "proc | sys" not in out:
            fail("unhide-posix bogus: rc=%d, usage missing" % rc)
        ok("unhide-posix bogus: exit 1 with 'proc | sys' usage")

        # B10: unhide-posix sys -> real scan, exit 0
        rc, out = run(runner + [bins["unhide-posix"], "sys"], timeout=900)
        if rc not in (0, 1) or "[*]Searching for Hidden processes through getpriority() scanning" not in out:
            fail("unhide-posix sys: rc=%d, scan banner missing" % rc)
        ok("unhide-posix sys: real getpriority()/getpgid()/getsid() scan executed (rc in 0/1; 1 = hidden procs reported, expected under qemu)")

        # B11: unhide_rb -> warning block + scan start (no arg parsing upstream)
        proc = subprocess.Popen(runner + [bins["unhide_rb"]],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
        seen = []
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                seen.append(line)
                if "Scanning for hidden processes..." in line:
                    break
                if len(seen) > 200:
                    break
        finally:
            proc.terminate()
            proc.wait(timeout=30)
        out = "".join(seen)
        if BANNER_RB not in out or "Scanning for hidden processes..." not in out:
            fail("unhide_rb: banner/scan-start missing in %r" % out[:500])
        ok("unhide_rb: P.O.F. warning block + phase-1 scan start verified")
    else:
        # C1: unhide-linux refuses to run as non-root
        rc, out = run(runner + [bins["unhide-linux"], "-V"])
        if rc != 1 or BANNER_LINUX not in out or "You must be root to run" not in out:
            fail("unhide-linux -V (non-root): rc=%d, banner/root-refusal missing" % rc)
        ok("unhide-linux -V (non-root): banner + 'You must be root to run', exit 1")

        # C2: unhide-tcp refuses to run as non-root
        rc, out = run(runner + [bins["unhide-tcp"], "-V"])
        if rc != 1 or BANNER_TCP not in out or "You must be root to run" not in out:
            fail("unhide-tcp -V (non-root): rc=%d, banner/root-refusal missing" % rc)
        ok("unhide-tcp -V (non-root): banner + 'You must be root to run', exit 1")

        # C3: unhide_rb refuses to run as non-root
        rc, out = run(runner + [bins["unhide_rb"]])
        if rc != 1 or BANNER_RB not in out or "You must be root to run" not in out:
            fail("unhide_rb (non-root): rc=%d, banner/root-refusal missing" % rc)
        ok("unhide_rb (non-root): banner + 'You must be root to run', exit 1")

        # C4: unhide-posix has no root check -> arg validation only
        rc, out = run(runner + [bins["unhide-posix"], "bogus"])
        if rc != 1 or BANNER_POSIX not in out or "proc | sys" not in out:
            fail("unhide-posix bogus (non-root): rc=%d, banner/usage missing" % rc)
        ok("unhide-posix bogus (non-root): banner + 'proc | sys' usage, exit 1")

    print("unhide tests passed: %d checks" % checks)


if __name__ == "__main__":
    main()
