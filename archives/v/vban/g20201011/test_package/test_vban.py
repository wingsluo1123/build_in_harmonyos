import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import time


ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def tool(bin_dir, name):
    path = os.path.join(bin_dir, name)
    check(os.path.isfile(path) and os.access(path, os.X_OK),
          f"missing packaged command: {path}")
    return path


def free_udp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(5)
    return sock, sock.getsockname()[1]


def version_tests(commands):
    for name, path in commands.items():
        result = subprocess.run([path, "--version"], capture_output=True, text=True,
                                timeout=10, check=False)
        check(result.returncode == 0, f"{name} --version failed: {result.stderr}")
        check("version 2.1.0" in result.stdout, f"unexpected {name} version output")


def text_wire_test(sendtext):
    receiver, port = free_udp_socket()
    message = "HarmonyOS-VBAN"
    result = subprocess.run(
        [sendtext, "-i", "127.0.0.1", "-p", str(port), "-s", "ohos", message],
        capture_output=True, text=True, timeout=10, check=False)
    packet, _ = receiver.recvfrom(2048)
    receiver.close()
    check(result.returncode == 0, f"vban_sendtext failed: {result.stderr}")
    check(packet[:4] == b"VBAN", "VBAN magic is not four explicit wire bytes")
    check(packet[4:8] == bytes((0x40, 0, 0, 1)), "text format bytes differ")
    check(packet[8:24] == b"ohos" + bytes(12), "stream name is not zero padded")
    check(packet[24:28] == bytes(4), "frame number is not little-endian zero")
    check(packet[28:] == message.encode(), "text payload differs")


def golden_audio_decode_test(receptor, root):
    # The upstream CLI stores device paths in a 64-byte field.
    output = root / "g.pcm"
    receiver, port = free_udp_socket()
    receiver.close()
    recv = subprocess.Popen(
        [receptor, "-i", "127.0.0.1", "-p", str(port), "-s", "golden",
         "-b", "file", "-d", output.name], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    stderr_text = ""
    try:
        time.sleep(0.3)
        check(recv.poll() is None, "receptor exited before the golden packet")
        payload = bytes((0x01, 0x80, 0x02, 0x7F, 0x03, 0x80, 0x04, 0x7F))
        header = (b"VBAN" + bytes((16, 1, 1, 1)) +
                  b"golden" + bytes(10) + bytes((0x12, 0x34, 0x56, 0x78)))
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.sendto(header + payload, ("127.0.0.1", port))
        sender.close()
        deadline = time.time() + 5
        while time.time() < deadline and (not output.exists() or output.stat().st_size < len(payload)):
            time.sleep(0.05)
    finally:
        if recv.poll() is None:
            recv.send_signal(signal.SIGINT)
            recv.wait(timeout=5)
        stderr_text = recv.stderr.read()
    check(output.exists(),
          f"receptor rejected the independent golden audio packet: {stderr_text}")
    check(output.read_bytes() == payload,
          "golden packet decode changed the independently encoded payload")


def file_eof_packet_count_test(emitter, root):
    """One finite input must produce one datagram and then terminate at EOF."""
    payload = bytes(range(64))
    # Upstream stores device paths in a fixed 64-byte field.
    source = root / "e.pcm"
    source.write_bytes(payload)
    receiver, port = free_udp_socket()
    result = subprocess.run(
        [emitter, "-i", "127.0.0.1", "-p", str(port), "-s", "eof",
         "-b", "file", "-d", source.name, "-r", "44100", "-n", "2",
         "-f", "16I"], cwd=root, capture_output=True, text=True,
        timeout=5, check=False)
    check(result.returncode == 0, f"file emitter failed at EOF: {result.stderr}")
    packet, _ = receiver.recvfrom(2048)
    receiver.settimeout(0.5)
    extra_packet = None
    try:
        extra_packet, _ = receiver.recvfrom(2048)
    except socket.timeout:
        pass
    finally:
        receiver.close()
    check(extra_packet is None, "file EOF emitted an extra datagram")
    check(packet[:4] == b"VBAN", "finite file packet magic differs")
    check(packet[5] == 15, "finite file packet sample count underflowed")
    check(packet[24:28] == bytes((1, 0, 0, 0)),
          "first finite file frame number is not little-endian one")
    check(packet[28:] == payload, "finite file packet payload differs")


def file_read_error_test(emitter, root):
    """A backend read error must not be reported as successful EOF."""
    source = root / "d"
    source.mkdir()
    receiver, port = free_udp_socket()
    result = subprocess.run(
        [emitter, "-i", "127.0.0.1", "-p", str(port), "-s", "error",
         "-b", "file", "-d", source.name, "-r", "44100", "-n", "2",
         "-f", "16I"], cwd=root, capture_output=True, text=True,
        timeout=5, check=False)
    receiver.settimeout(0.5)
    no_packet = False
    try:
        receiver.recvfrom(2048)
    except socket.timeout:
        no_packet = True
    finally:
        receiver.close()
    check(result.returncode != 0, "file read error was misreported as successful EOF")
    check(no_packet, "file read error emitted a datagram")


def file_loopback_test(emitter, receptor, root):
    payload = bytes((index * 17) & 0xFF for index in range(4096))
    source = root / "input.pcm"
    output = root / "output.pcm"
    source.write_bytes(payload)
    receiver, port = free_udp_socket()
    receiver.close()
    recv = subprocess.Popen(
        [receptor, "-i", "127.0.0.1", "-p", str(port), "-s", "loop",
         "-b", "file", "-d", output.name], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(0.2)
        sent = subprocess.run(
            [emitter, "-i", "127.0.0.1", "-p", str(port), "-s", "loop",
             "-b", "file", "-d", source.name, "-r", "44100", "-n", "2",
             "-f", "16I"], cwd=root, capture_output=True, text=True,
            timeout=10, check=False)
        check(sent.returncode == 0, f"file emitter failed at EOF: {sent.stderr}")
        deadline = time.time() + 5
        while time.time() < deadline and (not output.exists() or output.stat().st_size < len(payload)):
            time.sleep(0.05)
    finally:
        recv.send_signal(signal.SIGINT)
        recv.wait(timeout=5)
    check(output.exists(), "file receptor produced no output")
    check(output.read_bytes() == payload, "UDP file loopback changed PCM bytes")


def pipe_tmpdir_test(emitter, root):
    receiver, port = free_udp_socket()
    env = os.environ.copy()
    env["TMPDIR"] = str(root)
    fifo = root / "vban_0"
    fifo_supported = True
    try:
        os.mkfifo(fifo)
        fifo.unlink()
    except (PermissionError, NotImplementedError):
        fifo_supported = False
    proc = subprocess.Popen(
        [emitter, "-i", "127.0.0.1", "-p", str(port), "-s", "pipe",
         "-b", "pipe", "-r", "44100", "-n", "2", "-f", "16I"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    try:
        if not fifo_supported:
            stderr = proc.communicate(timeout=5)[1]
            check(proc.returncode != 0, "pipe backend hid a filesystem FIFO failure")
            check(str(fifo) in stderr, "pipe failure did not report its TMPDIR path")
            check("/tmp/vban_0" not in stderr, "pipe backend ignored TMPDIR")
            check(any(marker in stderr for marker in
                      ("Permission denied", "Operation not permitted")),
                  "pipe failure did not report a filesystem capability error")
            check(not fifo.exists(), "failed FIFO setup left an artifact")
            return
        deadline = time.time() + 5
        while time.time() < deadline and not fifo.exists():
            time.sleep(0.05)
        check(fifo.exists(), "default FIFO was not created under TMPDIR")
        payload = bytes(range(64))
        with fifo.open("wb", buffering=0) as writer:
            writer.write(payload)
        packet, _ = receiver.recvfrom(2048)
        check(proc.wait(timeout=5) == 0, "pipe emitter did not stop cleanly at EOF")
    finally:
        receiver.close()
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
    check(packet[:4] == b"VBAN", "pipe packet magic differs")
    check(packet[28:] == payload, "pipe packet payload differs")
    check(not fifo.exists(), "FIFO was not removed after close")


def main():
    check(len(sys.argv) == 2, "usage: test_vban.py <package-bin-dir>")
    bin_dir = os.path.abspath(sys.argv[1])
    commands = {name: tool(bin_dir, name) for name in
                ("vban_receptor", "vban_emitter", "vban_sendtext")}
    version_tests(commands)
    text_wire_test(commands["vban_sendtext"])
    with tempfile.TemporaryDirectory(prefix="vban-test-") as directory:
        root = pathlib.Path(directory)
        golden_audio_decode_test(commands["vban_receptor"], root)
        file_eof_packet_count_test(commands["vban_emitter"], root)
        file_read_error_test(commands["vban_emitter"], root)
        file_loopback_test(commands["vban_emitter"], commands["vban_receptor"], root)
        pipe_tmpdir_test(commands["vban_emitter"], root)
    print(f"vban consumer tests passed: {ASSERTIONS} assertions")


if __name__ == "__main__":
    main()
