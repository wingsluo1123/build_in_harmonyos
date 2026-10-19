#!/usr/bin/env python3
"""Consumer tests for mar 0.5 (both run the packaged, static-pie bin/mar).

The consumers are compiled here, with the OHOS toolchain through CMake, against the packaged
headers and libmar.a, and executed on AArch64 natively or through qemu-aarch64 on x86 runners.

1. mar_consumer_c - CLI <-> C API round trip.  bin/mar writes an archive (four key=value pairs, one
   with non-ASCII bytes, and a 3000-byte binary payload); the C consumer reads it back through the
   file-backed mmap API and checks the raw big-endian header; the consumer then writes a second
   archive (ABI probe pairs and four payload copies spanning several pages) that bin/mar lists,
   measures and extracts.  On OHOS aarch64 plain char is unsigned: with the unpatched utility the
   very first bin/mar invocation already fails with "Unknown option".
2. mar_consumer_cpp - C++ wrapper consumer.  It includes the installed C++ headers (mar_string_c.h
   among them), which only compile with the patched stream classes, walks the CLI-written archive
   with mar::index, reads it with mar::istream, copies it with mar::copy and writes 400 report lines
   (22400 bytes, about 22 flushes of its 1024-byte buffer) through a file-backed mar::iostream that
   bin/mar then lists, measures and extracts.
"""
import os
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

PAYLOAD = bytes((i * 131 + 7) % 256 for i in range(3000))  # every byte value, NUL included
TITLE = "\u9e3f\u8499PC\u9002\u914d"  # UTF-8 value: bytes >= 0x80 pass through bin/mar and libmar
COPIES = 4
REPORT = "".join(
    f"report line {i:04d}: mar stream consumer on OpenHarmony PC\n" for i in range(400)
).encode("ascii")


class MarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    # -- helpers -----------------------------------------------------------------------------
    def _work(self):
        return os.path.join(self.build_folder, "mar-work")

    def _mar_bin(self):
        folder = self.dependencies[self.tested_reference_str].package_folder
        return os.path.join(folder, "bin", "mar")

    def _aarch64(self, *args):
        """Argument vector that runs an AArch64 binary: natively on AArch64, else via qemu-aarch64."""
        if str(self.settings.arch) != "armv8" or platform.machine().lower() in ("aarch64", "arm64"):
            return list(args)
        qemu = shutil.which("qemu-aarch64")
        if qemu is None:
            raise ConanException("qemu-aarch64 is required to run AArch64 binaries on this host")
        return [qemu, *args]

    def _expect(self, condition, message):
        if not condition:
            raise ConanException("FAIL " + message)
        self.output.info("PASS " + message)

    def _mar(self, *args, rc=0):
        """Run the packaged bin/mar in the work dir; check its exit status; return (stdout, stderr)."""
        cmd = self._aarch64(self._mar_bin(), *args)
        self.output.info("RUN: " + shlex.join(cmd))
        proc = subprocess.run(cmd, cwd=self._work(), capture_output=True)
        if proc.returncode != rc:
            raise ConanException(
                f"FAIL mar {shlex.join(args)}: exit status {proc.returncode}, expected {rc}\n"
                f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}")
        return proc.stdout, proc.stderr

    def _read(self, name):
        with open(os.path.join(self._work(), name), "rb") as handle:
            return handle.read()

    # -- build: compile the consumers against the packaged headers and libmar.a ---------------
    def build(self):
        work = self._work()
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        with open(os.path.join(work, "payload.bin"), "wb") as handle:
            handle.write(PAYLOAD)
        cmake = CMake(self)
        cmake.configure()
        # E074/E525: no FIFO jobserver on HMDFS, keep make serial.
        cmake.build(build_tool_args=["-j1"])

    # -- test --------------------------------------------------------------------------------
    def test(self):
        work = self._work()
        bindir = os.path.join(self.build_folder, self.cpp.build.bindirs[0])
        consumer_c = os.path.join(bindir, "mar_consumer_c")
        consumer_cpp = os.path.join(bindir, "mar_consumer_cpp")

        # Tool output: the packaged mar writes the archive both consumers read.  Valid invocations
        # must succeed silently (the unpatched utility reports "Unknown option" and exits 1).
        _, err = self._mar("-s", "product=OpenHarmony-PC", "-s", "title=" + TITLE,
                           "-s", "arch=aarch64", "-s", "abi=musl", "-i", "payload.bin", "cli.mar")
        self._expect(err == b"", "mar -s/-i creates cli.mar without diagnostics")
        out, _ = self._mar("-t", "cli.mar")
        self._expect(out == b"product=OpenHarmony-PC\ntitle=" + TITLE.encode() + b"\narch=aarch64\nabi=musl\n",
                     "mar -t lists the four pairs, UTF-8 title intact")
        out, _ = self._mar("-l", "cli.mar")
        self._expect(out == b"3000\n", "mar -l reports the 3000-byte user data")

        # 1. C consumer: reads cli.mar through libmar, writes lib.mar.
        self.run(shlex.join(self._aarch64(consumer_c, "cli.mar", "payload.bin", "lib.mar")), cwd=work)
        out, _ = self._mar("-k", "lib.mar")
        self._expect(out == b"writer\nptr\nchar\npagesize\ncopies\n", "mar -k lists the keys the C consumer set")
        out, _ = self._mar("-m", "writer", "lib.mar")
        self._expect(out == b"consumer.c\n", "mar -m writer reads the C consumer's pair")
        out, _ = self._mar("-m", "ptr", "lib.mar")
        self._expect(out == b"8\n", "the consumer ran with 8-byte pointers")
        out, _ = self._mar("-m", "char", "lib.mar")
        if str(self.settings.arch) == "armv8":
            self._expect(out == b"unsigned\n", "plain char is unsigned on this target (the ABI that broke the utility)")
        out, _ = self._mar("-m", "pagesize", "lib.mar")
        page = int(out)
        self._expect(page >= 4096 and page & (page - 1) == 0, "page size is a power of two >= 4096")
        out, _ = self._mar("-l", "lib.mar")
        self._expect(out == b"%d\n" % (COPIES * len(PAYLOAD)), "mar -l measures the 12000 bytes the consumer wrote")
        self._mar("-x", "out.bin", "lib.mar")
        self._expect(self._read("out.bin") == PAYLOAD * COPIES, "mar -x extracts the four payload copies byte for byte")

        # 2. C++ consumer: reads cli.mar through the wrappers, writes cpp.mar through mar::iostream.
        self.run(shlex.join(self._aarch64(consumer_cpp, "cli.mar", "payload.bin", "cpp.mar")), cwd=work)
        out, _ = self._mar("-m", "writer", "cpp.mar")
        self._expect(out == b"consumer_cpp.cpp\n", "mar -m writer reads the C++ consumer's pair")
        out, _ = self._mar("-m", "lines", "cpp.mar")
        self._expect(out == b"400\n", "mar -m lines reads the second pair")
        out, _ = self._mar("-l", "cpp.mar")
        self._expect(out == b"%d\n" % len(REPORT), "mar -l measures the %d bytes written through the stream" % len(REPORT))
        self._mar("-x", "report.txt", "cpp.mar")
        self._expect(self._read("report.txt") == REPORT, "mar -x extracts the stream text byte for byte")

        # The utility still rejects what it should.
        _, err = self._mar("-Q", "cli.mar", rc=1)
        self._expect(err.startswith(b"Unknown option `-Q'"), "mar rejects an unknown option")
        _, err = self._mar("-m", "missing", "cli.mar", rc=1)
        self._expect(b"Failed to print meta data by key" in err, "mar -m on a missing key fails")
        _, err = self._mar("-t", rc=1)
        self._expect(err.startswith(b"Archive not specified"), "mar without an archive fails")
