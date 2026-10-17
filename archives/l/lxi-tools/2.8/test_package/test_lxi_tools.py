#!/usr/bin/env python3
"""End-to-end tests for the packaged lxi and lxi-gui executables."""

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


class Instrument(threading.Thread):
    def __init__(self, chunks, delay=0.08, keep_open=0.0):
        super().__init__(daemon=True)
        self.chunks = chunks
        self.delay = delay
        self.keep_open = keep_open
        self.ready = threading.Event()
        self.error = None
        self.port = None

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                self.port = listener.getsockname()[1]
                self.ready.set()
                connection, _ = listener.accept()
                with connection:
                    command = bytearray()
                    while not command.endswith(b"\n"):
                        part = connection.recv(4096)
                        if not part:
                            raise RuntimeError("client closed before sending the SCPI command")
                        command.extend(part)
                    if b"?" not in command:
                        raise RuntimeError("test query did not contain a question mark")
                    for chunk in self.chunks:
                        if self.delay:
                            time.sleep(self.delay)
                        connection.sendall(chunk)
                    if self.keep_open:
                        time.sleep(self.keep_open)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:  # pragma: no cover - surfaced in the caller
            self.error = exc
            self.ready.set()


def run_query(executable, chunks, timeout_seconds=2, keep_open=0.0, process_timeout=5):
    server = Instrument(chunks, keep_open=keep_open)
    server.start()
    assert server.ready.wait(3), "fake instrument did not start"
    assert server.error is None, str(server.error)
    command = [
        executable,
        "scpi",
        "--address",
        "127.0.0.1",
        "--port",
        str(server.port),
        "--timeout",
        str(timeout_seconds),
        "--raw",
        "*IDN?",
    ]
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, timeout=process_timeout, check=False)
    elapsed = time.monotonic() - started
    server.join(timeout=max(3, keep_open + 1))
    assert server.error is None, str(server.error)
    return result, elapsed


def inspect_elf(readelf, binary, expect_ohos):
    header = subprocess.run([readelf, "-h", binary], capture_output=True, text=True, check=True).stdout
    sections = subprocess.run([readelf, "-SW", binary], capture_output=True, text=True, check=True).stdout
    dynamic = subprocess.run([readelf, "-d", binary], capture_output=True, text=True, check=True).stdout
    assert "AArch64" in header if expect_ohos else "ELF" in header
    if expect_ohos:
        assert sections.count(".codesign") == 1, binary
    assert "RPATH" not in dynamic and "RUNPATH" not in dynamic, binary
    assert ".conan2" not in Path(binary).read_bytes().decode("latin1"), binary


def main():
    package = Path(sys.argv[1])
    executable = str(package / "bin" / "lxi")
    gui = str(package / "bin" / "lxi-gui")
    expect_ohos = os.environ.get("LXI_EXPECT_OHOS") == "1"
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    assert Path(executable).is_file(), executable
    assert Path(gui).is_file(), "the upstream-default GUI was not packaged"
    assert readelf, "readelf is required"

    version = subprocess.run([executable, "--version"], capture_output=True, text=True, check=True)
    assert "lxi v2.8" in version.stdout, version.stdout
    gui_help = subprocess.run([gui, "--help"], capture_output=True, text=True, check=False)
    assert gui_help.returncode == 0, gui_help.stderr
    assert "Usage:" in gui_help.stdout, gui_help.stdout
    inspect_elf(readelf, executable, expect_ohos)
    inspect_elf(readelf, gui, expect_ohos)

    if expect_ohos:
        param = shutil.which("param")
        assert param, "HarmonyOS param tool is required"
        identity = subprocess.run(
            [param, "get", "const.ohos.fullname"], capture_output=True, text=True, check=True
        )
        assert identity.stdout.strip(), "HarmonyOS identity was empty"

    result, _ = run_query(executable, [b"ACME,", b"MODEL", b"\n"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == b"ACME,MODEL\n", result.stdout

    block = b"#15A\x00B\nC"
    result, _ = run_query(executable, [b"#", b"1", b"5", b"A\x00", b"B\nC"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == block, result.stdout

    result, elapsed = run_query(executable, [b"READY", b"\n"], keep_open=1.5)
    assert result.returncode == 0 and result.stdout == b"READY\n"
    assert elapsed < 1.0, "client waited for a persistent connection to close"

    invalid_cases = [
        ([b"#x"], "non-digit block header"),
        ([b"#0indefinite"], "indefinite block on persistent RAW"),
        ([b"#2A1"], "non-digit block length field"),
        ([b"#75242880"], "declared block larger than response limit"),
        ([b"#15A"], "premature EOF"),
    ]
    for chunks, name in invalid_cases:
        result, _ = run_query(executable, chunks)
        assert result.returncode != 0, name

    result, elapsed = run_query(
        executable, [b"PARTIAL"], timeout_seconds=1, keep_open=1.5, process_timeout=4
    )
    assert result.returncode != 0, "unterminated text response was accepted"
    assert 0.7 <= elapsed < 2.5, elapsed

    print("lxi-tools consumer scenarios: 14/14 PASS")


if __name__ == "__main__":
    main()
