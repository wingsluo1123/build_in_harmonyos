#!/usr/bin/env python3
"""Conan test_package for kio-fuse 5.1.1 (OHOS command-level E2E).

kio-fuse ships no consumable library or header — the deliverable is the
libexec kio-fuse daemon plus the org.kde.KIOFuse D-Bus activation service
file — so this test runs the real packaged binary itself (no stub):

  1. Static artifact assertions (always, any profile): the libexec ELF
     DT_NEEDED contains libQt6DBus (patch 0001 effective) and no
     libfuse3.so (static libfuse), and no absolute paths; the D-Bus
     service file + systemd user unit point at the packaged daemon; the
     vendored libdbus-1.so.3 is shipped (this check also makes the
     destructive CI re-run of the test fail, as a real test must).
  2. Runtime probes via test_package/test_kio_fuse.sh, executed through
     self.run in the generated conanrun environment on runnable targets:
     --version prints the upstream version line and the static libfuse
     version; --help prints the usage text incl. --disable-filejob-io;
     kio-fuse -f <mountpoint> really starts KIOFuseService (the OHOS
     sandbox denies the kernel FUSE mount gracefully, or the daemon
     keeps serving when the environment permits the mount).

Tests are plain assertions; any failure exits non-zero and fails the test.
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicit runtime set: the daemon links libQt6DBus directly, and
        # kio's transitives (kconfig/ki18n/kservice/kcrash) back both the
        # KF6KIOConfig find_dependency()s and the KF6KIOCore runtime load.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")
        self.requires("kservice/6.26.0")

    def layout(self):
        basic_layout(self)

    def test(self):
        pkg = self.dependencies.get(self.tested_reference_str.split("/")[0])
        assert pkg and pkg.package_folder, "tested kio-fuse package not found"
        prefix = pkg.package_folder
        daemon = os.path.join(prefix, "libexec", "kio-fuse")
        assert os.path.isfile(daemon), f"libexec/kio-fuse missing under {prefix}"

        # ---- static artifact checks (every profile) ----
        readelf = next((c for c in (
            *sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/llvm-readelf")),
            "/data/service/hnp/bin/llvm-readelf",
            "/storage/Users/currentUser/.harmonybrew/bin/readelf",
        ) if os.path.isfile(c)), None)
        assert readelf, "no llvm-readelf available on the device"
        dyn = subprocess.run([readelf, "-d", daemon], capture_output=True,
                             text=True)
        needed = [line.split("[")[-1].rstrip("]")
                  for line in dyn.stdout.splitlines() if "(NEEDED)" in line]
        assert needed, f"no DT_NEEDED entries parsed from {daemon}"
        assert any(n.startswith("libQt6DBus") for n in needed), \
            f"patch 0001 not effective? NEEDED={needed}"
        assert not any(n.startswith("libfuse3") for n in needed), \
            f"libfuse not linked statically? NEEDED={needed}"
        assert not [n for n in needed if n.startswith(("/", "../"))], \
            f"absolute DT_NEEDED paths: {needed}"

        svc_hits = glob.glob(os.path.join(
            prefix, "share", "**", "org.kde.KIOFuse.service"), recursive=True)
        assert svc_hits, "org.kde.KIOFuse.service not installed"
        svc = open(svc_hits[0], encoding="utf-8").read()
        assert "[D-BUS Service]" in svc and "Name=org.kde.KIOFuse" in svc, svc
        exec_line = next((line for line in svc.splitlines()
                          if line.startswith("Exec=")), "")
        assert "/libexec/kio-fuse" in exec_line and "-f" in exec_line, \
            f"unexpected D-Bus Exec line: {exec_line!r}"

        unit_hits = glob.glob(os.path.join(
            prefix, "**", "kio-fuse.service"), recursive=True)
        assert unit_hits, "kio-fuse.service systemd unit not installed"
        unit = open(unit_hits[0], encoding="utf-8").read()
        exec_start = next((line for line in unit.splitlines()
                           if line.startswith("ExecStart=")), "")
        assert "/libexec/kio-fuse" in exec_start, \
            f"unexpected systemd ExecStart: {exec_start!r}"

        assert glob.glob(os.path.join(prefix, "lib", "libdbus-1.so*")), \
            "vendored libdbus-1.so.3 missing"
        self.output.info("static artifact checks OK: DT_NEEDED=%s" % needed)

        # ---- runtime probes: real daemon execution (conanrun env) ----
        script = os.path.join(self.source_folder, "test_kio_fuse.sh")
        run_binary = "1" if can_run(self) else "0"
        self.output.info("runtime probes: test_kio_fuse.sh (run_binary=%s)"
                         % run_binary)
        self.run(f'sh "{script}" "{daemon}" "{self.build_folder}" "{run_binary}"',
                 env="conanrun")
