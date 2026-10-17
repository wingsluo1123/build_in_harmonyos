#!/usr/bin/env python3
"""HarmonyOS-specific consumer test for the installed pwncat application.

Verifies that the packaged ``bin/pwncat`` is the upstream netcat replacement
artifact, that it runs on the OHOS aarch64 runtime, and that two behaviours that
depend on the OHOS networking stack behave as pwncat documents them:

* IPv6 literal endpoints (``::1``) work, which on OHOS is the practical way to
  reach the IPv6 loopback: the runtime's ``/etc/hosts`` maps
  ``::1 ip6-localhost`` but has no ``::1 localhost`` alias, so name-based IPv6
  loopback does not resolve.
* ``--nodns`` on a hostname yields pwncat's controlled ``Resolve Error`` instead
  of an unhandled traceback — the OHOS resolver reports unresolvable names with
  a non-``gaierror`` error code, so this path is worth pinning down.
"""

import os
import platform
import socket
import subprocess
import sys
import time


def _free_port(family):
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.bind(("::1" if family == socket.AF_INET6 else "127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait_listening(family, host, port, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def main(argv):
    package_folder = argv[1] if len(argv) > 1 else ""

    # --- this adaptation targets the OHOS aarch64 POSIX runtime ---
    assert os.name == "posix", os.name
    machine = platform.machine().lower()
    assert machine in {"aarch64", "arm64", "armv8", "armv8l"}, platform.machine()
    system = platform.system()
    assert system in ("HarmonyOS", "OpenHarmony"), (
        "expected a HarmonyOS/OpenHarmony runtime, got {!r}".format(system))

    # --- the packaged artifact is the upstream executable script ---
    script = os.path.join(package_folder, "bin", "pwncat")
    assert os.path.isfile(script), "missing packaged executable: " + script
    assert os.access(script, os.X_OK), "packaged executable is not executable: " + script
    with open(script, encoding="utf-8") as handle:
        shebang = handle.readline().strip()
    assert shebang.startswith("#!") and "python3" in shebang, shebang

    def run(*args, **kwargs):
        return subprocess.run([sys.executable, script] + list(args),
                              capture_output=True, timeout=60, **kwargs)

    version = run("--version", text=True)
    assert version.returncode == 0, (version.returncode, version.stderr)
    assert "0.1.2" in version.stdout, version.stdout

    # --- IPv6 literal (::1) round trip on the OHOS runtime ---
    port6 = _free_port(socket.AF_INET6)
    # -k keeps the listener re-accepting so the readiness probe does not consume
    # the single connection the payload needs.
    server = subprocess.Popen(
        [sys.executable, script, "-6", "-k", "-l", "::1", str(port6)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        assert _wait_listening(socket.AF_INET6, "::1", port6), \
            "packaged pwncat IPv6 listener never came up on ::1"
        payload = b"pwncat ohos ipv6 roundtrip\n"
        client = subprocess.run(
            [sys.executable, script, "-6", "::1", str(port6)],
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

    # --- --nodns on a hostname fails in a controlled way, never a traceback ---
    nodns = run("-n", "-vvvv", "localhost", str(_free_port(socket.AF_INET)),
                text=True)
    assert nodns.returncode != 0, ("expected failure, got", nodns.returncode)
    assert "Resolve Error" in nodns.stderr, nodns.stderr[-400:]
    assert "Traceback" not in nodns.stderr, nodns.stderr[-400:]

    print("OK: pwncat OHOS consumer test passed "
          "(system={}, machine={})".format(system, platform.machine()))


if __name__ == "__main__":
    main(sys.argv)
