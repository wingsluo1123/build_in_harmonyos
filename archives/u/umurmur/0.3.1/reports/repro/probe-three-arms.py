#!/usr/bin/env python3
"""Run the uMurmur path-B three-arm experiment on HarmonyOS PC."""

import argparse
import os
import pathlib
import signal
import socket
import ssl
import struct
import subprocess
import tempfile
import time


def unused_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def connect_tls(port):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection(("127.0.0.1", port), timeout=3)
    wrapped = context.wrap_socket(raw, server_hostname="localhost")
    wrapped.settimeout(1)
    return wrapped


def wait_for_tls(process, port, log_path):
    deadline = time.monotonic() + 15
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            return connect_tls(port)
        except (OSError, ssl.SSLError) as error:
            last_error = error
            time.sleep(0.1)
    detail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
    raise AssertionError(f"TLS listener unavailable ({last_error}):\n{detail}")


def read_exact(stream, size):
    data = b""
    while len(data) < size:
        part = stream.recv(size - len(data))
        if not part:
            raise EOFError(f"needed {size} bytes, got {len(data)}")
        data += part
    return data


def read_frame(stream):
    message_type, length = struct.unpack(">HI", read_exact(stream, 6))
    return message_type, read_exact(stream, length)


def process_ticks(pid):
    stat = pathlib.Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    fields = stat[stat.rfind(")") + 2 :].split()
    return int(fields[11]) + int(fields[12])


def idle_ticks(process, port):
    idle = socket.create_connection(("127.0.0.1", port), timeout=3)
    try:
        time.sleep(0.2)
        before = process_ticks(process.pid)
        time.sleep(1.0)
        after = process_ticks(process.pid)
        return after - before
    finally:
        idle.close()


def stop_process(process):
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def run_arm(binary, config, arm, tmp):
    port = unused_port()
    log_path = tmp / f"arm-{arm}.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                str(binary),
                "-d",
                "-c",
                str(config),
                "-a",
                "127.0.0.1",
                "-b",
                str(port),
                "-A",
                "::1",
                "-B",
                str(port),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            client = wait_for_tls(process, port, log_path)
            try:
                if arm in ("a", "b"):
                    try:
                        read_frame(client)
                    except socket.timeout:
                        pass
                    else:
                        raise AssertionError(f"Arm {arm.upper()} unexpectedly sent Version")
                else:
                    message_type, payload = read_frame(client)
                    assert message_type == 0, message_type
                    assert b"0.3.1" in payload, payload
            finally:
                client.close()

            ticks = None if arm == "a" else idle_ticks(process, port)
            return ticks
        finally:
            stop_process(process)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm-a", required=True, type=pathlib.Path)
    parser.add_argument("--arm-b", required=True, type=pathlib.Path)
    parser.add_argument("--arm-c", required=True, type=pathlib.Path)
    parser.add_argument("--config", required=True, type=pathlib.Path)
    args = parser.parse_args()

    binaries = {arm: getattr(args, f"arm_{arm}").resolve() for arm in "abc"}
    for binary in binaries.values():
        if not binary.is_file():
            raise SystemExit(f"missing experiment ELF: {binary}")
    installed_config = args.config.resolve()
    if not installed_config.is_file():
        raise SystemExit(f"missing configuration template: {installed_config}")

    openssl = os.environ.get("OPENSSL", "openssl")
    with tempfile.TemporaryDirectory(prefix="umurmur-three-arm-") as name:
        tmp = pathlib.Path(name)
        certificate = tmp / "cert.pem"
        key = tmp / "key.pem"
        subprocess.run(
            [
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
                str(certificate),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "OPENSSL_CONF": os.devnull},
        )
        config_text = installed_config.read_text(encoding="utf-8")
        config_text = config_text.replace("/etc/umurmur/cert.crt", str(certificate))
        config_text = config_text.replace("/etc/umurmur/key.key", str(key))
        config_text += f'\nlogfile = "{tmp / "daemon.log"}";\n'
        config = tmp / "umurmur.conf"
        config.write_text(config_text, encoding="utf-8")

        run_arm(binaries["a"], config, "a", tmp)
        print("ARM_A_PASS tls_handshake_ok_server_first_version_timeout")
        arm_b_ticks = run_arm(binaries["b"], config, "b", tmp)
        print(f"ARM_B_PASS still_times_out_and_busy_poll_ticks={arm_b_ticks}")
        arm_c_ticks = run_arm(binaries["c"], config, "c", tmp)
        print(f"ARM_C_PASS version_delivered_idle_ticks={arm_c_ticks}")

        assert arm_b_ticks >= 20, f"Arm B did not reproduce busy polling: {arm_b_ticks}"
        assert arm_c_ticks <= 10, f"Arm C consumed unexpected idle CPU: {arm_c_ticks}"
        assert arm_b_ticks >= arm_c_ticks + 20, (arm_b_ticks, arm_c_ticks)
        print("THREE_ARM_PASS")


if __name__ == "__main__":
    main()
