#!/usr/bin/env python3
"""Conan recipe for procdump 2.2 (Sysinternals ProcDump for Linux).

Build system: hand-written GNU Makefile driven by CI (Makefile has no configure
step) plus a small C++ CLR profiler that upstream compiles into
`obj/ProcDumpProfiler.so` and then *embeds as raw bytes* into the `procdump`
executable with `ld -r -b binary`. ProfilerHelpers.c writes those bytes back out
to disk at runtime so it can be injected into a .NET process.

Why build() drives the steps itself instead of calling `make`:
  * `CCFLAGS` in the Makefile hard-codes GCC-only `-fanalyzer` plus `-Werror`;
    they are ordinary `=` assignments, so a command-line override does replace
    them, but the remaining `$(OBJDIR): clean` / `$(BINDIR): clean` rules make
    every `make` invocation wipe `obj/` and `bin/` first -- which would delete
    the embedded-blob object before the link step could use it.
  * The embed step shells out to a bare `ld`, which on this target is not GNU
    ld and additionally needs an explicit `-m aarch64linux` emulation. The
    recipe instead emits a one-line `.S` that `.incbin`s the profiler and
    compiles it with the same clang that built everything else, which
    reproduces the `_binary_<path>_start/_end` symbol pair GNU ld would create
    while depending on nothing but the C compiler.

OHOS notes (full detail in notes.md / manifest.yaml):
  * The musl-based OHOS libc implements no POSIX thread cancellation at all:
    pthread_cancel/pthread_setcancelstate/pthread_setcanceltype are neither
    declared in <pthread.h> nor exported by libc.so, and `pthread_t` is
    `struct __pthread *` instead of an integer. build() therefore runs a real
    link probe and, only when cancellation is genuinely missing, defines
    PROCDUMP_NO_PTHREAD_CANCEL so the patches' PthreadCompat.h can fall back to
    a sigaction()+pthread_kill() thread exit. No platform macro is involved.
  * `<zconf.h>` is included by Procdump.h/ProcDumpConfiguration.h but no zlib
    symbol is ever referenced; the OHOS sysroot ships zconf.h, so zlib stays a
    build-time header-only concern and is deliberately NOT declared as a
    Conan dependency.
  * Upstream compiles with `-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=2`. musl has no
    FORTIFY and its libc.so exports none of the `__*_chk` entry points, so those
    two flags are dropped here: with them the executable still links but cannot
    be loaded ("Error relocating ...: __vsnprintf_chk: symbol not found", 11
    such symbols). test_package/test.sh asserts they stay absent.
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches, get,
                               save)
from conan.tools.layout import basic_layout


class ProcdumpConan(ConanFile):
    name = "procdump"
    version = "2.2"
    description = "ProcDump for Linux - captures process core dumps on cpu/memory/signal/.NET triggers"
    license = "MIT"
    homepage = "https://github.com/microsoft/ProcDump-for-Linux"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the OHOS toolchain lives outside the worker's default PATH and the
        # conanbuild env carries no CC/CXX, so read the compilers from the profile
        # conf instead of relying on shell variables (they are empty on CI).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # Upstream CCFLAGS: `-Wall -I ./include -pthread -std=gnu99
        # -fstack-protector-all -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=2 -O2
        # -fanalyzer -Werror`. Three of those cannot be carried over to OHOS:
        #   -fanalyzer  GCC-only (clang: "unknown argument")
        #   -Werror     turns the pre-existing clang diagnostics in the 2022 sources
        #               into a build failure
        #   _FORTIFY_SOURCE=2 (with the -U that precedes it)
        #               musl implements no FORTIFY and libc.so exports none of the
        #               __*_chk entry points, so the produced executable links but
        #               cannot be loaded: "Error relocating ...: __vsnprintf_chk:
        #               symbol not found" (11 such symbols). Only the stack
        #               protector, which musl does provide, is kept.
        cflags = ["-O2", "-g", "-Wall", "-I", "./include", "-pthread", "-std=gnu99",
                  "-fstack-protector-all"]

        # Feature probe instead of a platform macro (knowledge E085/E320/E407):
        # compile AND link a one-liner that touches pthread_cancel. If the target
        # libc really implements cancellation the upstream call sites are used
        # unchanged.
        probe_src = os.path.join(self.build_folder, "pthread_cancel_probe.c")
        save(self, probe_src,
             "#include <pthread.h>\n"
             "int main(void) { return pthread_cancel(pthread_self()); }\n")
        probe_exe = os.path.join(self.build_folder, "pthread_cancel_probe")
        rc = self.run(f"{cc} -o {probe_exe} {probe_src}", shell=True, ignore_errors=True)
        has_cancel = (rc == 0)
        if has_cancel:
            self.output.info("probe: target libc provides pthread_cancel()")
        else:
            self.output.info(f"probe: probe exited {rc} -- target libc has no "
                             "pthread_cancel(); enabling the PthreadCompat "
                             "signal-based fallback")
            cflags.append("-DPROCDUMP_NO_PTHREAD_CANCEL")

        objdir = os.path.join(self.source_folder, "obj")
        bindir = os.path.join(self.source_folder, "bin")
        self.run(f"mkdir -p {objdir} {bindir}", shell=True)

        cflags_s = " ".join(cflags)
        # Same source set the Makefile picks up ($(wildcard src/*.c)); compiled
        # sequentially (R9).
        sources = sorted(f for f in os.listdir(os.path.join(self.source_folder, "src"))
                         if f.endswith(".c"))
        self.run(f"cd {self.source_folder} && "
                 + " && ".join(f"{cc} -c -g -o obj/{f[:-2]}.o src/{f} {cflags_s}"
                               for f in sources),
                 shell=True)

        # CLR profiler. PROFCXXFLAGS is upstream's, minus nothing: -fms-extensions,
        # --no-undefined and easylogging++ all build clean under clang on OHOS.
        prof_cxxflags = [
            "-DELPP_NO_DEFAULT_LOG_FILE", "-DELPP_THREAD_SAFE", "-g", "-pthread",
            "-shared", "--no-undefined", "-Wno-invalid-noreturn", "-Wno-pragma-pack",
            "-Wno-writable-strings", "-Wno-format-security", "-fPIC", "-fms-extensions",
            "-DHOST_64BIT", "-DBIT64", "-DPAL_STDCPP_COMPAT", "-DPLATFORM_UNIX",
            "-std=c++11",
        ] + (["-DPROCDUMP_NO_PTHREAD_CANCEL"] if not has_cancel else [])
        prof_srcs = ["ClassFactory.cpp", "ProcDumpProfiler.cpp", "dllmain.cpp",
                     "corprof_i.cpp", "easylogging++.cc"]
        prof_so = os.path.join(objdir, "ProcDumpProfiler.so")
        self.run(
            f"{cxx} -o {prof_so} "
            + " ".join(os.path.join("profiler", "src", s) for s in prof_srcs)
            + " " + " ".join(prof_cxxflags)
            + " -I profiler/inc -I include",
            cwd=self.source_folder, shell=True)

        # Embed the profiler as raw bytes. GNU `ld -r -b binary obj/ProcDumpProfiler.so`
        # would export _binary_obj_ProcDumpProfiler_so_{start,end}; the same pair is
        # produced here by a generated .S so the step needs nothing but clang.
        blob_o = os.path.join(objdir, "ProcDumpProfiler.o")
        blob_s = os.path.join(objdir, "embed_profiler.S")
        save(self, blob_s,
             '    .section .rodata\n'
             '    .globl _binary_obj_ProcDumpProfiler_so_start\n'
             '    .globl _binary_obj_ProcDumpProfiler_so_end\n'
             '    .balign 8\n'
             '_binary_obj_ProcDumpProfiler_so_start:\n'
             '    .incbin "obj/ProcDumpProfiler.so"\n'
             '_binary_obj_ProcDumpProfiler_so_end:\n'
             '    .byte 0\n')
        self.run(f"{cc} -c -fPIC -o {blob_o} {blob_s}", cwd=self.source_folder, shell=True)

        objs = " ".join(f"obj/{f[:-2]}.o" for f in sources) + " obj/ProcDumpProfiler.o"
        self.run(f"{cc} -o bin/procdump {objs} {cflags_s}",
                 cwd=self.source_folder, shell=True)

        # Upstream also builds tests/integration/ProcDumpTestApplication as part of
        # `make build`. It is the load generator the integration scenarios attach
        # to; build it so the package mirrors upstream's build output, but it is
        # not packaged.
        test_app = os.path.join(self.source_folder, "tests", "integration",
                                "ProcDumpTestApplication.c")
        self.run(f"{cc} -o bin/ProcDumpTestApplication {test_app} {cflags_s}",
                 cwd=self.source_folder, shell=True)

    def package(self):
        copy(self, "procdump", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "procdump.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]