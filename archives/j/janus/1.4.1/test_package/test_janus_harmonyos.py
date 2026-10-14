#!/usr/bin/env python3
"""Run Janus REST and WebSocket integration checks on an attached HarmonyOS device."""

import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import shlex
import socket
import struct
import subprocess
import tarfile
import tempfile
import time
import uuid


def hdc_command(executable, target, *args, check=True):
    command = [executable]
    if target:
        command.extend(["-t", target])
    command.extend(args)
    result = subprocess.run(command, capture_output=True, text=True, errors="replace")
    if check and result.returncode:
        raise RuntimeError(
            f"HDC command failed ({result.returncode}): {command}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def copy_runtime_libraries(package_roots, stage):
    target_lib = stage / "lib"
    target_lib.mkdir(parents=True, exist_ok=True)
    copied = set()
    for package_root in package_roots:
        root = Path(package_root)
        for lib_root in (root / "lib", root / "lib64"):
            if not lib_root.exists():
                continue
            for source in lib_root.rglob("*.so*"):
                if not source.is_file():
                    continue
                destination = target_lib / source.name
                if destination.name in copied:
                    continue
                shutil.copy2(source, destination)
                copied.add(destination.name)
    if not copied:
        raise RuntimeError("Conan dependencies supplied no shared libraries for device runtime")


def write_device_configs(stage, remote_root, http_port=18088, ws_port=18188):
    config_dir = stage / "etc" / "janus"
    config_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir = f"{remote_root}/lib/janus/plugins"
    transport_dir = f"{remote_root}/lib/janus/transports"
    event_dir = f"{remote_root}/lib/janus/events"
    logger_dir = f"{remote_root}/lib/janus/loggers"
    (config_dir / "janus.jcfg").write_text(
        "general: {\n"
        f'  configs_folder = "{remote_root}/etc/janus";\n'
        f'  plugins_folder = "{plugin_dir}";\n'
        f'  transports_folder = "{transport_dir}";\n'
        f'  events_folder = "{event_dir}";\n'
        f'  loggers_folder = "{logger_dir}";\n'
        "  log_to_stdout = true;\n"
        "  debug_level = 4;\n"
        "}\n",
        encoding="utf-8",
    )
    (config_dir / "janus.transport.http.jcfg").write_text(
        'general: { json = "compact"; base_path = "/janus"; http = true; '
        f'port = {http_port}; ip = "127.0.0.1"; https = false; }}\n'
        'admin: { admin_http = false; admin_https = false; }\n',
        encoding="utf-8",
    )
    (config_dir / "janus.transport.websockets.jcfg").write_text(
        f'general: {{ json = "compact"; ws = true; ws_port = {ws_port}; '
        'ws_ip = "127.0.0.1"; wss = false; }\n'
        'admin: { admin_ws = false; admin_wss = false; }\n',
        encoding="utf-8",
    )
    for plugin in ("echotest", "videocall", "videoroom"):
        (config_dir / f"janus.plugin.{plugin}.jcfg").write_text(
            "general: { events = false; }\n", encoding="utf-8"
        )


def send_http(port, method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if body is not None else {}
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        if response.status != 200:
            raise RuntimeError(f"HTTP {method} {path}: {response.status}: {data[:400]!r}")
        return json.loads(data.decode("utf-8")) if data else {}
    finally:
        connection.close()


def expect_janus_reply(reply, accepted, action):
    status = reply.get("janus")
    if status not in accepted:
        raise RuntimeError(f"Janus {action} returned {reply!r}")


def require_enabled_modules(info):
    expected = {
        "plugins": {
            "janus.plugin.echotest",
            "janus.plugin.videocall",
            "janus.plugin.videoroom",
        },
        "transports": {"janus.transport.http", "janus.transport.websockets"},
    }
    for section, required in expected.items():
        entries = info.get(section)
        if isinstance(entries, dict):
            actual = set(entries)
        elif isinstance(entries, list):
            actual = {
                item if isinstance(item, str) else item.get("name")
                for item in entries
                if isinstance(item, (str, dict))
            }
        else:
            actual = set()
        missing = required - actual
        if missing:
            raise RuntimeError(
                f"Janus {section} missing from live server info: {sorted(missing)}; "
                f"available: {sorted(name for name in actual if name)}"
            )


def test_rest(http_port, info):
    if info.get("janus") not in ("server_info", "success"):
        raise RuntimeError(f"Unexpected REST info response: {info!r}")
    require_enabled_modules(info)

    created = send_http(
        http_port,
        "POST",
        "/janus",
        {"janus": "create", "transaction": uuid.uuid4().hex},
    )
    expect_janus_reply(created, {"success"}, "session create")
    session_id = created["data"]["id"]
    handle_id = None
    try:
        attached = send_http(
            http_port,
            "POST",
            f"/janus/{session_id}",
            {
                "janus": "attach",
                "plugin": "janus.plugin.echotest",
                "transaction": uuid.uuid4().hex,
            },
        )
        expect_janus_reply(attached, {"success"}, "EchoTest attach")
        handle_id = attached["data"]["id"]
    finally:
        if handle_id is not None:
            detached = send_http(
                http_port,
                "POST",
                f"/janus/{session_id}/{handle_id}",
                {"janus": "detach", "transaction": uuid.uuid4().hex},
            )
            expect_janus_reply(detached, {"success"}, "EchoTest detach")
        destroyed = send_http(
            http_port,
            "POST",
            f"/janus/{session_id}",
            {"janus": "destroy", "transaction": uuid.uuid4().hex},
        )
        expect_janus_reply(destroyed, {"success"}, "session destroy")


def recv_exact(sock, length):
    data = bytearray()
    while len(data) < length:
        part = sock.recv(length - len(data))
        if not part:
            raise RuntimeError("WebSocket closed while reading a frame")
        data.extend(part)
    return bytes(data)


def send_ws_text(sock, text):
    send_ws_frame(sock, 1, text.encode("utf-8"))


def send_ws_frame(sock, opcode, payload):
    mask = secrets.token_bytes(4)
    length = len(payload)
    if length < 126:
        header = bytes([0x80 | opcode, 0x80 | length])
    elif length < 65536:
        header = bytes([0x80 | opcode, 0x80 | 126]) + struct.pack("!H", length)
    else:
        header = bytes([0x80 | opcode, 0x80 | 127]) + struct.pack("!Q", length)
    masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    sock.sendall(header + mask + masked)


def recv_ws_frame(sock):
    first, second = recv_exact(sock, 2)
    opcode = first & 0x0F
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", recv_exact(sock, 8))[0]
    mask = recv_exact(sock, 4) if second & 0x80 else None
    payload = recv_exact(sock, length)
    if mask:
        payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    return opcode, payload


def test_websocket(port):
    key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
    expected = base64.b64encode(
        hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
    ).decode("ascii")
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.settimeout(5)
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: 127.0.0.1\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Sec-WebSocket-Protocol: janus-protocol\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        headers = bytearray()
        while b"\r\n\r\n" not in headers:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket closed during upgrade")
            headers.extend(chunk)
        header_text = bytes(headers).split(b"\r\n\r\n", 1)[0].decode("latin1")
        lines = header_text.split("\r\n")
        if not lines[0].startswith("HTTP/1.1 101"):
            raise RuntimeError(f"WebSocket upgrade failed: {header_text}")
        response_headers = {
            line.split(":", 1)[0].strip().lower(): line.split(":", 1)[1].strip()
            for line in lines[1:]
            if ":" in line
        }
        if response_headers.get("sec-websocket-accept") != expected:
            raise RuntimeError("WebSocket Sec-WebSocket-Accept did not match the RFC 6455 value")
        if response_headers.get("sec-websocket-protocol") != "janus-protocol":
            raise RuntimeError("Janus WebSocket subprotocol was not negotiated")

        transaction = uuid.uuid4().hex
        send_ws_text(sock, json.dumps({"janus": "info", "transaction": transaction}))
        while True:
            opcode, payload = recv_ws_frame(sock)
            if opcode == 9:
                send_ws_frame(sock, 10, payload)
                continue
            if opcode == 1:
                reply = json.loads(payload.decode("utf-8"))
                if reply.get("janus") != "server_info" or reply.get("transaction") != transaction:
                    raise RuntimeError(f"Unexpected Janus WebSocket reply: {reply!r}")
                require_enabled_modules(reply)
                return
            if opcode == 8:
                raise RuntimeError("Janus WebSocket closed before replying to info")


def run_native(args):
    temp_root = Path(tempfile.mkdtemp(prefix="janus-native-device-test-"))
    stage = temp_root / "root"
    stage.mkdir()
    shutil.copytree(args.janus_package, stage, dirs_exist_ok=True, symlinks=False)
    copy_runtime_libraries(args.dependency_package, stage)
    http_port = free_port()
    ws_port = free_port()
    write_device_configs(stage, str(stage), http_port=http_port, ws_port=ws_port)

    janus = stage / "bin" / "janus"
    config = stage / "etc" / "janus" / "janus.jcfg"
    log = stage / "janus.log"
    environment = os.environ.copy()
    library_path = [str(stage / "lib")]
    if environment.get("LD_LIBRARY_PATH"):
        library_path.append(environment["LD_LIBRARY_PATH"])
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(library_path)
    process = None
    try:
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [str(janus), "-F", str(config.parent), "-C", str(config)],
                cwd=str(config.parent),
                env=environment,
                stdout=output,
                stderr=subprocess.STDOUT,
            )

        info = None
        deadline = time.monotonic() + 30
        last_error = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                info = send_http(http_port, "GET", "/janus/info")
                break
            except (OSError, RuntimeError, json.JSONDecodeError) as error:
                last_error = error
                time.sleep(0.5)
        if info is None:
            output = log.read_text(encoding="utf-8", errors="replace")[-8000:]
            raise RuntimeError(
                f"Native HarmonyOS Janus REST server did not start: {last_error}\n{output}"
            )

        test_rest(http_port, info)
        test_websocket(ws_port)
        print(
            "HarmonyOS AArch64 Janus integration passed: live HTTP/WebSocket transports, "
            "three enabled plugins, REST session/EchoTest lifecycle, and Janus WebSocket info."
        )
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        shutil.rmtree(temp_root, ignore_errors=True)


def run(args):
    if args.native_device:
        run_native(args)
        return

    hdc = args.hdc or os.environ.get("JANUS_HDC") or shutil.which("hdc")
    target = args.target or os.environ.get("JANUS_HDC_TARGET")
    if not hdc:
        raise RuntimeError("Set JANUS_HDC or install hdc in PATH")
    if not target:
        raise RuntimeError("Set JANUS_HDC_TARGET to the connected HDC device serial")

    token = uuid.uuid4().hex[:10]
    remote_root = f"/data/local/tmp/janus-conan-{token}"
    temp_root = Path(tempfile.mkdtemp(prefix="janus-harmonyos-test-"))
    stage = temp_root / "root"
    stage.mkdir()
    shutil.copytree(args.janus_package, stage, dirs_exist_ok=True, symlinks=False)
    copy_runtime_libraries(args.dependency_package, stage)
    write_device_configs(stage, remote_root)
    archive = temp_root / "janus-device-test.tar"
    with tarfile.open(archive, "w") as stream:
        stream.add(stage, arcname=".")

    remote_archive = remote_root + ".tar"
    http_local = free_port()
    ws_local = free_port()
    http_forwarded = False
    ws_forwarded = False
    process_started = False
    try:
        hdc_command(hdc, target, "shell", "mkdir", "-p", remote_root)
        hdc_command(hdc, target, "file", "send", str(archive), remote_archive)
        hdc_command(
            hdc,
            target,
            "shell",
            "sh",
            "-c",
            f"tar -xf {shlex.quote(remote_archive)} -C {shlex.quote(remote_root)}",
        )
        hdc_command(hdc, target, "fport", f"tcp:{http_local}", "tcp:18088")
        http_forwarded = True
        hdc_command(hdc, target, "fport", f"tcp:{ws_local}", "tcp:18188")
        ws_forwarded = True

        janus = f"{remote_root}/bin/janus"
        config = f"{remote_root}/etc/janus/janus.jcfg"
        log = f"{remote_root}/janus.log"
        pid_file = f"{remote_root}/janus.pid"
        launch = (
            f"cd {shlex.quote(remote_root)} && "
            f"export LD_LIBRARY_PATH={shlex.quote(remote_root + '/lib')} && "
            f"nohup {shlex.quote(janus)} -F {shlex.quote(remote_root + '/etc/janus')} "
            f"-C {shlex.quote(config)} "
            f">{shlex.quote(log)} 2>&1 & echo $! >{shlex.quote(pid_file)}"
        )
        hdc_command(hdc, target, "shell", "sh", "-c", launch)
        process_started = True

        info = None
        deadline = time.monotonic() + 30
        last_error = None
        while time.monotonic() < deadline:
            try:
                info = send_http(http_local, "GET", "/janus/info")
                break
            except (OSError, RuntimeError, json.JSONDecodeError) as error:
                last_error = error
                time.sleep(0.5)
        if info is None:
            log_tail = hdc_command(
                hdc,
                target,
                "shell",
                "sh",
                "-c",
                f"tail -80 {shlex.quote(log)}",
                check=False,
            )
            raise RuntimeError(f"Janus REST server did not start: {last_error}\n{log_tail.stdout}\n{log_tail.stderr}")
        test_rest(http_local, info)
        test_websocket(ws_local)
        print(
            "HarmonyOS Janus integration passed: REST info/create/attach/detach/destroy "
            "and WebSocket janus-protocol info request."
        )
    finally:
        if ws_forwarded:
            hdc_command(hdc, target, "fport", "rm", f"tcp:{ws_local} tcp:18188", check=False)
        if http_forwarded:
            hdc_command(hdc, target, "fport", "rm", f"tcp:{http_local} tcp:18088", check=False)
        if process_started:
            hdc_command(
                hdc,
                target,
                "shell",
                "sh",
                "-c",
                f"if test -f {shlex.quote(remote_root + '/janus.pid')}; then "
                f"kill $(cat {shlex.quote(remote_root + '/janus.pid')}) 2>/dev/null || true; fi",
                check=False,
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--janus-package", required=True)
    parser.add_argument("--dependency-package", action="append", default=[])
    parser.add_argument("--hdc")
    parser.add_argument("--target")
    parser.add_argument("--native-device", action="store_true")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
