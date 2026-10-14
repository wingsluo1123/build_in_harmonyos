#!/usr/bin/env python3
"""Conan recipe — synscan 5.02 (Autotools) — SYN port scanner toolset.

Synscan (https://digit-labs.org/files/tools/synscan/) is a self-contained
Autotools toolset that ships two command-line programs:
  - synscan : sends crafted TCP SYN packets over a raw socket
  - sslog   : listens for the resulting SYN/ACK replies via libpcap
The core scanning itself needs a raw socket + libpcap at *runtime* and
requires root/elevated privileges, so it cannot be exercised as a plain
consumer.  However net.c/common.c/obuf.c contain a substantial, libpcap-free
parsing engine (IP-list & port-list parsing, iterators, sums, TCP-flag
parsing) that works without any special privilege.  We therefore package:

  bin/synscan, bin/sslog        — the two real binaries (the tool)
  lib/libsynscan.a              — archive of common.o/net.o/obuf.o (parse API)
  include/{net,iter,obuf,common,synscan}.h — public headers for the parse API

so that the test_package can both run the binaries (`-V`/`-h`, which exit
before the root/raw-socket path) and link against and genuinely call the
parse API on the device without needing root.

Build (Autotools): configure requires libpcap (hard AC_ERROR); we satisfy it
via `--with-libpcap=<staged-dir>` pointing at a private build-dir stage that
holds the published libpcap/1.10.6 pcap.h + libpcap.a.  The 2011-aged
configure only *defines* ac_config_guess/ac_config_sub and never runs them, so
no config.guess/config.sub or --build/--host triplet is needed.

OHOS/HMFS adaptation (single patch to the shipped generated `configure`):
the AS_TMPDIR block creates ./conf* with `umask 077 && mktemp -d` (+ a 077
mkdir fallback); on the HMFS device filesystem a 077/setgid dir is left
owner-unwritable, so config.status dies in `./conf*/subs1.awk: Permission
denied`.  The patch drops the mktemp branch and always mkdir under umask 022
(same fingerprint/fix as libapreq2 2.17, cln 1.3.7, tta 2.2, rancid 3.14).

`make install` is not used: its install target calls `strip` and
`@INSTALL_PROGRAM@`, which can be fragile on OHOS.  package() copies the two
binaries, the static archive and the headers directly.
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SynscanConan(ConanFile):
    name = "synscan"
    version = "5.02"
    description = (
        "synscan 5.02 — high-speed SYN port scanner (synscan sends crafted "
        "TCP SYN packets, sslog listens for SYN/ACK replies via libpcap), "
        "with a libpcap-free IP/port-list parsing engine"
    )
    license = "GPL-2.0"
    homepage = "https://digit-labs.org/files/tools/synscan/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"synscan is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # libpcap is a hard upstream configure dependency (and sslog links it).
        self.requires("libpcap/1.10.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Injects CC/CFLAGS/CONFIG_SHELL from the OHOS toolchain into the
        # conanbuild env used to run configure/make (R33 convention).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _stage_libpcap(self):
        """Configure's --with-libpcap=DIR requires DIR to directly contain
        pcap.h + libpcap.a (it sets -I DIR, -I DIR/bpf, -L DIR, -lpcap).  The
        published libpcap/1.10.6 package keeps headers under include/pcap/ and
        the static lib under lib/, so stage them into a private build-dir
        prefix (R49).  The real libpcap pcap.h also does
        `#include <pcap/funcattrs.h>` (plus <pcap/pcap-inttypes.h> /
        <pcap/socket.h> / <pcap/bpf.h> / <pcap/dlt.h> / <pcap/compiler-tests.h>),
        so the whole flat pcap/ header set must land under <stage>/pcap/ to be
        reachable via -I<stage>; the flat <stage>/pcap.h (duplicate of
        pcap/pcap.h) satisfies configure's `-f $withval/pcap.h` probe.
        """
        dep = self.dependencies["libpcap"]
        pkg = dep.package_folder
        stage = os.path.join(self.build_folder, "libpcap-stage")
        pcap_incdir = os.path.join(pkg, "include", "pcap")
        os.makedirs(stage, exist_ok=True)
        os.makedirs(os.path.join(stage, "pcap"), exist_ok=True)
        pcap_h = os.path.join(pcap_incdir, "pcap.h")
        libpcap_a = os.path.join(pkg, "lib", "libpcap.a")
        if not os.path.isfile(pcap_h):
            self.output.warning("pcap.h not found at %s" % pcap_h)
        if not os.path.isfile(libpcap_a):
            self.output.warning("libpcap.a not found at %s" % libpcap_a)
        # Flat pcap.h + libpcap.a for configure's `-f $withval/pcap.h` check
        # and for sslog.c's `#include <pcap.h>`.
        copy(self, "pcap.h", src=pcap_incdir, dst=stage, keep_path=False)
        copy(self, "libpcap.a", src=os.path.dirname(libpcap_a),
             dst=stage, keep_path=False)
        # Full flat pcap/ header subtree so the transitive
        # `#include <pcap/funcattrs.h>` etc. resolve via -I<stage>.
        copy(self, "*", src=pcap_incdir, dst=os.path.join(stage, "pcap"),
             keep_path=False)
        self.output.info("staged libpcap for --with-libpcap at %s" % stage)
        return stage

    def build(self):
        apply_conandata_patches(self)
        stage = self._stage_libpcap()
        # In-source Autotools build (synscan ships its own Makefile.in +
        # generated configure; same pattern as tta/rancid/magicrescue).
        # HMFS: pin CONFIG_SHELL/SHELL to /bin/sh (mksh works on HMFS whereas
        # the HNP bash getcwd fails) and run under umask 022 so configure's
        # ./conf* temp dirs stay writable (belt-and-braces next to patch 0001).
        configure_cmd = (
            'umask 022 && CONFIG_SHELL=/bin/sh SHELL=/bin/sh "{}/configure" '
            '--with-libpcap={} --prefix=/'
        ).format(self.source_folder, stage)
        # In-source configure: generate Makefile into source_folder so the
        # subsequent `make linux` (also run in source_folder) finds it.  Conan
        # self.run() defaults cwd to build_folder — WITHOUT this cwd, configure
        # emits Makefile/config.h into build_folder while `make` runs in
        # source_folder (which only has Makefile.in), producing
        # "No rule to make target 'linux'" because no Makefile is present.
        #
        # configure forks hundreds of sh/compiler probes.  On a loaded shared
        # CI worker the device intermittently reports fork/exec EAGAIN at this
        # step — the exact same source tree/head 8e30df64 both FAILED
        # (#88960: `configure[35]: can't fork - try again`; #89224: Popen
        # `[Errno 11] Resource temporarily unavailable`) and PASSED on other
        # workers (#89038 CI-018, #89133 CI-025).  That cross-worker split is
        # the environment-resource signature, not a recipe defect, so retry
        # this step a bounded 3 times — only when the captured output actually
        # shows fork pressure, and re-raise otherwise so genuine configure
        # errors (missing libpcap, etc.) are never masked.  Same bounded
        # fork-retry already merged for libcmis/0.6.3.
        configure_log = os.path.join(self.build_folder, "configure.log")
        fork_markers = ("can't fork", "cannot fork", "try again",
                        "resource temporarily unavailable")
        for attempt in (1, 2, 3):
            ret = None
            fork_exc = None
            try:
                with open(configure_log, "w", encoding="utf-8") as handle:
                    ret = self.run(configure_cmd, cwd=self.source_folder,
                                   env="conanbuild", ignore_errors=True,
                                   stdout=handle, stderr=handle)
            except Exception as exc:  # conan_run raises on Popen fork failure
                fork_exc = exc
            detail = ""
            try:
                with open(configure_log, encoding="utf-8",
                          errors="replace") as handle:
                    detail = handle.read()
            except OSError:
                pass
            # Keep configure output visible in the CI log despite the capture.
            if detail:
                print(detail, flush=True)
            if ret == 0:
                break
            combined = ("%s\n%s" % (fork_exc or "", detail)).lower()
            hit_fork_pressure = any(m in combined for m in fork_markers)
            if attempt >= 3 or not hit_fork_pressure:
                raise ConanException(
                    "synscan configure failed (attempt %d/3, rc=%s): %s"
                    % (attempt, ret, (detail or str(fork_exc))[-2000:]))
            wait = 15 * attempt
            self.output.warning(
                "synscan configure hit fork pressure (attempt %d/3, rc=%s); "
                "sleeping %ds then retrying" % (attempt, ret, wait))
            time.sleep(wait)
        # make linux selects the upstream Linux/raw-socket path (-DLINUX).
        self.run("umask 022 && make linux SHELL=/bin/sh -j1",
                 cwd=self.source_folder, env="conanbuild")
        # Archive the libpcap-free parse engine for consumers/test_package.
        # The OHOS SDK ships llvm tooling: prefer llvm-ar, fall back to ar.
        self.run("/bin/sh -c 'set -e; llvm-ar rcs libsynscan.a common.o net.o "
                 "obuf.o 2>/dev/null || ar rcs libsynscan.a common.o net.o obuf.o'",
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(incdir, exist_ok=True)
        # Tool binaries (skip make install: its `strip` + @INSTALL_PROGRAM@
        # are fragile on OHOS).
        copy(self, "synscan", src=src, dst=bindir, keep_path=False)
        copy(self, "sslog", src=src, dst=bindir, keep_path=False)
        # Static parse API.
        copy(self, "libsynscan.a", src=src, dst=libdir, keep_path=False)
        # Public headers for the parse API.
        for header in ("net.h", "iter.h", "obuf.h", "common.h", "synscan.h"):
            copy(self, header, src=src, dst=incdir, keep_path=False)

    def package_info(self):
        # Static parse library (net_parse_portlist / net_parse_iplistv4 /
        # iterators / net_ipv4_parse_flags).  Consumers define `arg_progname`.
        self.cpp_info.libs = ["synscan"]
        self.cpp_info.bindirs = ["bin"]
