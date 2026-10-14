#!/usr/bin/env python3
"""Generate tests/fixture.pcap — the deterministic capture used by the
consumer E2E tests in run_e2e.sh.

Contents: one ICMP echo request and one ICMP echo reply between
192.0.2.10 (02:00:00:00:00:01) and 192.0.2.20 (02:00:00:00:00:02),
payload "OHPC-SNORT-E2E".  Written with little-endian pcap timestamps and
Ethernet/IPv4/ICMP checksums computed in full, so the capture is stable,
self-contained and independent of any external tooling.

Regenerate with:  python3 gen_fixture.py   (writes fixture.pcap in cwd)
"""
import struct


def checksum(data):
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def icmp_echo(icmp_type, icmp_id, seq, payload):
    header = struct.pack("!BBHHH", icmp_type, 0, 0, icmp_id, seq)
    csum = checksum(header + payload)
    return struct.pack("!BBHHH", icmp_type, 0, csum, icmp_id, seq) + payload


def ipv4(src, dst, proto, payload):
    def pack(csum):
        return struct.pack(
            "!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), 0x1234, 0, 64,
            proto, csum, bytes(map(int, src.split("."))),
            bytes(map(int, dst.split("."))))
    header = pack(0)
    return pack(checksum(header)) + payload


def ethernet(src_mac, dst_mac, payload):
    # Ethernet II lays the header out as [dst][src]; write dst first.
    return (bytes.fromhex(dst_mac.replace(":", ""))
            + bytes.fromhex(src_mac.replace(":", ""))
            + struct.pack("!H", 0x0800) + payload)


def main():
    mac_a, mac_b = "02:00:00:00:00:01", "02:00:00:00:00:02"
    ip_a, ip_b = "192.0.2.10", "192.0.2.20"
    payload = b"OHPC-SNORT-E2E" + b"\x00" * 4
    request = ethernet(mac_a, mac_b,
                       ipv4(ip_a, ip_b, 1, icmp_echo(8, 0x1234, 1, payload)))
    reply = ethernet(mac_b, mac_a,
                     ipv4(ip_b, ip_a, 1, icmp_echo(0, 0x1234, 1, payload)))

    with open("fixture.pcap", "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for i, pkt in enumerate((request, reply)):
            f.write(struct.pack("<IIII", 1700000000 + i, 0,
                                len(pkt), len(pkt)))
            f.write(pkt)


if __name__ == "__main__":
    main()
