#!/usr/bin/env python3
"""Installed-command consumer tests for multimon 1.0."""

import fcntl
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import termios
import time


EXPECTED = ["DTMF: 1", "DTMF: 2", "DTMF: 3", "DTMF: A"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, **kwargs)


def decoded_lines(result):
    return [line for line in result.stdout.splitlines() if line.startswith("DTMF:")]


def main():
    require(len(sys.argv) == 2, "usage: test_multimon.py PACKAGE_BIN")
    package_bin = pathlib.Path(sys.argv[1]).resolve()
    multimon = str(package_bin / "multimon")
    generator = str(package_bin / "gen")
    temp_root = pathlib.Path(os.environ.get("TMPDIR", "/data/storage/el2/base/cache"))

    with tempfile.TemporaryDirectory(prefix="multimon-consumer-", dir=temp_root) as directory:
        root = pathlib.Path(directory)
        raw = root / "dtmf.raw"
        generated = run([generator, "-t", "raw", "-d", "123A", str(raw)])
        require(generated.returncode == 0, f"installed gen failed: {generated.stderr}")
        require(raw.stat().st_size > 16384, "fixture must span multiple decoder reads")

        regular = run([multimon, "-t", "raw", "-a", "DTMF", str(raw)])
        require(regular.returncode == 0, f"regular-file decode failed: {regular.stderr}")
        require(decoded_lines(regular) == EXPECTED, "regular-file DTMF sequence mismatch")

        payload = raw.read_bytes()
        read_fd, write_fd = os.pipe()

        fragmented_process = subprocess.Popen(
            [multimon, "-t", "raw", "-a", "DTMF", f"/proc/self/fd/{read_fd}"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=(read_fd,),
        )
        try:
            require(os.write(write_fd, payload[:1]) == 1, "failed to write the first partial sample")
            deadline = time.monotonic() + 5
            while True:
                queued = struct.unpack(
                    "i",
                    fcntl.ioctl(read_fd, termios.FIONREAD, struct.pack("i", 0)),
                )[0]
                if queued == 0:
                    break
                require(time.monotonic() < deadline, "consumer did not read the first partial sample")
                time.sleep(0.01)

            offset = 1
            while offset < len(payload):
                offset += os.write(write_fd, payload[offset:])
        except BaseException:
            fragmented_process.kill()
            fragmented_process.communicate()
            raise
        finally:
            os.close(write_fd)
            os.close(read_fd)
        try:
            stdout, stderr = fragmented_process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            fragmented_process.kill()
            fragmented_process.communicate()
            raise
        fragmented = subprocess.CompletedProcess(
            fragmented_process.args,
            fragmented_process.returncode,
            stdout,
            stderr,
        )
        require(fragmented.returncode == 0, f"fragmented pipe decode failed: {fragmented.stderr}")
        require(decoded_lines(fragmented) == EXPECTED, "fragmented pipe changed the decoded sequence")
        require(fragmented.stdout == regular.stdout, "pipe and regular-file outputs differ")

        empty = root / "empty.raw"
        empty.touch()
        clean_eof = run([multimon, "-t", "raw", "-a", "DTMF", str(empty)])
        require(clean_eof.returncode == 0, f"clean EOF failed: {clean_eof.stderr}")

        truncated = root / "truncated.raw"
        truncated.write_bytes(b"x")
        half_sample = run([multimon, "-t", "raw", "-a", "DTMF", str(truncated)])
        require(half_sample.returncode != 0, "half-sample EOF was accepted")
        require("truncated 16-bit sample" in half_sample.stderr, "half-sample error was not explicit")

    print("PASS: installed gen -> fragmented inherited pipe -> multimon consumer workflow")
    print("PASS: regular input, clean EOF, and truncated-sample EOF semantics")


if __name__ == "__main__":
    main()
