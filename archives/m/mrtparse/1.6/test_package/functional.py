"""Consume the selected mrtparse module; no signal or decoder shims."""

import hashlib
import io
import json
import pathlib
import platform
import socket
import struct
import sys
import unittest

module_root = pathlib.Path(sys.argv[1]).resolve()
report_path = pathlib.Path(sys.argv[2])
sys.path.insert(0, str(module_root))
sys.dont_write_bytecode = True
import mrtparse

assert pathlib.Path(mrtparse.__file__).resolve().parent == module_root / "mrtparse"
assert mrtparse.__version__ == "1.6"


def record(kind, payload, subtype=4):
    return struct.pack("!IHHI", 1600000000, kind, subtype, len(payload)) + payload


def payload(subtype=4, ipv6=False, state=False):
    as4 = subtype in (4, 5, 7)
    peer_as, local_as = (65536, 65537) if as4 else (64512, 64513)
    afi = 2 if ipv6 else 1
    af = socket.AF_INET6 if ipv6 else socket.AF_INET
    peer_ip, local_ip = ("2001:db8::1", "2001:db8::2") if ipv6 else ("192.0.2.1", "192.0.2.2")
    data = struct.pack("!IIHH" if as4 else "!HHHH", peer_as, local_as, 0, afi)
    data += socket.inet_pton(af, peer_ip) + socket.inet_pton(af, local_ip)
    data += struct.pack("!HH", 1, 6) if state else b"\xff" * 16 + struct.pack("!HB", 19, 4)
    return data, (str(peer_as), str(local_as), peer_ip, local_ip)


def read(raw):
    reader = mrtparse.Reader(io.BytesIO(raw))
    try:
        return [item.mrt for item in reader]
    finally:
        reader.f.close()


class Consumer(unittest.TestCase):
    def test_plain_extended_keepalive(self):
        # Shared decoder covers AS2/AS4, local/nonlocal, IPv4/IPv6.
        for subtype in (1, 4, 6, 7):
            for ipv6 in (False, True):
                with self.subTest(subtype=subtype, ipv6=ipv6):
                    data, expected = payload(subtype, ipv6)
                    plain = read(record(16, data, subtype))[0]
                    extended = read(record(17, struct.pack("!I", 123456) + data, subtype))[0]
                    for item in (plain, extended):
                        self.assertIsNone(item.err)
                        self.assertEqual((item.bgp.peer_as, item.bgp.local_as,
                                          item.bgp.peer_ip, item.bgp.local_ip), expected)
                        self.assertEqual((item.bgp.msg.type, item.bgp.msg.len), (4, 19))
                        self.assertEqual(item.bgp.buf, data)
                    self.assertIsNone(plain.micro_ts)
                    self.assertEqual(extended.micro_ts, 123456)
                    self.assertEqual(extended.buf, record(17, struct.pack("!I", 123456) + data, subtype))

    def test_state_change(self):
        for subtype in (0, 5):
            with self.subTest(subtype=subtype):
                data, expected = payload(subtype, state=True)
                for kind in (16, 17):
                    body = data if kind == 16 else struct.pack("!I", 999999) + data
                    item = read(record(kind, body, subtype))[0]
                    self.assertIsNone(item.err)
                    self.assertEqual((item.bgp.peer_as, item.bgp.local_as,
                                      item.bgp.peer_ip, item.bgp.local_ip), expected)
                    self.assertEqual((item.bgp.old_state, item.bgp.new_state), (1, 6))
                    self.assertEqual(item.micro_ts, None if kind == 16 else 999999)

    def test_short_timestamp(self):
        for size in range(4):
            with self.subTest(size=size):
                raw = record(17, b"\x00" * size)
                item = read(raw)[0]
                self.assertEqual(item.err, mrtparse.MRT_ERR_C["MRT Data Error"])
                self.assertIn("timestamp length %d < 4 byte" % size, item.err_msg)
                self.assertEqual(item.buf, raw)

    def test_missing_bgp_header(self):
        item = read(record(17, struct.pack("!I", 123456)))[0]
        self.assertEqual(item.micro_ts, 123456)
        self.assertEqual(item.err, mrtparse.MRT_ERR_C["MRT Data Error"])
        self.assertIn("Insufficient buffer", item.err_msg)

    def test_consecutive_record_alignment(self):
        data, _ = payload()
        records = [record(17, struct.pack("!I", 0) + data), record(16, data),
                   record(17, struct.pack("!I", 123456) + data)]
        items = read(b"".join(records))
        self.assertEqual(len(items), 3)
        self.assertEqual([item.micro_ts for item in items], [0, None, 123456])
        self.assertEqual([item.buf for item in items], records)
        for item in items:
            self.assertIsNone(item.err)
            self.assertEqual((item.bgp.msg.type, item.bgp.msg.len), (4, 19))


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Consumer))
report = {
    "platform": platform.platform(), "python": sys.version,
    "module_path": mrtparse.__file__,
    "module_sha256": hashlib.sha256(pathlib.Path(mrtparse.__file__).read_bytes()).hexdigest(),
    "tests_run": result.testsRun, "failures": len(result.failures),
    "errors": len(result.errors), "skipped": len(result.skipped),
    "successful": result.wasSuccessful(),
    "counting": "5 unittest consumer methods; subtests and assertions are not additional consumers",
}
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
