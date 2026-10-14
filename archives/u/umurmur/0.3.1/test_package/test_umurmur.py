#!/usr/bin/env python3
"""Target-side uMurmur consumer and protocol-closure tests."""

import os
import pathlib
import re
import shlex
import shutil
import signal
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time


package = pathlib.Path(sys.argv[1]).resolve()
daemon = package / "sbin" / "umurmurd"
installed_config = package / "etc" / "umurmur" / "umurmur.conf"
runner = shlex.split(os.environ.get("UMURMUR_TEST_RUNNER", ""))


def command(*args):
    return runner + [str(daemon), *map(str, args)]


def exact(stream, size):
    data = b""
    while len(data) < size:
        part = stream.recv(size - len(data))
        if not part:
            raise EOFError(f"needed {size} bytes, got {len(data)}")
        data += part
    return data


def read_frame(stream):
    header = exact(stream, 6)
    msg_type, length = struct.unpack(">HI", header)
    return msg_type, exact(stream, length)


def connect_tls(port):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection(("127.0.0.1", port), timeout=3)
    wrapped = context.wrap_socket(raw, server_hostname="localhost")
    wrapped.settimeout(3)
    return wrapped


def unused_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def wait_for_tls(process, port, log_path):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            break
        try:
            return connect_tls(port)
        except (OSError, ssl.SSLError):
            time.sleep(0.1)
    detail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
    raise AssertionError(f"daemon did not accept TLS on port {port}:\n{detail}")


def read_varint(data, offset):
    value = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7


def protobuf_bytes_fields(data):
    fields = {}
    offset = 0
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        number, wire_type = tag >> 3, tag & 7
        assert wire_type == 2, f"unexpected protobuf wire type {wire_type}"
        length, offset = read_varint(data, offset)
        fields[number] = data[offset : offset + length]
        offset += length
    return fields


def xor_bytes(left, right):
    return bytes(a ^ b for a, b in zip(left, right))


def double_block(block):
    value = int.from_bytes(block, "big")
    carry = value >> 127
    value = ((value << 1) & ((1 << 128) - 1)) ^ (0x87 if carry else 0)
    return value.to_bytes(16, "big")


def increment_iv(iv):
    result = bytearray(iv)
    for index in range(len(result)):
        result[index] = (result[index] + 1) & 0xFF
        if result[index] != 0:
            break
    return bytes(result)


def aes_block(openssl, key, block):
    result = subprocess.run(
        runner
        + [openssl, "enc", "-aes-128-ecb", "-K", key.hex(), "-nopad", "-nosalt"],
        input=block,
        capture_output=True,
        check=True,
        env={**os.environ, "OPENSSL_CONF": os.devnull},
    )
    assert len(result.stdout) == 16, result.stderr
    return result.stdout


def ocb_encrypt(openssl, key, nonce, plain):
    assert 0 < len(plain) <= 16
    delta = double_block(aes_block(openssl, key, nonce))
    length_block = (len(plain) * 8).to_bytes(16, "big")
    pad = aes_block(openssl, key, xor_bytes(delta, length_block))
    checksum = plain + pad[len(plain) :]
    encrypted = xor_bytes(pad, checksum)[: len(plain)]
    delta = xor_bytes(delta, double_block(delta))
    tag = aes_block(openssl, key, xor_bytes(delta, checksum))
    return bytes([nonce[0]]) + tag[:3] + encrypted


def ocb_decrypt(openssl, key, nonce, packet):
    assert packet[0] == nonce[0]
    encrypted = packet[4:]
    assert 0 < len(encrypted) <= 16
    delta = double_block(aes_block(openssl, key, nonce))
    length_block = (len(encrypted) * 8).to_bytes(16, "big")
    pad = aes_block(openssl, key, xor_bytes(delta, length_block))
    checksum = xor_bytes(encrypted + bytes(16 - len(encrypted)), pad)
    plain = checksum[: len(encrypted)]
    delta = xor_bytes(delta, double_block(delta))
    tag = aes_block(openssl, key, xor_bytes(delta, checksum))
    assert packet[1:4] == tag[:3], "invalid Mumble OCB authentication tag"
    return plain


assert daemon.is_file(), f"missing packaged daemon: {daemon}"
assert installed_config.is_file(), f"missing installed configuration: {installed_config}"
readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
assert readelf, "readelf is required to validate the OHOS executable signature"
sections = subprocess.run(
    [readelf, "-SW", daemon], capture_output=True, text=True, check=True
).stdout
assert sections.count(".codesign") == 1, "packaged daemon is not signed exactly once"
dynamic = subprocess.run(
    [readelf, "-d", daemon], capture_output=True, text=True, check=True
).stdout
assert "RPATH" not in dynamic and "RUNPATH" not in dynamic, dynamic
binary_data = daemon.read_bytes()
for forbidden in (b".conan2", b"/home/"):
    assert forbidden not in binary_data, f"build path leaked into ELF: {forbidden!r}"
assert os.fsencode(str(package)) not in binary_data, "package folder leaked into ELF"

help_run = subprocess.run(command("-h"), capture_output=True, text=True)
assert help_run.returncode == 0, help_run.stderr
assert "uMurmur version 0.3.1" in help_run.stdout, help_run.stdout
default_match = re.search(r"default ([^)]+)\)", help_run.stdout)
assert default_match, help_run.stdout
assert pathlib.Path(default_match.group(1)).resolve() == installed_config.resolve(), help_run.stdout

config_run = subprocess.run(
    command("-t", "-c", installed_config), capture_output=True, text=True
)
assert config_run.returncode == 0, config_run.stderr

with tempfile.TemporaryDirectory(prefix="umurmur-test-") as tmp_name:
    tmp = pathlib.Path(tmp_name)
    default_config_run = subprocess.run(
        command("-t"), cwd=tmp, capture_output=True, text=True
    )
    assert default_config_run.returncode == 0, default_config_run.stderr

    malformed_config = tmp / "broken.conf"
    malformed_config.write_text("channels = ( { name = ; } );\n", encoding="utf-8")
    reject_run = subprocess.run(
        command("-t", "-c", malformed_config), capture_output=True, text=True
    )
    assert reject_run.returncode != 0, "malformed configuration was accepted"
    assert "Error in config file" in reject_run.stderr, reject_run.stderr

    openssl = shutil.which("openssl")
    assert openssl, "openssl executable is required to generate the ephemeral test certificate"
    cert = tmp / "cert.pem"
    key = tmp / "key.pem"
    subprocess.run(
        runner
        + [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-subj",
            "/CN=localhost",
            "-days",
            "1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "OPENSSL_CONF": os.devnull},
    )
    config = tmp / "umurmur.conf"
    config_text = installed_config.read_text(encoding="utf-8")
    config_text = config_text.replace("/etc/umurmur/cert.crt", str(cert))
    config_text = config_text.replace("/etc/umurmur/key.key", str(key))
    config_text += f'\nlogfile = "{tmp / "daemon-background.log"}";\n'
    config.write_text(config_text, encoding="utf-8")

    port = unused_port()
    foreground_log_path = tmp / "daemon-foreground.log"
    with foreground_log_path.open("w", encoding="utf-8") as foreground_log:
        foreground = subprocess.Popen(
            command(
                "-d",
                "-c",
                config,
                "-a",
                "127.0.0.1",
                "-b",
                port,
                "-A",
                "::1",
                "-B",
                port,
            ),
            stdout=foreground_log,
            stderr=subprocess.STDOUT,
        )
        try:
            client = wait_for_tls(foreground, port, foreground_log_path)

            # The server must send Version before the client emits an
            # application frame. This regresses the pre-handshake queue bug.
            first_type, first_payload = read_frame(client)
            assert first_type == 0, first_type
            assert b"0.3.1" in first_payload, first_payload

            # Minimal valid protobuf-c Authenticate: field 1, wire type 2.
            username = b"ohos-probe"
            authenticate = b"\x0a" + bytes([len(username)]) + username
            client.sendall(struct.pack(">HI", 2, len(authenticate)) + authenticate)
            received = {first_type}
            crypt_setup = None
            for _ in range(20):
                msg_type, payload = read_frame(client)
                received.add(msg_type)
                if msg_type == 15:
                    crypt_setup = payload
                if 15 in received and 5 in received:
                    break
            assert 15 in received, f"missing CryptSetup, got {received}"
            assert 5 in received, f"missing ServerSync, got {received}"

            # Prove the UDP packet belongs to this authenticated TLS session,
            # not merely to the daemon's public status socket. CryptSetup gives
            # the per-session OCB key and the two initial nonces.
            crypt_fields = protobuf_bytes_fields(crypt_setup)
            key_material = crypt_fields[1]
            client_nonce = crypt_fields[2]
            server_nonce = crypt_fields[3]
            assert len(key_material) == len(client_nonce) == len(server_nonce) == 16
            udp_plain = b"\x20" + struct.pack(">Q", 0x1020304050607080)
            udp_packet = ocb_encrypt(
                openssl, key_material, increment_iv(client_nonce), udp_plain
            )
            session_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            session_udp.settimeout(3)
            session_udp.sendto(udp_packet, ("127.0.0.1", port))
            session_reply, _ = session_udp.recvfrom(64)
            decoded_reply = ocb_decrypt(
                openssl, key_material, increment_iv(server_nonce), session_reply
            )
            assert decoded_reply == udp_plain, (decoded_reply, udp_plain)
            session_udp.close()

            # UDP shares the daemon port with TLS/TCP. Its 12-byte status ping
            # preserves the caller token and appends server state.
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.settimeout(3)
            udp.sendto(
                struct.pack(">III", 0, 0x12345678, 0x90ABCDEF),
                ("127.0.0.1", port),
            )
            response, _ = udp.recvfrom(64)
            assert len(response) == 24, len(response)
            version, high, low, users, maximum, bandwidth = struct.unpack(
                ">IIIIII", response
            )
            assert (high, low) == (0x12345678, 0x90ABCDEF), (high, low)
            assert version != 0 and users >= 1
            assert maximum >= users and bandwidth > 0
            udp.close()

            raw = socket.create_connection(("127.0.0.1", port), timeout=3)
            raw.settimeout(3)
            raw.sendall(b"not a TLS record")
            try:
                rejected = raw.recv(64)
            except ConnectionResetError:
                rejected = b""
            assert rejected == b"", rejected
            raw.close()

            malformed = connect_tls(port)
            assert read_frame(malformed)[0] == 0
            malformed.sendall(struct.pack(">HI", 2, 0x7FFFFFFF))
            try:
                rejected = malformed.recv(1)
            except ConnectionResetError:
                rejected = b""
            assert rejected == b"", rejected
            malformed.close()

            survivor = connect_tls(port)
            assert read_frame(survivor)[0] == 0
            survivor.close()
            client.close()

            foreground.send_signal(signal.SIGTERM)
            assert foreground.wait(timeout=5) == 0
        finally:
            if foreground.poll() is None:
                foreground.terminate()
                try:
                    foreground.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    foreground.kill()
                    foreground.wait()

    # HarmonyOS daemon lifecycle: exercise fork/setsid, PID locking and
    # SIGTERM cleanup separately from the foreground protocol path.
    daemon_port = unused_port()
    pidfile = tmp / "umurmurd.pid"
    parent = subprocess.run(
        command(
            "-c",
            config,
            "-p",
            pidfile,
            "-a",
            "127.0.0.1",
            "-b",
            daemon_port,
            "-A",
            "::1",
            "-B",
            daemon_port,
        ),
        timeout=10,
    )
    assert parent.returncode == 0
    deadline = time.monotonic() + 10
    while not pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert pidfile.exists(), "daemon mode did not create the PID file"
    child_pid = int(pidfile.read_text(encoding="ascii").strip())
    daemon_client = wait_for_tls(None, daemon_port, tmp / "daemon-background.log")
    assert read_frame(daemon_client)[0] == 0
    daemon_client.close()
    os.kill(child_pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while pidfile.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not pidfile.exists(), "SIGTERM did not remove the PID file"

print(
    "uMurmur target closure passed: config + server-first TLS Version + "
    "protobuf auth + session-bound encrypted UDP + UDP status + malformed inputs + "
    "foreground/background SIGTERM"
)
