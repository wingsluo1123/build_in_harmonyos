#!/usr/bin/env python3
"""Black-box RTP/MPEG-TS tests for the installed tsdecrypt executable."""

import os
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time


def ts_payload(packet_count=7, fill_base=0):
    packets = []
    for counter in range(packet_count):
        fill = (fill_base + counter) & 0xFF
        packets.append(bytes((0x47, 0x1F, 0xFF, 0x10 | counter)) + bytes([fill]) * 184)
    return b"".join(packets)


def rtp_packet(payload, *, seq=1, csrc=(), extension=None, padding=0,
               payload_type=33, marker=False, version=2):
    first = (version << 6) | len(csrc)
    if extension is not None:
        first |= 0x10
    if padding:
        first |= 0x20
    second = payload_type | (0x80 if marker else 0)
    packet = bytearray(struct.pack("!BBHII", first, second, seq, 0x01020304, 0x11223344))
    for value in csrc:
        packet.extend(struct.pack("!I", value))
    if extension is not None:
        profile, data = extension
        if len(data) % 4:
            raise ValueError("extension data must use 32-bit words")
        packet.extend(struct.pack("!HH", profile, len(data) // 4))
        packet.extend(data)
    packet.extend(payload)
    if padding:
        packet.extend(bytes(padding - 1))
        packet.append(padding)
    return bytes(packet)


def free_udp_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def run_case(binary, name, datagram, expected):
    port = free_udp_port()
    with tempfile.TemporaryDirectory(prefix="tsdecrypt-test-") as tempdir:
        output = os.path.join(tempdir, "out.ts")
        log = os.path.join(tempdir, "tsdecrypt.log")
        command = [
            binary,
            "--input", "127.0.0.1:{}".format(port),
            "--input-rtp",
            "--input-ignore-disc",
            "--output", "file://{}".format(output),
            "--const-cw", "a1a2a3a4a5a6a7a8b1b2b3b4b5b6b7b8",
            "--no-output-filter",
            "--log-file", log,
        ]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            time.sleep(0.50)
            if process.poll() is not None:
                raise AssertionError("{}: daemon exited before input".format(name))
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.sendto(datagram, ("127.0.0.1", port))
            filler_payload = ts_payload(fill_base=0x80)
            filler = rtp_packet(filler_payload, seq=2)
            filler_count = 160
            for index in range(filler_count):
                sender.sendto(filler, ("127.0.0.1", port))
                time.sleep(0.002)
            sender.close()
            minimum_size = len(expected) + len(filler_payload) * 100
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if os.path.exists(output) and os.path.getsize(output) >= minimum_size:
                    break
                time.sleep(0.02)
        finally:
            process.send_signal(signal.SIGTERM)
            try:
                _, stderr = process.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr = process.communicate(timeout=2)
                raise AssertionError("{}: daemon did not terminate".format(name))
        if process.returncode != 0:
            raise AssertionError("{}: exit {}: {}".format(
                name, process.returncode, stderr.decode("utf-8", "replace")))
        actual = b""
        if os.path.exists(output):
            with open(output, "rb") as stream:
                actual = stream.read()
        suffix = actual[len(expected):] if actual.startswith(expected) else b""
        repeated_fillers = filler_payload * (
            (len(suffix) + len(filler_payload) - 1) // len(filler_payload)
        )
        valid_suffix = (
            suffix == repeated_fillers[:len(suffix)]
            and len(filler_payload) * 100 <= len(suffix) <= len(filler_payload) * filler_count
        )
        if not actual.startswith(expected) or not valid_suffix:
            log_text = ""
            if os.path.exists(log):
                with open(log, "r", encoding="utf-8", errors="replace") as stream:
                    log_text = stream.read()
            raise AssertionError(
                "{}: expected prefix {} plus 100..{} marked fillers, got {} bytes\n{}".format(
                    name, len(expected), filler_count, len(actual), log_text))
        print("PASS {}".format(name))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_rtp_input.py /path/to/tsdecrypt")
    binary = os.path.abspath(sys.argv[1])
    payload = ts_payload()

    valid = [
        ("base_header", rtp_packet(payload), payload),
        ("marker_bit", rtp_packet(payload, marker=True), payload),
        ("two_csrc", rtp_packet(payload, csrc=(0xAABBCCDD, 0x01020304)), payload),
        ("zero_word_extension", rtp_packet(payload, extension=(0x1000, b"")), payload),
        ("split_extension", rtp_packet(payload, extension=(0x1000, b"abcdefgh")), payload),
        ("padding", rtp_packet(payload, padding=16), payload),
        ("csrc_extension_padding", rtp_packet(
            payload, csrc=(0xAABBCCDD,), extension=(0xABCD, b"abcd"), padding=8), payload),
    ]

    bad_sync = bytearray(payload)
    bad_sync[188 * 3] = 0x46
    malformed = [
        ("wrong_version", rtp_packet(payload, version=1)),
        ("wrong_payload_type", rtp_packet(payload, payload_type=32)),
        ("truncated_csrc", rtp_packet(payload, csrc=(0xAABBCCDD,))[:14]),
        ("truncated_extension_header", rtp_packet(
            payload, extension=(0x1000, b"abcd"))[:14]),
        ("extension_beyond_datagram", bytes.fromhex("90210001010203041122334410000002") + b"abcd"),
        ("zero_padding", bytes((0xA0, 33)) + rtp_packet(payload)[2:] + b"\x00"),
        ("padding_beyond_datagram", bytes((0xA0, 33)) + rtp_packet(payload)[2:] + bytes((0xFF,))),
        ("unaligned_payload", rtp_packet(payload + b"x")),
        ("bad_later_ts_sync", rtp_packet(bytes(bad_sync))),
        ("oversized_payload", rtp_packet(payload + ts_payload(1))),
    ]

    for name, packet, expected in valid:
        run_case(binary, name, packet, expected)
    for name, packet in malformed:
        run_case(binary, name, packet, b"")

    print("RTP/MPEG-TS assertions: {}/{} passed".format(
        len(valid) + len(malformed), len(valid) + len(malformed)))


if __name__ == "__main__":
    main()
