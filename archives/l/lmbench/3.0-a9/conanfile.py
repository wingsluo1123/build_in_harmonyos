#!/usr/bin/env python3
"""Conan recipe for lmbench 3.0-a9 — system micro-benchmark suite.

lmbench (Larry McVoy / Carl Staelin) is a portable micro-benchmark suite: it
measures OS latency (system calls, context switching, pipes, process
creation, signal handling, memory/cache) and bandwidth (pipe, TCP, UDP,
Unix-socket, file, memory, mmap).  Each benchmark is a standalone C program;
the build system is plain make driven by ``scripts/build`` (no
configure/autotools/CMake).

OHOS adaptation (HarmonyOS PC, aarch64):

* The build stays upstream's own: ``make OS=aarch64-ohos CC=<clang>`` in
  ``src/`` runs ``scripts/build`` (compiler feature probes, then make of all
  benchmarks into ``bin/<OS>/``).  The compiler is taken from the Conan conf
  (``tools.build:compiler_executables``, R33) on the make command line, never
  from a bare shell variable.  The OS tag is passed explicitly because
  ``scripts/os`` falls back to ``scripts/gnu-os`` (config.guess), which cannot
  run on OHOS (needs a writable temp dir and a recognised system type).
* Patch 0001 (scripts/build): the feature probes write scratch files under
  ``/tmp/dummy``; on OHOS ``/tmp`` is read-only and ``/usr/tmp``/``/var/tmp``
  do not exist, so every probe failed silently and the fallback defines
  (-DSYS5, -Dvalloc=malloc, ...) were wrong.  The patch makes the probe base
  honour ``$TMPDIR`` first.
* Patches 0002-0005 (Sun RPC): this libc (musl) has no ``rpc/rpc.h``.
  ``bench.h`` included it unconditionally and ``lib_tcp.c``/``lib_udp.c``/
  ``lat_rpc.c`` used the portmapper / RPC client-server API.  The patches
  guard the RPC code with upstream's own ``HAVE_pmap_clnt_h`` probe (undefined
  on musl, set by ``scripts/build`` only when the headers exist) and keep
  ``TRUE``/``FALSE`` (previously supplied by ``rpc/types.h``).  Everything
  that does not need RPC is unaffected: the TCP/UDP/Unix latency and
  bandwidth benchmarks (lat_tcp, lat_udp, bw_tcp, bw_udp, lat_unix, ...) are
  built from the same sources.  ``lat_rpc`` builds a diagnostic entry point
  that reports the missing platform capability instead of the RPC benchmark.
* Known platform limitation (documented, not patched): ``lat_unix_connect``
  uses a filesystem named AF_UNIX socket (upstream hardcodes ``/tmp/af_unix``)
  and OHOS rejects AF_UNIX ``bind`` on the filesystem with EPERM in every
  writable directory (abstract sockets work, but upstream's program is
  path-based).  ``lat_unix``/``bw_unix`` use ``socketpair`` and work.
* The measurement harness needs the machine's timing parameters.  Upstream
  computes them once via the helper programs ``enough``/``timing_o``/
  ``loop_o`` and exports ``ENOUGH``/``TIMING_O``/``LOOP_O`` (that is exactly
  what ``scripts/config-run`` does).  All three helpers are installed in
  ``bin/`` and are used the same way by ``test_package/test_lmbench.sh``.
* ``package()`` mirrors upstream's ``install`` target: benchmarks to ``bin/``,
  headers to ``include/``, the static library to ``lib/libmbench.a`` (upstream
  installs it as ``libmbench.a``).  The interactive suite driver
  (``scripts/results``/``config-run``) is not part of upstream's install and
  is not shipped; every benchmark binary runs standalone.
* License: GPL-2.0 (``COPYING``); ``COPYING-2`` adds the upstream result
  publication restrictions on top of the GPL.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LmbenchConan(ConanFile):
    name = "lmbench"
    version = "3.0-a9"
    description = ("lmbench 3.0-a9: portable system micro-benchmark suite "
                   "(syscall/context/pipe/process latency, memory and cache "
                   "latency, pipe/TCP/UDP/Unix/file bandwidth)")
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/lmbench/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("benchmark", "micro-benchmark", "latency", "bandwidth",
              "lmbench")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # src/Makefile EXES + OPT_EXES (49 standalone benchmark programs).
    _exes = (
        "bw_file_rd", "bw_mem", "bw_mmap_rd", "bw_pipe", "bw_tcp", "bw_unix",
        "hello", "lat_select", "lat_pipe", "lat_rpc", "lat_syscall",
        "lat_tcp", "lat_udp", "lat_mmap", "mhz", "lat_proc", "lat_pagefault",
        "lat_connect", "lat_fs", "lat_sig", "lat_mem_rd", "lat_ctx",
        "lat_sem", "memsize", "lat_unix", "lmdd", "timing_o", "enough",
        "msleep", "loop_o", "lat_fifo", "lmhttp", "lat_http", "lat_fcntl",
        "disk", "lat_unix_connect", "flushdisk", "lat_ops", "line", "tlb",
        "par_mem", "par_ops", "stream",
    )
    _opt_exes = (
        "cache", "lat_dram_page", "lat_pmake", "lat_rand", "lat_usleep",
        "lat_cmd",
    )
    _headers = (
        "bench.h", "lib_debug.h", "lib_mem.h", "lib_tcp.h", "lib_udp.h",
        "lib_unix.h", "names.h", "stats.h", "timing.h", "version.h",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lmbench targets POSIX systems (make + POSIX libc); got "
                f"{self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1.  R33: compiler from the Conan conf, passed on the make
        # command line (the upstream Makefile defaults CC to `scripts/compiler`
        # output and AR to plain `ar`; both are overridden explicitly).
        # OS is lmbench's internal bin/ tag; see the recipe docstring.
        self.run(
            'make -j1 OS=aarch64-ohos CC="{0}" AR=llvm-ar'.format(cc),
            cwd=os.path.join(self.source_folder, "src"),
            env="conanbuild",
        )

    def package(self):
        src_root = self.source_folder
        bin_dir = os.path.join(src_root, "bin", "aarch64-ohos")
        dst_bin = os.path.join(self.package_folder, "bin")
        dst_inc = os.path.join(self.package_folder, "include")
        dst_lib = os.path.join(self.package_folder, "lib")

        copy(self, "COPYING", src=src_root,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING-2", src=src_root,
             dst=os.path.join(self.package_folder, "licenses"))
        for exe in self._exes + self._opt_exes:
            copy(self, exe, src=bin_dir, dst=dst_bin)
        for header in self._headers:
            copy(self, header, src=os.path.join(src_root, "src"), dst=dst_inc)
        # Upstream installs bin/<OS>/lmbench.a as lib/libmbench.a
        copy(self, "lmbench.a", src=bin_dir, dst=dst_lib)
        os.rename(os.path.join(dst_lib, "lmbench.a"),
                  os.path.join(dst_lib, "libmbench.a"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["mbench"]
