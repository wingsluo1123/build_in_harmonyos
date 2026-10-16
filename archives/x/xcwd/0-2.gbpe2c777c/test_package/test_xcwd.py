#!/usr/bin/env python3
"""Consumer harness for the packaged ``xcwd`` executable (R34 / L1e aligned).

Driven by ``test_package/conanfile.py`` from a real ``self.run()`` inside the
``conanrun`` environment::

    python3 test_xcwd.py <packaged-xcwd> <work-dir>

Every check reads the artifact that Conan shipped in the package folder (or
executes it), so moving ``bin/`` away makes the suite fail — which is exactly
what CI's destructive L1e pass asserts.

Only the Python standard library is used: the CI worker is not guaranteed to
provide ``readelf`` / ``strings`` / ``nm``, so the ELF parsing below is done
in-process.

Note on scope: HarmonyOS PC ships no X server (no Xorg/Xvfb/Xwayland package in
the artifact repository and no ``/tmp/.X11-unix`` socket on the device), so the
X-server-dependent functionality — focused-window handle, ``_NET_WM_PID``
lookup, ``WM_CLASS`` matching and the ``/proc/<pid>/cwd`` resolution — cannot be
exercised end to end here.  What *is* verified is recorded in MANIFEST.yml: the
program really runs, the X11 platform branch that the OHOS adaptation selects is
really the one compiled in, and the packaged libX11 is really what it loads.
"""

import os
import stat
import subprocess
import sys

EM_AARCH64 = 0xB7
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
DT_NEEDED = 1
DT_STRTAB = 5
DT_RPATH = 15
DT_SONAME = 14
DT_RUNPATH = 29

# Literals that exist only in upstream's `#ifdef LINUX` sources:
#   xcwd.c:235  snprintf(path, sizeof(path), "/proc/%ld/cwd", proc->pid)
#   xcwd.c:161  glob("/proc/[0-9]*", GLOB_NOSORT, NULL, &globbuf)
#   xcwd.c:172  snprintf(name, sizeof(name), "%s%s", globbuf.gl_pathv[...], "/stat")
LINUX_ONLY_LITERALS = (b"/proc/%ld/cwd", b"/proc/[0-9]*", b"/stat")

# Exact no-display status: xcwd.c:69-71 exits EXIT_FAILURE when XOpenDisplay()
# returns NULL (no DISPLAY / unreachable server).
NO_DISPLAY_EXIT = 1


class Report:
    def __init__(self):
        self.failures = 0
        self.checks = 0

    def ok(self, case, message):
        self.checks += 1
        print(f"  [ok]   {case}: {message}")

    def fail(self, case, message):
        self.checks += 1
        self.failures += 1
        print(f"  [FAIL] {case}: {message}")


def u16(data, offset):
    return int.from_bytes(data[offset:offset + 2], "little")


def u32(data, offset):
    return int.from_bytes(data[offset:offset + 4], "little")


def u64(data, offset):
    return int.from_bytes(data[offset:offset + 8], "little")


def parse_dynamic(data):
    """Return {needed:[...], soname:str|None, has_rpath:bool, has_runpath:bool}."""
    program_offset = u64(data, 32)
    program_size = u16(data, 54)
    program_count = u16(data, 56)

    loads, dynamic = [], None
    for index in range(program_count):
        offset = program_offset + index * program_size
        kind = u32(data, offset)
        if kind == PT_LOAD:
            loads.append((u64(data, offset + 16), u64(data, offset + 8),
                          u64(data, offset + 32)))
        elif kind == PT_DYNAMIC:
            dynamic = (u64(data, offset + 16), u64(data, offset + 8),
                       u64(data, offset + 32))

    if dynamic is None:
        raise AssertionError("ELF has no PT_DYNAMIC segment")

    def vaddr_to_offset(address):
        for vaddr, file_offset, filesize in loads:
            if vaddr <= address < vaddr + filesize:
                return file_offset + (address - vaddr)
        raise AssertionError(f"vaddr 0x{address:x} is not mapped by any PT_LOAD")

    entries = []
    _, dynamic_offset, dynamic_size = dynamic
    for index in range(dynamic_size // 16):
        offset = dynamic_offset + index * 16
        tag = int.from_bytes(data[offset:offset + 8], "little", signed=True)
        value = u64(data, offset + 8)
        if tag == 0:
            break
        entries.append((tag, value))

    string_table = None
    for tag, value in entries:
        if tag == DT_STRTAB:
            string_table = vaddr_to_offset(value)
    if string_table is None:
        raise AssertionError("ELF has no DT_STRTAB entry")

    def read_string(offset):
        end = data.index(b"\x00", string_table + offset)
        return data[string_table + offset:end].decode("utf-8", "replace")

    result = {"needed": [], "soname": None, "has_rpath": False, "has_runpath": False}
    for tag, value in entries:
        if tag == DT_NEEDED:
            result["needed"].append(read_string(value))
        elif tag == DT_SONAME:
            result["soname"] = read_string(value)
        elif tag == DT_RPATH:
            result["has_rpath"] = True
        elif tag == DT_RUNPATH:
            result["has_runpath"] = True
    return result


def run_binary(executable, work_dir, tag, environment):
    stdout_path = os.path.join(work_dir, f"consumer-{tag}.out")
    stderr_path = os.path.join(work_dir, f"consumer-{tag}.err")
    with open(stdout_path, "wb") as stdout_file, \
            open(stderr_path, "wb") as stderr_file:
        completed = subprocess.run([executable], stdout=stdout_file,
                                   stderr=stderr_file, env=environment,
                                   check=False)
    with open(stdout_path, "rb") as handle:
        stdout = handle.read()
    with open(stderr_path, "rb") as handle:
        stderr = handle.read()
    return completed.returncode, stdout, stderr


def main(argv):
    if len(argv) != 3:
        print("usage: test_xcwd.py <packaged-xcwd> <work-dir>")
        return 2
    executable, work_dir = argv[1], argv[2]

    report = Report()

    # ── HC-1: packaged artifact contract ────────────────────────────────────
    if not os.path.isfile(executable):
        report.fail("HC-1", f"packaged executable missing: {executable}")
        return 1
    mode = os.stat(executable).st_mode
    report.ok("HC-1", f"packaged executable present: {executable}")
    if mode & stat.S_IXUSR:
        report.ok("HC-1", "executable bit set on the packaged file")
    else:
        report.fail("HC-1", f"packaged file is not executable (mode {mode:o})")

    with open(executable, "rb") as handle:
        data = handle.read()

    if data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1:
        report.ok("HC-1", "ELF64 little-endian image")
    else:
        report.fail("HC-1", f"unexpected ELF ident: {data[:8]!r}")
    machine = u16(data, 18)
    if machine == EM_AARCH64:
        report.ok("HC-1", "e_machine=EM_AARCH64 (aarch64)")
    else:
        report.fail("HC-1", f"e_machine={machine} is not EM_AARCH64")
    elf_type = u16(data, 16)
    if elf_type == ET_DYN:
        report.ok("HC-1", "e_type=ET_DYN (PIE)")
    else:
        report.fail("HC-1", f"e_type={elf_type} is not ET_DYN/PIE")

    # ── HC-2: the packaged program really runs (headless contract) ───────────
    runtime_env = dict(os.environ)
    runtime_env.pop("DISPLAY", None)
    code, stdout, stderr = run_binary(executable, work_dir, "nodisplay", runtime_env)
    if code == NO_DISPLAY_EXIT:
        report.ok("HC-2", f"headless run exits {NO_DISPLAY_EXIT} "
                          "(xcwd.c:69-71 XOpenDisplay failure path)")
    else:
        report.fail("HC-2", f"headless run exited {code}, expected "
                            f"{NO_DISPLAY_EXIT}")
    if not stdout and not stderr:
        report.ok("HC-2", "headless run produces no output (matches upstream path)")
    else:
        report.fail("HC-2", f"headless run produced stdout={stdout!r} "
                            f"stderr={stderr!r}")

    # ── HC-3: the LINUX platform branch is really compiled in ───────────────
    missing = [literal for literal in LINUX_ONLY_LITERALS if literal not in data]
    if not missing:
        report.ok("HC-3", "LINUX-only /proc literals present "
                          f"({len(LINUX_ONLY_LITERALS)}/{len(LINUX_ONLY_LITERALS)})")
    else:
        report.fail("HC-3", "binary is missing LINUX-only literals "
                            f"{[item.decode() for item in missing]} — the "
                            "upstream -DLINUX branch was not compiled in")

    # ── HC-4: ELF dynamic invariants of the shipped artifact ────────────────
    dynamic = parse_dynamic(data)
    report.ok("HC-4", f"DT_NEEDED = {dynamic['needed']}")
    if "libX11.so.6" in dynamic["needed"]:
        report.ok("HC-4", "links the X11 client library libX11.so.6")
    else:
        report.fail("HC-4", "DT_NEEDED does not contain libX11.so.6")
    absolute = [name for name in dynamic["needed"] if "/" in name]
    if not absolute:
        report.ok("HC-4", "no DT_NEEDED entry leaks a build-machine path")
    else:
        report.fail("HC-4", f"DT_NEEDED leaks absolute paths: {absolute}")
    if not dynamic["has_rpath"] and not dynamic["has_runpath"]:
        report.ok("HC-4", "no DT_RPATH/DT_RUNPATH (conanrun provides the "
                          "library search path; OHOS loader rejects "
                          "cache-pointing RUNPATH)")
    else:
        report.fail("HC-4", "binary embeds DT_RPATH/DT_RUNPATH "
                            f"(rpath={dynamic['has_rpath']}, "
                            f"runpath={dynamic['has_runpath']})")

    # ── HC-5: the runtime dependency on the packaged libX11 is genuine ──────
    stripped_env = dict(os.environ)
    stripped_env.pop("LD_LIBRARY_PATH", None)
    stripped_env.pop("LD_PRELOAD", None)
    stripped_env.pop("DISPLAY", None)
    code, _, stderr = run_binary(executable, work_dir, "nolibpath", stripped_env)
    lines = stderr.decode("utf-8", "replace").strip().splitlines()
    excerpt = f", loader said: {lines[0]!r}" if lines else ""
    # The program's own no-display path also exits nonzero, so a bare
    # "code != 0" could pass for the wrong reason.  Require that the process
    # died *before* main() could reach that path, i.e. a loader/dependency
    # failure.
    if code != 0 and code != NO_DISPLAY_EXIT:
        report.ok("HC-5", f"without the Conan library path the loader stops the "
                          f"binary (exit {code}){excerpt} — libX11 is not taken "
                          f"from the system")
    else:
        report.fail("HC-5", f"exit {code}{excerpt} does not prove a loader "
                            f"failure: the binary either started anyway or "
                            f"reached its own no-display exit "
                            f"({NO_DISPLAY_EXIT}), so this check is inconclusive")

    print(f"[xcwd consumer] {report.checks - report.failures}/{report.checks} "
          f"checks passed")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
