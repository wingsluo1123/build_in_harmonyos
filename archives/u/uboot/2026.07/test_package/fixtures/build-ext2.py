#!/usr/bin/env python3
"""Build mmc4p1.ext2 (18MB ext2, 4KB blocks, one group) containing
/boot/{boot.cmd,boot.bmp,boot.scr,vmlinuz-5.15.63-rockchip64,Image}
for the sandbox u-boot bootmenu E2E fixture (test_ut.py setup_bootmenu_image).

Pure stdlib: OHOS has no mke2fs -d / debugfs to inject files into the
partition that u-boot's own ext4 driver must later read. ext2 rev 1 +
EXT2_FEATURE_INCOMPAT_FILETYPE is the minimal feature set u-boot fs/ext4
accepts. Note OHOS e2fsck loops forever on this image (see notes.md);
u-boot's ext4 driver is the validation oracle.

Usage: python3 build-ext2.py <fixtures-host-dir> <output-path>
"""
import os
import struct
import sys

BLK = 4096
TOTAL_BLOCKS = 18 * 1024 * 1024 // BLK  # 4608
INODES = 512
INODE_SIZE = 128
INODE_TABLE_BLOCKS = INODES * INODE_SIZE // BLK  # 16

# Block layout (4K blocks: superblock lives at byte 1024 inside block 0,
# so the group descriptor starts at block 1 -- NOT the 1K-block layout
# where sb@1 pushes the gdt to 2. u-boot's ext4fs_blockgroup computes
# gdt at first_data_block+1 = block 1 regardless.)
BB_SUPER = 0
BB_GDT = 1
BB_BBM = 2
BB_IBM = 3
BB_ITAB = 4                       # .. 4+16-1
BB_DATA = BB_ITAB + INODE_TABLE_BLOCKS  # 20

# Inode numbers (mke2fs convention: first_ino=11)
INO_ROOT = 2
INO_BOOT = 12
INO_BOOTCMD = 13
INO_BMP = 14
INO_SCR = 15
INO_VMLINUZ = 16
INO_IMAGE = 17

# Data blocks
B_ROOT = BB_DATA        # 20  /            dir data
B_BOOT = 21             #     /boot        dir data
B_BOOTCMD = 22          #     /boot/boot.cmd
B_BMP = 23              # .. 28            /boot/boot.bmp (6 blocks)
B_SCR = 29              #     /boot/boot.scr
B_VMLINUZ = 30          #     /boot/vmlinuz-5.15.63-rockchip64
# /boot/Image is a fast symlink -> vmlinuz-5.15.63-rockchip64: no data
# block (target stored inline in the inode's i_block), see symlink_inode()
LAST_USED_BLOCK = B_VMLINUZ  # 30 -> 31 blocks used (0..30)

USED_BLOCKS = LAST_USED_BLOCK + 1
USED_INODES = 7

S_IFDIR = 0x4000
S_IFREG = 0x8000
S_IFLNK = 0xA000
FT_REG = 1
FT_DIR = 2
FT_SYMLINK = 7


def pad_dent(inode, name, ftype):
    """Entry with rec_len padded to 4-byte multiple."""
    raw = struct.pack('<IHBB', inode, 0, len(name), ftype) + name.encode()
    rec_len = (len(raw) + 3) & ~3
    return struct.pack('<IHBB', inode, rec_len, len(name), ftype) + \
        name.encode() + b'\x00' * (rec_len - len(raw))


def make_dir(entries):
    """entries: list of (inode, name, ftype); last entry extends to BLK."""
    blob = bytearray()
    for inode, name, ftype in entries[:-1]:
        blob += pad_dent(inode, name, ftype)
    inode, name, ftype = entries[-1]
    rec_len = BLK - len(blob)
    blob += struct.pack('<IHBB', inode, rec_len, len(name), ftype) + \
        name.encode()
    assert len(blob) <= BLK, f'dir overflow: {len(blob)}'
    blob += b'\x00' * (BLK - len(blob))
    return bytes(blob)


def inode(mode, size, links, data_blocks):
    """128-byte ext2 inode. data_blocks: list of direct block numbers."""
    assert len(data_blocks) <= 12
    raw = bytearray(INODE_SIZE)
    struct.pack_into('<H', raw, 0, mode)
    struct.pack_into('<I', raw, 4, size)
    struct.pack_into('<H', raw, 26, links)
    struct.pack_into('<I', raw, 28, len(data_blocks) * 8)  # 512B sectors
    for i, b in enumerate(data_blocks):
        struct.pack_into('<I', raw, 40 + 4 * i, b)
    return bytes(raw)


def symlink_inode(target):
    """128-byte ext2 inode for a fast symlink (target inline in i_block).

    u-boot's ext4fs_read_link reads i_size bytes straight out of i_block
    when i_size < 60 (fs/ext4/ext4_common.c); no data block is allocated.
    """
    assert len(target) < 60, 'fast symlink target must be < 60 bytes'
    raw = bytearray(INODE_SIZE)
    struct.pack_into('<H', raw, 0, S_IFLNK)
    struct.pack_into('<I', raw, 4, len(target))
    struct.pack_into('<H', raw, 26, 1)
    raw[40:40 + len(target)] = target
    return bytes(raw)


def build(host_dir, out_path):
    boot_cmd = open(os.path.join(host_dir, 'boot.cmd'), 'rb').read()
    boot_bmp = open(os.path.join(host_dir, 'boot.bmp'), 'rb').read()
    boot_scr = open(os.path.join(host_dir, 'boot.scr'), 'rb').read()
    vmlinuz = b'kernel\n'   # upstream: outf.write('kernel\n')
    image_target = b'vmlinuz-5.15.63-rockchip64'  # upstream srcdir symlink

    assert len(boot_bmp) <= 6 * BLK
    assert len(boot_scr) <= BLK and len(boot_cmd) <= BLK

    img = bytearray(TOTAL_BLOCKS * BLK)

    # ---- superblock at byte 1024 (inside block 1) ----
    s = bytearray(1024)
    struct.pack_into('<I', s, 0, INODES)
    struct.pack_into('<I', s, 4, TOTAL_BLOCKS)
    struct.pack_into('<I', s, 8, 0)                      # r_blocks
    struct.pack_into('<I', s, 12, TOTAL_BLOCKS - USED_BLOCKS)
    struct.pack_into('<I', s, 16, INODES - USED_INODES)
    struct.pack_into('<I', s, 20, 0)                     # first_data_block
    struct.pack_into('<I', s, 24, 2)                     # log_block_size (4K)
    struct.pack_into('<i', s, 28, 2)                     # log_frag_size
    struct.pack_into('<I', s, 32, 8192)                   # blocks_per_group
    struct.pack_into('<I', s, 36, 32768)                 # frags_per_group
    struct.pack_into('<I', s, 40, INODES)
    struct.pack_into('<I', s, 44, 0)                     # mtime
    struct.pack_into('<I', s, 48, 0)                     # wtime
    struct.pack_into('<H', s, 52, 0)                     # mnt_count
    struct.pack_into('<H', s, 54, 20)                    # max_mnt_count
    struct.pack_into('<H', s, 56, 0xEF53)                # magic
    struct.pack_into('<H', s, 58, 1)                     # state: clean
    struct.pack_into('<H', s, 60, 1)                     # errors: continue
    struct.pack_into('<H', s, 62, 0)                     # minor_rev
    struct.pack_into('<I', s, 64, 0)                     # lastcheck
    struct.pack_into('<I', s, 68, 0)                     # checkinterval
    struct.pack_into('<I', s, 72, 0)                     # creator_os: Linux
    struct.pack_into('<I', s, 76, 1)                     # rev_level: 1
    struct.pack_into('<H', s, 80, 0)                     # def_resuid
    struct.pack_into('<H', s, 82, 0)                     # def_resgid
    struct.pack_into('<I', s, 84, 11)                    # first_ino
    struct.pack_into('<H', s, 88, INODE_SIZE)
    struct.pack_into('<H', s, 90, 0)                     # block_group_nr
    struct.pack_into('<I', s, 92, 0)                     # feature_compat
    struct.pack_into('<I', s, 96, 0x2)                   # INCOMPAT_FILETYPE
    struct.pack_into('<I', s, 100, 0)                    # feature_ro_compat
    # uuid[16] zeros, volume_name[16] zeros, last_mounted[64] zeros
    struct.pack_into('<I', s, 200, 0)                    # algo_bitmap
    struct.pack_into('<B', s, 204, 0)                    # prealloc_blocks
    struct.pack_into('<B', s, 205, 0)                    # prealloc_dir_blocks
    struct.pack_into('<H', s, 206, 0)                    # padding1
    # journal_* zeros, hash_seed zeros
    struct.pack_into('<H', s, 254, 32)                   # desc_size
    struct.pack_into('<I', s, 256, 0)                    # default_mount_opts
    struct.pack_into('<I', s, 260, 0)                    # first_meta_bg
    struct.pack_into('<I', s, 264, 0)                    # mkfs_time
    img[1024:2048] = s

    # ---- group descriptor (one group) ----
    gd = bytearray(32)
    struct.pack_into('<I', gd, 0, BB_BBM)
    struct.pack_into('<I', gd, 4, BB_IBM)
    struct.pack_into('<I', gd, 8, BB_ITAB)
    struct.pack_into('<H', gd, 12, TOTAL_BLOCKS - USED_BLOCKS)
    struct.pack_into('<H', gd, 14, INODES - USED_INODES)
    struct.pack_into('<H', gd, 16, 2)                    # used_dirs
    img[BB_GDT * BLK:BB_GDT * BLK + 32] = gd

    # ---- bitmaps ----
    bbm = bytearray(BLK)
    for b in range(USED_BLOCKS):
        bbm[b // 8] |= 1 << (b % 8)
    img[BB_BBM * BLK:BB_BBM * BLK + BLK] = bbm

    ibm = bytearray(BLK)
    for ino in (INO_ROOT, INO_BOOT, INO_BOOTCMD, INO_BMP, INO_SCR,
                INO_VMLINUZ, INO_IMAGE):
        ibm[(ino - 1) // 8] |= 1 << ((ino - 1) % 8)
    img[BB_IBM * BLK:BB_IBM * BLK + BLK] = ibm

    # ---- inodes ----
    def put_ino(ino, data):
        off = BB_ITAB * BLK + (ino - 1) * INODE_SIZE
        img[off:off + INODE_SIZE] = data

    put_ino(INO_ROOT, inode(S_IFDIR | 0o755, BLK, 3, [B_ROOT]))
    put_ino(INO_BOOT, inode(S_IFDIR | 0o755, BLK, 2, [B_BOOT]))
    put_ino(INO_BOOTCMD, inode(S_IFREG | 0o644, len(boot_cmd), 1,
                               [B_BOOTCMD]))
    put_ino(INO_BMP, inode(S_IFREG | 0o644, len(boot_bmp), 1,
                           list(range(B_BMP, B_BMP + 6))))
    put_ino(INO_SCR, inode(S_IFREG | 0o644, len(boot_scr), 1, [B_SCR]))
    put_ino(INO_VMLINUZ, inode(S_IFREG | 0o644, len(vmlinuz), 1,
                               [B_VMLINUZ]))
    put_ino(INO_IMAGE, symlink_inode(image_target))

    # ---- directories (root and /boot are separate blocks) ----
    root = make_dir([
        (INO_ROOT, '.', FT_DIR),
        (INO_ROOT, '..', FT_DIR),
        (INO_BOOT, 'boot', FT_DIR),
    ])
    bootdir = make_dir([
        (INO_BOOT, '.', FT_DIR),
        (INO_ROOT, '..', FT_DIR),
        (INO_BOOTCMD, 'boot.cmd', FT_REG),
        (INO_BMP, 'boot.bmp', FT_REG),
        (INO_SCR, 'boot.scr', FT_REG),
        (INO_VMLINUZ, 'vmlinuz-5.15.63-rockchip64', FT_REG),
        (INO_IMAGE, 'Image', FT_SYMLINK),
    ])
    img[B_ROOT * BLK:B_ROOT * BLK + BLK] = root
    img[B_BOOT * BLK:B_BOOT * BLK + BLK] = bootdir

    # ---- file data ----
    img[B_BOOTCMD * BLK:B_BOOTCMD * BLK + len(boot_cmd)] = boot_cmd
    img[B_BMP * BLK:B_BMP * BLK + len(boot_bmp)] = boot_bmp
    img[B_SCR * BLK:B_SCR * BLK + len(boot_scr)] = boot_scr
    img[B_VMLINUZ * BLK:B_VMLINUZ * BLK + len(vmlinuz)] = vmlinuz

    with open(out_path, 'wb') as f:
        f.write(img)
    print(f'ext2: {out_path} {len(img)} bytes, {USED_BLOCKS} blocks, '
          f'root=/ boot=/{len(bootdir) and "ok"}')


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
