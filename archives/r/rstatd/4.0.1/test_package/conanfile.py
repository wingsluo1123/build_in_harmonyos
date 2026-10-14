#!/usr/bin/env python3
"""Conan test_package for rstatd 4.0.1 - functional test of the packaged daemon.

The package ships three executables and no library, so the test drives
rpc.rstatd over real ONC RPC: it emulates what inetd does (a connected UDP
socket on file descriptor 0), sends RSTATPROC_STATS / RSTATPROC_HAVEDISK
requests with a hand written RPC/XDR encoder and asserts on the values the
daemon collected from /proc.  See test_rstatd.c for the details.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RstatdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Build the shims.  Both are optional helpers: if compilation fails
        # the test still runs, just without the corresponding helper.
        #   fdchk_shim  - provides __fd_chk for qemu guest roots whose libc
        #                 lacks it (see notes.md section 8)
        #   syslog_shim - diagnostic only (CI evidence gathering, see
        #                 notes.md section 11): routes the daemon's syslog()
        #                 output to stderr and probes fd 0 / kernel release
        for src_name, dst_name in (("fdchk_shim.c", "libfdchk_shim.so"),
                                   ("syslog_shim.c", "libsyslog_shim.so")):
            shim_src = os.path.join(self.source_folder, src_name)
            shim_dst = os.path.join(self.build_folder, dst_name)
            if os.path.isfile(shim_src):
                cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c")
                if not cc:
                    cc = os.environ.get("CC", "clang")
                try:
                    subprocess.run(
                        [cc, "-shared", "-fPIC", "-o", shim_dst, shim_src],
                        check=True,
                        capture_output=True,
                    )
                    self.output.info(f"Built shim {src_name}: {shim_dst}")
                except subprocess.CalledProcessError as e:
                    self.output.warning(f"Failed to build {src_name}: {e.stderr.decode()}")

    def test(self):
        # AutotoolsToolchain routes sbindir to ${prefix}/bin, so all three
        # programs land in <package_folder>/bin.
        bindir = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                              "bin")
        daemon = os.path.join(bindir, "rpc.rstatd")
        rup = os.path.join(bindir, "rup")
        rsysinfo = os.path.join(bindir, "rsysinfo")

        for path in (daemon, rup, rsysinfo):
            if not os.path.isfile(path):
                raise AssertionError("packaged executable is missing: %s" % path)

        # Compose LD_PRELOAD:
        #   - syslog_shim: diagnostic only, always on this revision so the CI
        #     log shows the daemon's own error messages (notes.md section 11).
        #   - fdchk_shim: only when a qemu guest root is present on the host
        #     (/opt/ohos-guest, notes.md section 8).  On a real OHOS device
        #     libc already defines __fd_chk, and preloading the range-check
        #     stub would mask the genuine check - so it must not load there.
        preload = []
        syslog_shim = os.path.join(self.build_folder, "libsyslog_shim.so")
        if os.path.isfile(syslog_shim):
            preload.append(syslog_shim)
            self.output.info(f"Using syslog shim: {syslog_shim}")
        if os.path.isfile("/opt/ohos-guest/lib/libc.so"):
            fdchk_shim = os.path.join(self.build_folder, "libfdchk_shim.so")
            if os.path.isfile(fdchk_shim):
                preload.append(fdchk_shim)
                self.output.info("qemu guest root detected: using fd_chk shim")
        if preload:
            os.environ["LD_PRELOAD"] = ":".join(preload)

        # The three programs must also be discoverable through the package's
        # declared bindirs (that is what commands.json consumers rely on).
        # `command -v <prog>` exits non-zero when the name is not resolvable,
        # so self.run() turns this into a real assertion.
        self.run("command -v rup", env="conanrun")
        self.run("command -v rpc.rstatd", env="conanrun")
        self.run("command -v rsysinfo", env="conanrun")

        cmd = '"{test}" "{daemon}" "{rup}" "{rsysinfo}"'.format(
            test=os.path.join(self.build_folder, "test_rstatd"),
            daemon=daemon, rup=rup, rsysinfo=rsysinfo)
        self.run(cmd, env="conanrun")