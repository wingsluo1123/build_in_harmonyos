#!/usr/bin/env python3
"""Consumer test: the installed pwncat application must work.

Exercises the packaged ``bin/pwncat`` end to end — the CLI contract
(``--version`` / ``--help``) and a real netcat-style TCP round trip over the
loopback interface driven by the installed executable. Run by
``test_package/conanfile.py`` via ``self.run``.

The executable is always launched as ``sys.executable <script>`` so the test
does not depend on a ``python3`` being on ``PATH`` (the packaged artifact keeps
its upstream ``#!/usr/bin/env python3`` shebang, which is asserted separately in
the OHOS test).
"""

import os
import socket
import subprocess
import sys
import time


def _free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait_listening(port, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def main(argv):
    package_folder = argv[1] if len(argv) > 1 else ""
    script = os.path.join(package_folder, "bin", "pwncat")
    assert os.path.isfile(script), "missing packaged executable: " + script
    assert os.access(script, os.X_OK), "packaged executable is not executable: " + script

    def run(*args, **kwargs):
        return subprocess.run([sys.executable, script] + list(args),
                              capture_output=True, timeout=60, **kwargs)

    # --- CLI contract, as declared by the upstream argparse surface ---
    version = run("--version", text=True)
    assert version.returncode == 0, (version.returncode, version.stderr)
    assert "0.1.2" in version.stdout, version.stdout
    assert "pwncat" in version.stdout.lower(), version.stdout

    helptext = run("--help", text=True)
    assert helptext.returncode == 0, (helptext.returncode, helptext.stderr)
    assert "usage: pwncat" in helptext.stdout, helptext.stdout[:200]
    # every documented mode must be advertised on the packaged build
    for mode in ("-l, --listen", "-z, --zero", "-L [addr:]port",
                 "-R addr:port", "--self-inject"):
        assert mode in helptext.stdout, "missing CLI mode: " + mode

    # --- real netcat-style data transfer through the packaged executable ---
    port = _free_port()
    # -k keeps the listener re-accepting, so the readiness probe below cannot
    # consume the single connection the payload needs.
    server = subprocess.Popen(
        [sys.executable, script, "-k", "-l", "127.0.0.1", str(port)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        assert _wait_listening(port), "packaged pwncat listener never came up"
        payload = b"pwncat consumer 0.1.2 roundtrip\n"
        client = subprocess.run(
            [sys.executable, script, "127.0.0.1", str(port)],
            input=payload, capture_output=True, timeout=60,
        )
        assert client.returncode == 0, (client.returncode, client.stderr[-400:])
        time.sleep(0.4)
        server.kill()
        received, _ = server.communicate(timeout=30)
        assert received == payload, (received, payload)
    finally:
        if server.poll() is None:
            server.kill()
            server.wait(timeout=30)

    print("OK: pwncat 0.1.2 consumer test passed")


if __name__ == "__main__":
    main(sys.argv)
