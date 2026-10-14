"""Exercise the installed sacc binary against a local Gopher server."""

import os
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path


BINARY = Path(os.environ.get("SACC_BIN", ""))


def request_once(
    selector: bytes, response: bytes, url_path: str, temp_parent: Path | None = None
) -> str:
    received = []
    temporary_directories = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def serve() -> None:
            connection, _ = listener.accept()
            with connection:
                if temp_parent is not None:
                    temporary_directories.extend(temp_parent.glob("sacc-*"))
                data = bytearray()
                while not data.endswith(b"\n"):
                    chunk = connection.recv(1024)
                    if not chunk:
                        break
                    data.extend(chunk)
                received.append(bytes(data))
                connection.sendall(response)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        result = subprocess.run(
            [str(BINARY), f"gopher://127.0.0.1:{port}/{url_path}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env={
                **os.environ,
                "TERM": "xterm",
                **({"TMPDIR": str(temp_parent)} if temp_parent is not None else {}),
            },
        )
        thread.join(timeout=5)

    if result.returncode != 0:
        raise AssertionError(f"sacc failed before completing Gopher request: {result.stderr}")
    if thread.is_alive():
        raise AssertionError("local Gopher server did not finish")
    if received != [selector]:
        raise AssertionError(f"unexpected selector: {received!r}")
    if temp_parent is not None and not temporary_directories:
        raise AssertionError("sacc did not create its working directory under TMPDIR")
    return result.stdout


class InstalledSaccTests(unittest.TestCase):
    def test_binary_installed(self) -> None:
        self.assertTrue(BINARY.is_file(), f"installed sacc binary is missing: {BINARY}")
        print("PASS installed binary")

    @unittest.skipUnless(BINARY.is_file(), 'requires installed binary')
    def test_menu_selector_and_listing(self) -> None:
        output = request_once(
            b"\r\n",
            b"0Fixture text\ttext\t127.0.0.1\t70\r\n.\r\n",
            "1",
        )
        self.assertIn("Txt+Fixture text", output)
        print("PASS menu selector and listing")

    @unittest.skipUnless(BINARY.is_file(), 'requires installed binary')
    def test_text_selector_and_body(self) -> None:
        output = request_once(
            b"text\r\n",
            b"Hello from local Gopher\r\n.\r\n",
            "0text",
        )
        self.assertIn("Hello from local Gopher", output)
        print("PASS text selector and body")

    @unittest.skipUnless(BINARY.is_file(), 'requires installed binary')
    def test_missing_url_is_rejected(self) -> None:
        result = subprocess.run(
            [str(BINARY)], capture_output=True, text=True, timeout=5, check=False
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("usage: sacc URL", result.stderr)
        print("PASS missing URL rejection")

    @unittest.skipUnless(BINARY.is_file(), 'requires installed binary')
    def test_uses_writable_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as path:
            output = request_once(
                b"text\r\n",
                b"Temporary directory check\r\n.\r\n",
                "0text",
                Path(path),
            )
        self.assertIn("Temporary directory check", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
