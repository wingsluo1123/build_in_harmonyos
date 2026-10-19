#!/usr/bin/env python3
"""Consumer check for the packaged Asterisk Opus format module."""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"


def _is_elf_shared_object(path):
    with open(path, "rb") as stream:
        ident = stream.read(16)
        if len(ident) < 16 or ident[:4] != ELF_MAGIC:
            return False
        stream.seek(16)
        return struct.unpack("<H", stream.read(2))[0] == 3


def main():
    package = sys.argv[1]
    module = os.path.join(package, "lib", "asterisk", "modules",
                          "res_format_attr_opus.so")
    if not os.path.isfile(module):
        print(f"FAIL: module not found: {module}", file=sys.stderr)
        return 1
    if not _is_elf_shared_object(module):
        print("FAIL: Opus module is not an ELF shared object", file=sys.stderr)
        return 1
    with open(module, "rb") as stream:
        contents = stream.read()
    if b"Opus Format Attribute Module" not in contents:
        print("FAIL: Opus module has no Asterisk module entry data", file=sys.stderr)
        return 1
    print("OK: res_format_attr_opus.so present + ELF + Asterisk entry data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
