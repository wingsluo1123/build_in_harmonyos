#!/usr/bin/env python3
"""Conan test_package for ukopp 4.9 — consumer verification.

Runs the real installed `ukopp` through test_ukopp.sh: layered packaging
probes (A1 packaged binary present + executable, A2 ELF64/AArch64 magic,
A3 DT_NEEDED closure carries the GTK3 stack — readelf, skipped when
absent) plus the real command line mode: `ukopp -nogui` with a fresh
$HOME must exit rc=0 after writing its startup banner and its
version/license report into $HOME/.ukopp/logfile — zfuncs zinitapp()
redirects stdout/stderr to that logfile whenever stdin is not a tty, so
the assertions read the logfile (not stdout); `-nogui` never calls
gtk_init(), making the run headless-safe.

Execution model
---------------
CI runs this on a real HarmonyOS PC worker, where the OHOS aarch64 ELF is
native: test_ukopp.sh execs the binary directly. On a host whose
architecture differs from the packaged ELF (e.g. an x86_64 Linux dev box
compiling for OHOS aarch64) the binary cannot be exec'd. The decision is
taken from the ELF header of the produced binary, NOT from Conan's
cross_building(): the OHOS profiles pass the same file for -pr:h and
-pr:b, so Conan reports host == build even though the ELF is foreign. In
that case test_ukopp.sh launches the binary through qemu-aarch64 against
an OHOS guest sysroot with a stack of guest-side shims preloaded via -E
LD_PRELOAD (they provide the OHOS fortify/arc4random/backtrace symbols
that the stock-musl guest libc lacks — see _GUEST_PRELOADS), while
libc++_shared.so is loaded normally from the guest sysroot (ukopp and
harfbuzz carry DT_NEEDED libc++_shared.so). Precedent:
archives/m/musicpc/0.35, archives/t/tasksh/1.2.0,
archives/a/array-hash/0.7.2, archives/v/vimpc/0.09.2.

CI closure gap
--------------
conanrun.sh carries the conan closure only, but ukopp and the closure's
C++ libs (harfbuzz) carry DT_NEEDED libc++_shared.so from the OHOS SDK
sysroot, and unversioned libffi.so may live only in the HNP install
(same gap documented by the klavaro/3.14 and mednaffe/0.9.3 consumer
tests): test() prepends those HNP/SDK libdirs to conanrun.sh when
present — no-op on hosts that do not ship them.
"""
import glob
import os
import platform
import shutil
import struct

from conan import ConanFile

# e_machine values from the ELF spec, restricted to what matters here.
_EM_AARCH64 = 0xB7
_EM_X86_64 = 0x3E

# Guest sysroots searched for the OHOS loader/libc when emulating.
_GUEST_ROOTS = ("/opt/ohos-guest",)
# Guest-side preload shims, applied by the emulated guest's dynamic loader
# via qemu -E LD_PRELOAD. The guest libc is a stock musl build, while the
# GTK3 closure was produced against the real OHOS libc/NDK, which exports
# the whole fortify family plus the C++ runtime entry points:
#   libchkfcnshim.so    __strlen_chk/__vsnprintf_chk/... (cairo, glib)
#   libpcmchkshim.so    __memcpy_chk/__memset_chk + backtrace/backtrace_symbols
#                       (cairo; ukopp links -rdynamic and calls backtrace())
#   libarc4shim.so      arc4random/arc4random_buf (expat)
#   libmemchrchkshim.so __memchr_chk (cairo)
# libc++_shared.so is NOT preloaded: it sits in the guest sysroot and is
# loaded normally — ukopp and the closure's C++ libs (harfbuzz) carry
# DT_NEEDED libc++_shared.so and resolve their __cxa_*/__gxx_personality_v0/
# _Unwind_Resume relocations against it.
_GUEST_PRELOADS = ("libchkfcnshim.so", "libpcmchkshim.so",
                   "libarc4shim.so", "libmemchrchkshim.so")


def _elf_machine(path):
    """Return the ELF e_machine of `path`, or None if it is not an ELF."""
    with open(path, "rb") as handle:
        header = handle.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        return None
    little_endian = header[5] == 1
    return struct.unpack("<H" if little_endian else ">H", header[18:20])[0]


def _host_machine():
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return _EM_AARCH64
    if machine in ("x86_64", "amd64"):
        return _EM_X86_64
    return None


class UkoppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _emulation_env(self, ukopp_bin):
        """Empty on the CI worker (the ELF is native there). On a cross-build
        host it names qemu-aarch64, the guest sysroot and the fortify shim,
        which test_package/test_ukopp.sh turns into the actual qemu command
        line. `cross_building()` is deliberately not consulted: the OHOS
        profiles pass the same file for -pr:h and -pr:b, so Conan sees
        host == build even though the ELF is aarch64 and the host is
        x86_64."""
        if _elf_machine(ukopp_bin) == _host_machine():
            return {}
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise Exception(
                "the packaged ukopp ELF targets a foreign architecture and "
                "qemu-aarch64 is required to execute it under test")
        guest = next((root for root in _GUEST_ROOTS
                      if os.path.isdir(os.path.join(root, "lib"))), None)
        if guest is None:
            raise Exception(
                "the packaged ukopp ELF targets a foreign architecture and "
                f"no OHOS guest sysroot was found in {list(_GUEST_ROOTS)}")
        env = {"UKOPP_RUNNER": qemu,
               "UKOPP_GUEST_ROOT": guest,
               "UKOPP_CROSS_EMULATED": "1"}
        preloads = [os.path.join(guest, "lib", name)
                    for name in _GUEST_PRELOADS]
        missing = [p for p in preloads if not os.path.isfile(p)]
        if missing:
            raise Exception(
                "the packaged ukopp ELF targets a foreign architecture and "
                f"guest preload shims are missing: {missing}")
        env["UKOPP_GUEST_PRELOAD"] = ":".join(preloads)
        return env

    def test(self):
        # The test logic itself is host shell: sh, timeout, grep and od all
        # run natively. Only the ukopp binary goes through the emulation
        # prefix, which is why the qemu command line is built inside
        # test_ukopp.sh.
        sh = os.environ.get("CONFIG_SHELL") or shutil.which("bash") \
            or shutil.which("sh") or "/bin/sh"
        ukopp_bin = os.path.join(
            self.dependencies["ukopp"].cpp_info.bindirs[0], "ukopp")
        env = self._emulation_env(ukopp_bin)

        def q(s):
            return '"' + s.replace('"', '\\"') + '"'

        cmd = " ".join([q(sh),
                        q(os.path.join(self.source_folder, "test_ukopp.sh")),
                        q(ukopp_bin)])
        if env:
            # ConanFile.run() has no env_append parameter; pass the
            # cross-emulation variables as a command prefix instead.
            env_prefix = " ".join(
                f"{k}={q(v)}" for k, v in sorted(env.items()))
            cmd = f"{env_prefix} {cmd}"
        # VirtualRunEnv's conanrun.sh carries the conan closure only. On the
        # CI worker ukopp itself and the GTK tree's C++ bits (harfbuzz)
        # carry DT_NEEDED libc++_shared.so from the OHOS SDK sysroot, and
        # unversioned libffi.so may live only in the HNP install (same
        # closure gap documented by the klavaro/3.14 and mednaffe/0.9.3
        # consumer tests). Prepend those globs when present — no-op on
        # hosts that do not ship them.
        runsh = os.path.join(self.generators_folder, "conanrun.sh")
        if os.path.isfile(runsh):
            text = open(runsh, encoding="utf-8", errors="ignore").read()
            prepend = ""
            for extra_glob in (
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/"
                "aarch64-linux-ohos",
                "/data/service/hnp/libffi.org/*/lib",
            ):
                extra = sorted(glob.glob(extra_glob))
                if extra:
                    prepend += ('export LD_LIBRARY_PATH="' + extra[0]
                                + ':$LD_LIBRARY_PATH"\n')
            if prepend and "hnp/" not in text:
                # Prepend (klavaro/3.14 pattern): appending would glue onto a
                # missing trailing newline and break `.` sourcing in
                # conanrun.sh.
                with open(runsh, "w", encoding="utf-8") as handle:
                    handle.write(prepend + text)
                self.output.info("Augmented conanrun.sh with SDK/hnp lib paths")
        self.run(cmd, env="conanrun")
