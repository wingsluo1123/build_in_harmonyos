#!/usr/bin/env python3
"""Test script for lua-resty-dns test_package.

Verifies that the resolver.lua file is correctly packaged:
  1. File exists at expected path
  2. File contains expected DNS resolver content
  3. Key API symbols are present (TYPE_A, TYPE_AAAA, compress_ipv6_addr, etc.)

This test genuinely depends on the package — if the package's lib/ directory
is removed, this test will fail (verified by CI L1e destructive test).
"""
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("FAIL: Missing Lua file path argument")
        sys.exit(1)

    lua_file = sys.argv[1]

    # Check file exists
    if not os.path.exists(lua_file):
        print(f"FAIL: Lua file not found: {lua_file}")
        sys.exit(1)

    # Read and verify content
    with open(lua_file, "r") as f:
        content = f.read()

    # Verify it's the DNS resolver module
    if "dns" not in content.lower():
        print("FAIL: File does not contain DNS resolver content")
        sys.exit(1)

    # Check for key DNS resolver features
    checks = [
        ("ngx.socket.udp", "UDP socket access for DNS queries"),
        ("TYPE_A", "DNS A record type constant"),
        ("TYPE_AAAA", "DNS AAAA record type constant"),
        ("TYPE_CNAME", "DNS CNAME record type constant"),
        ("compress_ipv6_addr", "IPv6 address compression utility"),
        ("expand_ipv6_addr", "IPv6 address expansion utility"),
        ("arpa_str", "Reverse DNS (arpa) string generation"),
        ("reverse_query", "Reverse DNS query method"),
    ]

    for pattern, desc in checks:
        if pattern not in content:
            print(f"FAIL: Missing expected content: {desc} ({pattern})")
            sys.exit(1)

    print(f"PASS: lua-resty-dns resolver.lua verified ({len(content)} bytes)")
    print(f"  File: {lua_file}")


if __name__ == "__main__":
    main()
