#!/usr/bin/env python3
"""Generate GPT disk images for sandbox u-boot E2E bootflow tests.

Replaces upstream's qemu-img + cgpt + futility toolchain (none of which
exists on OHOS) with pure-stdlib Python:

- mmc7.img: 20MB GPT, 5 basicdata partitions (misc/boot_a/boot_b/
  vendor_boot_a/vendor_boot_b); boot_a=v4 boot image, vendor_boot_a=v4
  vendor_boot image (decoded from the gzip hex dumps in the hexdumps file)
- mmc8.img: 20MB GPT, 3 partitions (misc/boot_a/boot_b); boot_a=v2 boot img
- mmc5.img: 20MB GPT, 12 ChromiumOS partitions per upstream
  setup_cros_image(); KERN_A/KERN_B packed with a hand-built vboot
  kernel part (keyblock+preamble+body) whose geometry satisfies
  boot/bootmeth_cros.c (no signature verification happens there)

Usage: python3 gen-gpt-fixtures.py <abootimg-hexdumps-file> <out-dir>
The hexdumps file holds boot_img_hex/vboot_img_hex/img_hex extracted
from upstream test/py/tests/test_android/test_abootimg.py.
"""
import binascii
import gzip
import re
import struct
import sys
import zlib

SECT = 512

# GPT type GUIDs (text form)
BASICDATA = 'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7'
CROS_KERN = 'fe3a2a5d-4f32-41a7-b725-accc3285a309'
CROS_ROOT = '3cb8e202-3b7e-47dd-8a3c-7ff2a13cfcec'
CROS_RWFW = 'cab6e88e-abf3-4102-a07a-d4bb9be3c1d3'
CROS_RESV = '2e0a753d-9e48-43b0-8337-b15192cb1b5e'
CROS_EFI = 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b'


def guid_bytes(text):
    """GPT on-disk GUID encoding (mixed endian)."""
    p = text.split('-')
    return struct.pack('<IHH8s', int(p[0], 16), int(p[1], 16), int(p[2], 16),
                       binascii.unhexlify(p[3] + p[4]))


def make_gpt(total_sectors, parts):
    """Build a full disk image (PMBR + primary/backup GPT).

    parts: list of (num, name, type_guid_text, first_lba, size_sectors, data)
    data is written at first_lba*SECT.
    """
    disk = bytearray(total_sectors * SECT)

    # Protective MBR
    pmbr = bytearray(SECT)
    pmbr[446:462] = bytes([0, 0xfe, 0xff, 0xff, 0xee, 0xfe, 0xff, 0xff]) + \
        struct.pack('<II', 1, min(total_sectors - 1, 0xffffffff))
    pmbr[510:512] = b'\x55\xaa'
    disk[0:SECT] = pmbr

    num_entries = 128
    entry_size = 128
    entries_lba = 2
    first_usable = 40
    last_usable = total_sectors - 1 - 32 - 1
    backup_entries_lba = last_usable + 1
    backup_lba = total_sectors - 1

    # Entries
    entries = bytearray(num_entries * entry_size)
    for (num, name, tguid, first_lba, size, data) in parts:
        e = bytearray(entry_size)
        e[0:16] = guid_bytes(tguid)
        e[16:32] = struct.pack('<IHH8s', num, 0x1234, 0x5678,
                               bytes([num & 0xff]) * 8)  # unique GUID
        e[32:40] = struct.pack('<Q', first_lba)
        e[40:48] = struct.pack('<Q', first_lba + size - 1)
        e[56:56 + 2 * len(name)] = name.encode('utf-16-le')
        entries[(num - 1) * entry_size:(num - 1) * entry_size +
                entry_size] = e
        disk[first_lba * SECT:first_lba * SECT + len(data)] = data

    def hdr(my_lba, alt_lba, crc, entries_crc):
        h = bytearray(92)
        h[0:8] = b'EFI PART'
        h[8:12] = struct.pack('<I', 0x00010000)
        h[12:16] = struct.pack('<I', 92)
        h[16:20] = struct.pack('<I', crc)
        h[24:32] = struct.pack('<Q', my_lba)
        h[32:40] = struct.pack('<Q', alt_lba)
        h[40:48] = struct.pack('<Q', first_usable)
        h[48:56] = struct.pack('<Q', last_usable)
        h[56:72] = struct.pack('<IHH8s', 0x3b7dd70a, 0x4a2c, 0x4c6e,
                               bytes(range(8)))
        h[72:80] = struct.pack('<Q', entries_lba)
        h[80:84] = struct.pack('<I', num_entries)
        h[84:88] = struct.pack('<I', entry_size)
        h[88:92] = struct.pack('<I', entries_crc)
        return h

    entries_crc = zlib.crc32(bytes(entries)) & 0xffffffff
    prim = hdr(1, backup_lba, 0, entries_crc)
    prim[16:20] = struct.pack('<I', zlib.crc32(bytes(prim)) & 0xffffffff)
    disk[1 * SECT:1 * SECT + 92] = prim
    disk[entries_lba * SECT:entries_lba * SECT + len(entries)] = entries

    # Backup copies
    back = hdr(backup_lba, 1, 0, entries_crc)
    back[16:20] = struct.pack('<I', zlib.crc32(bytes(back)) & 0xffffffff)
    disk[backup_entries_lba * SECT:backup_entries_lba * SECT +
         len(entries)] = entries
    disk[backup_lba * SECT:backup_lba * SECT + 92] = back

    return bytes(disk)


def hex_to_gz(hexstr):
    return gzip.decompress(binascii.unhexlify(''.join(hexstr.split())))


def extract_hex_dump(path, name):
    text = open(path, encoding='utf-8').read()
    # '^' + re.M: the variable must start a line. An unanchored
    # `name + '_hex'` search is wrong for name='img': the string
    # "boot_img_hex" *contains* "img_hex", so re.search would silently
    # return boot_new.img (header v4) for the v2 fixture. A v4 header on
    # mmc8 then makes bootmeth_android demand a vendor_boot partition
    # (header_version >= 3) that the v2 layout does not have, and the
    # whole bootflow is rejected -> bootflow_android_image_v2 fails.
    m = re.search(r'^' + name + r'_hex\s*=\s*"""(.*?)"""', text,
                  re.S | re.M)
    assert m, f'{name}_hex not found in {path}'
    return hex_to_gz(m.group(1))


def pack_cros_kernel(config):
    """Hand-built vboot kernel part satisfying boot/bootmeth_cros.c."""
    keyblock_size = 0x800
    preamble_size = 0x1000
    body_offset = keyblock_size + preamble_size
    load_addr = 0x100000
    bl_addr = load_addr + 0x2000  # diff 0x2000 => cmdline at body_offset
    bl_size = 0x1000
    body_size = 0x4000  # upstream futility data_size (asserted as 4000)

    part = bytearray(body_offset + body_size)

    # Keyblock header (only magic + keyblock_size are read)
    part[0:8] = b'CHROMEOS'
    struct.pack_into('<II', part, 8, 2, 0)  # header_version major/minor
    struct.pack_into('<I', part, 16, keyblock_size)

    # Preamble at keyblock_size (packed vb2_kernel_preamble, no magic;
    # offsets per boot/bootmeth_cros.h)
    p = keyblock_size
    struct.pack_into('<II', part, p + 0, preamble_size, 0)
    # preamble_signature (24B at p+8): all zeros
    struct.pack_into('<II', part, p + 32, 2, 2)  # header_version major/minor
    struct.pack_into('<I', part, p + 40, 1)      # kernel_version
    struct.pack_into('<Q', part, p + 48, load_addr)   # body_load_address
    struct.pack_into('<Q', part, p + 56, bl_addr)     # bootloader_address
    struct.pack_into('<II', part, p + 64, bl_size, 0)  # bootloader_size
    # body_signature at p+72: sig_offset/sig_size at +72/+80, data_size +88
    struct.pack_into('<II', part, p + 72, 0, 0)
    struct.pack_into('<I', part, p + 88, body_size)   # data_size
    struct.pack_into('<Q', part, p + 96, 0)   # vmlinuz_header_address
    struct.pack_into('<II', part, p + 104, 0, 0)  # vmlinuz_header_size
    struct.pack_into('<I', part, p + 112, 0)    # flags

    # Body: config/cmdline text at body_offset (== parser's read offset),
    # setup area at +0x1000 stays zero (test asserts empty), bootloader at
    # +0x2000 unread by the parser
    part[body_offset:body_offset + len(config)] = config
    return bytes(part)


def build_mmc7(src, out):
    total = 20 * 2048  # 20MB in sectors
    bootv4 = extract_hex_dump(src, 'boot_img')
    vboot = extract_hex_dump(src, 'vboot_img')
    parts = [
        (1, 'misc', BASICDATA, 40, 2048, b''),
        (2, 'boot_a', BASICDATA, 2088, 8192, bootv4),
        (3, 'boot_b', BASICDATA, 10280, 8192, b''),
        (4, 'vendor_boot_a', BASICDATA, 18472, 8192, vboot),
        (5, 'vendor_boot_b', BASICDATA, 26664, 8192, b''),
    ]
    with open(out + '/mmc7.img', 'wb') as f:
        f.write(make_gpt(total, parts))
    print(f'mmc7.img: {total*SECT} bytes, bootv4={len(bootv4)}B, '
          f'vboot={len(vboot)}B')


def build_mmc8(src, out):
    total = 20 * 2048
    boot = extract_hex_dump(src, 'img')
    parts = [
        (1, 'misc', BASICDATA, 40, 2048, b''),
        (2, 'boot_a', BASICDATA, 2088, 8192, boot),
        (3, 'boot_b', BASICDATA, 10280, 8192, b''),
    ]
    with open(out + '/mmc8.img', 'wb') as f:
        f.write(make_gpt(total, parts))
    print(f'mmc8.img: {total*SECT} bytes, boot={len(boot)}B')


def build_mmc5(out):
    total = 20 * 2048
    config = (b'BOOT_IMAGE=/vmlinuz-5.15.0-121-generic '
              b'root=/dev/nvme0n1p1 ro quiet splash vt.handoff=7\0')
    kpart = pack_cros_kernel(config)
    # Sector layout from upstream setup_cros_image() (ptr accumulation)
    parts = [
        (11, 'RWFW', CROS_RWFW, 40, 1, b''),
        (6, 'KERN_C', CROS_KERN, 41, 1, b''),
        (7, 'ROOT_C', CROS_ROOT, 42, 1, b''),
        (9, 'reserved', CROS_RESV, 43, 1, b''),
        (10, 'reserved', CROS_RESV, 44, 1, b''),
        (2, 'KERN_A', CROS_KERN, 45, 2048, kpart),
        (4, 'KERN_B', CROS_KERN, 2093, 2048, kpart),
        (8, 'OEM', BASICDATA, 4141, 2048, b''),
        (12, 'EFI-SYSTEM', CROS_EFI, 6189, 2048, b''),
        (5, 'ROOT_B', CROS_ROOT, 8237, 1, b''),
        (3, 'ROOT_A', CROS_ROOT, 8238, 1, b''),
        (1, 'STATE', BASICDATA, 8239, 2048, b''),
    ]
    with open(out + '/mmc5.img', 'wb') as f:
        f.write(make_gpt(total, parts))
    print(f'mmc5.img: {total*SECT} bytes, kpart={len(kpart)}B')


def main():
    src, out = sys.argv[1], sys.argv[2]
    build_mmc7(src, out)
    build_mmc8(src, out)
    build_mmc5(out)
    print('OK')


if __name__ == '__main__':
    main()
