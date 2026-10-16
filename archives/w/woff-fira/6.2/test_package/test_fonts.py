#!/usr/bin/env python3
"""Verify the exact Fira Code 6.2 WOFF resource package."""

import hashlib
import pathlib
import struct
import sys


EXPECTED_SHA256 = {
    "FiraCode-Bold.woff": "3760314a6100f7c06569d7dbcb63c6be76e4c758d3119c0a1f4d0f2dfd64b59a",
    "FiraCode-Light.woff": "ece6bdf6821d1c41a5ef8ee901661bf8df0809d074fb3992cd1349b74d4e1b68",
    "FiraCode-Medium.woff": "91f1c9c3eb82cca58221333684cf022e9169849c510158e9f162929d15286b66",
    "FiraCode-Regular.woff": "e4b5a20d572b7f718d64c884e4e48cb7e45303ab50722011469ee2e1964bff6d",
    "FiraCode-SemiBold.woff": "f7f09d47f416331a739641d5c1222fc989e43e7aa254a9fe1977cead0133616c",
    "FiraCode-VF.woff": "6c9de3511811ecb6992835f2a8cc2623cb2a41b47823d954278150bb73c53eaf",
}


def fail(message):
    raise SystemExit(f"[FAIL] {message}")


def main(argv):
    if len(argv) != 1:
        fail("usage: test_fonts.py <conan-package-folder>")

    package = pathlib.Path(argv[0])
    font_dir = package / "share" / "fonts" / "woff-fira" / "woff"
    if not font_dir.is_dir():
        fail(f"WOFF resource directory is missing: {font_dir}")

    actual_names = {path.name for path in font_dir.glob("*.woff")}
    expected_names = set(EXPECTED_SHA256)
    if actual_names != expected_names:
        fail(f"WOFF file set differs: expected={sorted(expected_names)}, actual={sorted(actual_names)}")

    for name, expected_hash in sorted(EXPECTED_SHA256.items()):
        path = font_dir / name
        raw = path.read_bytes()
        if len(raw) < 44:
            fail(f"{name} is shorter than a WOFF header: {len(raw)} bytes")
        if raw[:4] != b"wOFF":
            fail(f"{name} has invalid WOFF signature: {raw[:4]!r}")
        flavor = struct.unpack(">I", raw[4:8])[0]
        declared_length = struct.unpack(">I", raw[8:12])[0]
        table_count = struct.unpack(">H", raw[12:14])[0]
        reserved = struct.unpack(">H", raw[14:16])[0]
        if flavor not in (0x00010000, 0x4F54544F):
            fail(f"{name} has unsupported sfnt flavor 0x{flavor:08x}")
        if declared_length != len(raw) or table_count == 0 or reserved != 0:
            fail(
                f"{name} has inconsistent WOFF header: length={declared_length}, "
                f"actual={len(raw)}, tables={table_count}, reserved={reserved}"
            )
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != expected_hash:
            fail(f"{name} SHA-256 mismatch: expected={expected_hash}, actual={actual_hash}")
        print(f"[PASS] {name}: {len(raw)} bytes, {table_count} tables, SHA-256 OK")

    license_path = package / "licenses" / "LICENSE"
    if not license_path.is_file():
        fail(f"OFL-1.1 license file is missing: {license_path}")
    license_text = license_path.read_text(encoding="utf-8")
    if "The Fira Code Project Authors" not in license_text or "SIL OPEN FONT LICENSE Version 1.1" not in license_text:
        fail("packaged license does not contain the upstream Fira Code copyright and OFL-1.1 text")

    print("[PASS] Exactly six upstream WOFF files and the Fira Code OFL-1.1 license are packaged")


if __name__ == "__main__":
    main(sys.argv[1:])
