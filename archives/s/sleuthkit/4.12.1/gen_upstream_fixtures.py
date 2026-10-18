#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic disk-image fixture generator for the upstream TSK 4.12 tests.

The upstream release tarball ships no filesystem images: tests/Makefile.am
expects images under data/ (not published) or $HOME/from_brian ("not
public" per upstream comment) or a Google Drive download.  To execute the
four check_PROGRAMS for real (PR review rule 4), this script generates at
build time six small but genuine FAT12/16/32 + NTFS volumes whose layouts
satisfy the upstream assertions:

  fat12.dd          FAT12, TEST33.DAT@inode33 / ATTR47.DAT@inode47
                    (read_apis:test_fat12, fs_fname_apis, fs_attrlist_apis)
  fat-img-kw.dd     FAT16, FILE4.DAT@inode10 size 631 with "3slack3" slack
                    marker at file offset 897 (read_apis:test_fat_slack)
  fat32.dd          FAT32 multi-file volume (fs_thread_test -f fat)
  fe_test_1.img     composite: NTFS@32256 (allocated dir + files for
                    fs_fname_apis/fs_attrlist_apis/read_apis:test_ntfs_fe)
                    + FAT16@41126400 (/deleted/fragmented.html@inode1162,
                    read_apis:test_fat_recover); both offsets hardcoded
                    upstream
  ntfs-comp-1.img   NTFS with a compressed (LZNT1 stored chunks) and a
                    sparse file (read_apis:test_ntfs_comp)
  ntfs-img-kw-1.dd  NTFS with slack marker "n-slack" (read_apis:
                    test_ntfs_slack_ads, inode 36) and two $DATA
                    attributes with ids 3/5 (inode 37)

Only the Python standard library is used; no external images are
downloaded or copied.

TSK 4.12 FAT inode convention:
  inode N  <->  dirent slot (N - FATFS_FIRST_NORMINO=3) in the flat
  data-area dirent space (16 dirents per 512-byte sector), starting at
  firstdatasect. Root-dir entry k therefore maps to inode k+3.
File data is read via the dirent's first cluster + FAT chain, so the
first cluster can be chosen freely.
"""
import struct


def fat_chain(entries, chain, eoc):
    for i in range(len(chain) - 1):
        entries[chain[i]] = chain[i + 1]
    entries[chain[-1]] = eoc


def write_fat12(fat):
    out = bytearray((len(fat) * 3 + 1) // 2 + 1)
    for i, v0 in enumerate(fat):
        v = v0 & 0xFFF
        if i & 1:
            out[i * 3 // 2] |= (v & 0xF) << 4
            out[i * 3 // 2 + 1] = v >> 4
        else:
            out[i * 3 // 2] = v & 0xFF
            out[i * 3 // 2 + 1] = (out[i * 3 // 2 + 1] & 0xF0) | ((v >> 8) & 0xF)
    return out


def write_fat16(fat):
    return b"".join(struct.pack("<H", v & 0xFFFF) for v in fat)


def write_fat32(fat):
    return b"".join(struct.pack("<I", v & 0x0FFFFFFF) for v in fat)


def dos_name(name):
    base, _, ext = name.partition(".")
    assert (base.isalnum() or base.endswith("~1")) and len(base) <= 8 \
        and len(ext) <= 3, name
    return base.upper().ljust(8).encode() + ext.upper().ljust(3).encode()


def dir_entry(name, first_cluster, size, attr=0x20, deleted=False):
    """32-byte short directory entry."""
    e = bytearray(32)
    if name in (".", ".."):
        e[0:11] = name.ljust(11).encode()
    else:
        e[0:11] = dos_name(name)
        if deleted:
            e[0] = 0xE5
    e[11] = attr
    struct.pack_into("<H", e, 14, 0)        # create time
    struct.pack_into("<H", e, 16, 0x0021)   # create date 1980-01-01
    struct.pack_into("<H", e, 18, 0x0021)   # access date
    struct.pack_into("<H", e, 22, 0)        # write time
    struct.pack_into("<H", e, 24, 0x0021)   # write date
    struct.pack_into("<H", e, 26, first_cluster & 0xFFFF)
    struct.pack_into("<H", e, 20, (first_cluster >> 16) & 0xFFFF)
    struct.pack_into("<I", e, 28, size)
    return bytes(e)


def lfn_entries(name, checksum):
    """LFN dir entries, in on-disk order (last sequence first)."""
    ents = []
    units = [name[i:i + 13] for i in range(0, len(name), 13)]
    n = len(units)
    for seq in range(n, 0, -1):
        e = bytearray(32)
        e[0] = (seq | 0x40) if seq == n else seq
        e[11] = 0x0F
        e[12] = 0
        e[13] = checksum
        chars = []
        for ch in units[seq - 1]:
            chars += [ord(ch) & 0xFF, 0]
        chars += [0, 0]
        while len(chars) < 26:
            chars += [0xFF, 0xFF]
        e[1:11] = bytes(chars[0:10])    # 5 chars
        e[14:26] = bytes(chars[10:22])  # 6 chars
        e[28:32] = bytes(chars[22:26])  # 2 chars
        ents.append(bytes(e))
    return ents


class FatImage:
    def __init__(self, fs_type, total_sectors, csize=1, root_entries=512,
                 reserved=None, media=0xF8, fat_secs=None):
        self.fs_type = fs_type
        self.ssize = 512
        self.csize = csize
        self.total_sectors = total_sectors
        self.root_entries = root_entries
        self.reserved = reserved or {12: 1, 16: 1, 32: 32}[fs_type]
        self.media = media
        if fat_secs is None:
            bits = {12: 1.5, 16: 2, 32: 4}[fs_type]
            self.fat_secs = (int(total_sectors * bits) + 16 + self.ssize - 1) \
                // self.ssize
        else:
            self.fat_secs = fat_secs
        self.root_secs = (root_entries * 32 + self.ssize - 1) // self.ssize
        self.firstdatasect = self.reserved + self.fat_secs * 2
        self.firstclustsect = self.firstdatasect + self.root_secs
        self.nclusters = (total_sectors - self.firstclustsect) // csize
        assert self.nclusters > 0
        self.fat = [0] * (self.nclusters + 2)
        self.eoc = {12: 0xFFF, 16: 0xFFFF, 32: 0x0FFFFFFF}[fs_type]
        self.fat[0] = 0xFF00 | media
        self.fat[1] = self.eoc
        self.root_dir = []      # FAT12/16 root entries / FAT32 root cluster
        self.clusters = {}      # cluster -> 512*csize bytes
        self.root_cluster = 2
        self.dirent_cnt_se = self.ssize // 32

    def sec_of_cluster(self, c):
        return self.firstclustsect + (c - 2) * self.csize

    def root_inode_base(self):
        """inode of root entry 0 (FAT12/16): sector firstdatasect, slot 0."""
        return (self.firstdatasect - self.firstdatasect) * self.dirent_cnt_se + 3

    def alloc_chain(self, n, start=None):
        free = [c for c in range(2, self.nclusters + 2) if self.fat[c] == 0]
        if start is not None:
            assert self.fat[start] == 0, "cluster %d busy" % start
            chain = [start]
            for c in free:
                if c != start and len(chain) < n:
                    chain.append(c)
        else:
            chain = free[:n]
        assert len(chain) == n, "not enough free clusters"
        fat_chain(self.fat, chain, self.eoc)
        return chain

    def write_cluster(self, c, data):
        assert len(data) <= self.csize * self.ssize
        self.clusters[c] = bytes(data) + b"\x00" * \
            (self.csize * self.ssize - len(data))

    # ---- directory handling -------------------------------------------
    # dirs are described as lists of entry bytes; root (FAT12/16) or a
    # cluster chain (FAT32 + subdirs) is materialized in build().
    def add_dirent(self, ent, dirspec):
        dirspec["ents"].append(ent)

    def pad_to_inode(self, dirspec, target_inode, start_inode):
        """Append filler (deleted) entries so the next short entry gets
        inode == target_inode."""
        need = target_inode - start_inode - len(dirspec["ents"])
        assert need >= 0, "inode %d already passed (have %d ents)" % (
            target_inode, len(dirspec["ents"]))
        for i in range(need):
            dirspec["ents"].append(
                dir_entry("FILL.DAT", 0, 0, deleted=True))

    def add_file(self, name, data, dirspec, first_cluster=None, size=None,
                 attr=0x20, lfn=False):
        """Add a file. `size` overrides the dirent size so slack content
        can live past EOF inside the last cluster."""
        if size is None:
            size = len(data)
        csize_b = self.csize * self.ssize
        n = (len(data) + csize_b - 1) // csize_b
        chain = self.alloc_chain(n, first_cluster)
        for i, c in enumerate(chain):
            off = i * csize_b
            self.write_cluster(c, data[off:off + csize_b])
        if lfn and name != self._short_of(name):
            for e in lfn_entries(name, self._lfn_checksum(dos_name(self._short_of(name)))):
                dirspec["ents"].append(e)
            ent = dir_entry(self._short_of(name), chain[0], size, attr)
        else:
            ent = dir_entry(name, chain[0], size, attr)
        dirspec["ents"].append(ent)
        return chain[0]

    @staticmethod
    def _short_of(name):
        base, _, ext = name.partition(".")
        if len(base) <= 8 and len(ext) <= 3 and "~" not in base:
            return name
        b = base[:6].upper() + "~1"
        return b + ("." + ext[:3].upper() if ext else "")

    @staticmethod
    def _lfn_checksum(short11):
        s = 0
        for ch in short11:
            s = (((s & 1) << 7) + (s >> 1) + ch) & 0xFF
        return s

    def add_dir(self, name, dirspec, lfn=False):
        """Create a directory; returns its dirspec (entries filled later
        via add_file(..., dirspec=child))."""
        child = {"ents": [dir_entry(".", 0, 0, attr=0x10),
                          dir_entry("..", 0, 0, attr=0x10)]}
        if lfn and name != self._short_of(name):
            for e in lfn_entries(name, self._lfn_checksum(dos_name(self._short_of(name)))):
                dirspec["ents"].append(e)
            ent = dir_entry(self._short_of(name), 0, 0, attr=0x10)
        else:
            ent = dir_entry(name, 0, 0, attr=0x10)
        dirspec["ents"].append(ent)
        child["_parent_ent"] = ent
        child["_parent"] = dirspec
        child["_name"] = name
        child["_lfn"] = lfn
        return child

    def materialize(self, dirspec, parent_cluster, start_cluster=None):
        """Allocate a cluster chain for a directory and fix up its entry
        and its children's '..' pointers. Returns first cluster."""
        raw = b"".join(dirspec["ents"])
        csize_b = self.csize * self.ssize
        n = (len(raw) + csize_b - 1) // csize_b
        chain = self.alloc_chain(n, start_cluster)
        buf = raw + b"\x00" * (n * csize_b - len(raw))
        for i, c in enumerate(chain):
            self.write_cluster(c, buf[i * csize_b:(i + 1) * csize_b])
        # fix the entry in the parent
        ent = dirspec["_parent_ent"]
        newent = dir_entry(dirspec["_name"], chain[0], 0, attr=0x10)
        dirspec["_parent"]["ents"][dirspec["_parent"]["ents"].index(ent)] = newent
        # fix '..' of children of this dir? not needed (tests don't rely)
        return chain[0]

    # ---- root handling --------------------------------------------------
    def _root_start_inode(self):
        if self.fs_type == 32:
            # root cluster chain: inode base from the root cluster sector
            s = self.sec_of_cluster(self.root_cluster)
            return (s - self.firstdatasect) * self.dirent_cnt_se + 3
        return 3

    def build(self):
        img = bytearray(self.total_sectors * self.ssize)
        if self.fs_type == 12:
            fatb = write_fat12(self.fat)
        elif self.fs_type == 16:
            fatb = write_fat16(self.fat)
        else:
            fatb = write_fat32(self.fat)
        fatb = fatb[:self.fat_secs * self.ssize]
        for i in range(2):
            off = (self.reserved + i * self.fat_secs) * self.ssize
            img[off:off + len(fatb)] = fatb
        # directories
        root = self.root_dir
        if self.fs_type == 32:
            raw = b"".join(root)
            csize_b = self.csize * self.ssize
            n = (len(raw) + csize_b - 1) // csize_b
            chain = self.alloc_chain(n)
            buf = raw + b"\x00" * (n * csize_b - len(raw))
            self.root_cluster = chain[0]
            for i, c in enumerate(chain):
                self.write_cluster(c, buf[i * csize_b:(i + 1) * csize_b])
        else:
            raw = b"".join(root)
            assert len(raw) <= self.root_secs * self.ssize
            off = self.firstdatasect * self.ssize
            img[off:off + len(raw)] = raw
        # file/dir data
        for c, chunk in self.clusters.items():
            sec = self.sec_of_cluster(c)
            img[sec * self.ssize:(sec + self.csize) * self.ssize] = chunk
        # BPB
        bpb = bytearray(512)
        bpb[0:3] = b"\xEB\x3C\x90"
        bpb[3:11] = b"OHOSFIXT"
        struct.pack_into("<H", bpb, 11, self.ssize)
        bpb[13] = self.csize
        struct.pack_into("<H", bpb, 14, self.reserved)
        bpb[16] = 2
        struct.pack_into("<H", bpb, 17, self.root_entries if self.fs_type != 32 else 0)
        struct.pack_into("<H", bpb, 19, self.total_sectors if self.total_sectors < 0x10000 else 0)
        struct.pack_into("<I", bpb, 32, self.total_sectors if self.total_sectors >= 0x10000 else 0)
        bpb[21] = self.media
        struct.pack_into("<H", bpb, 22, self.fat_secs)
        struct.pack_into("<H", bpb, 24, 63)
        struct.pack_into("<H", bpb, 26, 255)
        if self.fs_type == 32:
            struct.pack_into("<I", bpb, 44, self.root_cluster)
            struct.pack_into("<H", bpb, 48, 1)
            struct.pack_into("<H", bpb, 50, 6)
            bpb[64] = 0x80
            bpb[66] = 0x29
            struct.pack_into("<I", bpb, 67, 0x20261001)
            bpb[71:82] = b"OHOSFAT32 "
            fsinfo = bytearray(512)
            fsinfo[0:4] = b"RRaA"
            struct.pack_into("<I", fsinfo, 484, 0xFFFFFFFF)
            struct.pack_into("<I", fsinfo, 488, self.nclusters)
            img[512:1024] = fsinfo
        else:
            bpb[36:44] = b"OHOSFAT  "
            bpb[38] = 0x29
            struct.pack_into("<I", bpb, 39, 0x20261001)
            bpb[43:54] = b"OHOSFAT12 "
        img[0:512] = bpb
        img[510:512] = b"\x55\xAA"
        return bytes(img)


ROOT = None  # helper: current root dirspec


def build_fat12_dd():
    """fat12.dd: generic valid FAT12.

    read_apis:test_fat12   -> testfile(fs, 33): file whose dirent is at
                              root entry 30 (inode 30+3)
    fs_fname_apis          -> dir/walk self-consistency on root
    fs_attrlist_apis       -> inode 47 (root entry 44) has 1 attribute
    """
    img = FatImage(12, total_sectors=2880, csize=1, root_entries=224)
    root = {"ents": []}
    img.pad_to_inode(root, 33, 3)                       # entries 0..29
    img.add_file("TEST33.DAT", b"fat12 inode 33 payload\n" * 90, root)
    img.pad_to_inode(root, 47, 3)                       # entries 31..43
    img.add_file("ATTR47.DAT", b"attribute api probe\n" * 10, root)
    img.add_file("README.TXT", b"synthetic fixture for TSK tests\n", root)
    img.root_dir = root["ents"]
    return img.build()


def build_fat_img_kw():
    """fat-img-kw.dd: slack-space behaviour (read_apis:test_fat_slack).

    file4.dat at inode 10 (root entry 7): dirent size 631; read at 512
    without slack -> 119; with slack -> 512; "3slack3" at file offset 897
    (byte 385 of the last sector).
    """
    img = FatImage(12, total_sectors=2880, csize=1, root_entries=224)
    root = {"ents": []}
    img.pad_to_inode(root, 10, 3)                       # entries 0..6
    last_sec = bytearray(512)
    last_sec[0:119] = b"B" * 119
    last_sec[385:392] = b"3slack3"
    data = b"A" * 512 + bytes(last_sec)                 # physical 2 clusters
    img.add_file("FILE4.DAT", data, root, first_cluster=10, size=631)
    img.root_dir = root["ents"]
    return img.build()


def build_fat32_dd():
    """fat32.dd: fs_thread_test -f fat determinism fixture."""
    # smallest valid FAT32: >= 65525 clusters, csize=1 -> ~32 MB
    img = FatImage(32, total_sectors=32 + 2 * 512 + 65536,
                   csize=1, root_entries=0, reserved=32, fat_secs=512)
    root = {"ents": []}
    img.add_file("BIG.DAT", bytes(range(256)) * 64, root)      # 16 KiB
    img.add_file("HELLO.TXT", b"hello from synthetic fat32\n", root)
    sub = img.add_dir("SUB", root)
    img.add_file("NESTED.DAT", b"nested payload\n" * 100, sub)
    sub_c = img.materialize(sub, 0)
    sub["ents"][1] = dir_entry("..", sub_c, 0, attr=0x10)  # informational
    img.add_file("MULTI.DAT", b"M" * (4096 * 3 + 11), root)    # 4 clusters
    img.root_dir = root["ents"]
    return img.build()


def build_fe_fat_partition():
    """FAT16 partition of fe_test_1.img (read_apis:test_fat_recover).

    /deleted dir contains fragmented.html whose dirent sits at inode 1162:
    subdir cluster chosen so that sector firstdatasect+72 holds the LFN +
    short entry at slot idx 7 (ibase 16*72+3 = 1155 + 7 = 1162).
    """
    root_entries = 512
    img = FatImage(16, total_sectors=1 + 2 * 16 + 32 + 4096,
                   csize=1, root_entries=root_entries, fat_secs=16)
    assert img.firstdatasect == 33 and img.firstclustsect == 65
    # dirent slot for inode 1162: sector 33 + 72 = 105, idx 7
    # sector 105 = cluster 105 - 65 + 2 = 42
    root = {"ents": []}
    deleted = img.add_dir("DELETED", root)
    # LFN needs 2 slots (15 chars): pad to 1160 so the SHORT entry lands on
    # inode 1162 (ibase 1155 + slots 5,6 = LFN entries, slot 7 = short entry)
    img.pad_to_inode(deleted, 1162 - 2, (105 - 33) * 16 + 3)   # ibase = 1155
    data = bytearray(5905)
    data[0:100] = b"X" * 100
    data[2048:2054] = b"appear"
    data[5900:5905] = b"tail."
    img.add_file("fragmented.html", bytes(data), deleted, lfn=True)
    deleted_c = img.materialize(deleted, 0, start_cluster=42)
    assert img.sec_of_cluster(deleted_c) == 105
    img.root_dir = root["ents"]
    return img.build()


# -*- coding: utf-8 -*-
"""Minimal NTFS image builder for the upstream TSK 4.12 tests.

Produces small, valid NTFS volumes whose MFT record placement and
attribute layout satisfy the upstream test assertions (self-consistent
walks plus documented slack/ADS/compression/sparse behaviour).

Layout: 512B sectors/clusters; boot = clusters 0-15 (sector 0 only),
$MFTMirr = clusters 8-11 (2048 B), $MFT = clusters 16.. (1024 B/record),
bitmap cluster, then user data.
"""
import struct

T_STD_INFO = 0x10
T_FNAME = 0x30
T_VOLINFO = 0x70
T_DATA = 0x80
T_IDXROOT = 0x90
T_IDXALLOC = 0xA0
T_BITMAP = 0xB0

MFT_REC_SIZE = 1024
CLUSTER = 512
NCLUSTERS = 384
MFT_START = 16
N_MFT_RECORDS = 48


def enc_runs(runs):
    """runs: list of (length_clusters, offset_clusters|None).  offset None
    means sparse (no offset bytes)."""
    out = bytearray()

    def varint(v):
        n = 1 if v < (1 << 8) else 2 if v < (1 << 16) else \
            3 if v < (1 << 24) else 4
        return n, v.to_bytes(n, "little")

    def signed_varint(v):
        # NTFS runlist offsets are SIGNED little-endian
        n = 1
        while not (-(1 << (8 * n - 1)) <= v < (1 << (8 * n - 1))):
            n += 1
        return n, v.to_bytes(n, "little", signed=True)

    for ln, off in runs:
        ln_n, ln_b = varint(ln)
        if off is None:
            out.append(ln_n)
            out += ln_b
        else:
            off_n, off_b = signed_varint(off)
            out.append(ln_n | (off_n << 4))
            out += ln_b
            out += off_b
    out.append(0x00)
    return bytes(out)


def utf16(s):
    return s.encode("utf-16-le")


FTIME = 0x01C4A83E00000000  # fixed constant NTFS FILETIME


def res_attr(atype, value, name="", aid=0, flags=0):
    nlen = len(name)
    name_off = 24
    soff = name_off + 2 * nlen
    soff = (soff + 7) & ~7
    total = soff + len(value)
    total = (total + 7) & ~7
    a = bytearray(total)
    struct.pack_into("<I", a, 0, atype)
    struct.pack_into("<I", a, 4, total)
    a[8] = 0                       # resident
    a[9] = nlen
    struct.pack_into("<H", a, 10, name_off)
    struct.pack_into("<H", a, 12, flags)
    struct.pack_into("<H", a, 14, aid)
    struct.pack_into("<I", a, 16, len(value))
    struct.pack_into("<H", a, 20, soff)
    a[24:24 + 2 * nlen] = utf16(name)
    a[soff:soff + len(value)] = value
    return bytes(a)


def nonres_attr(atype, runs, size, name="", aid=0, flags=0, compusize=0,
                alloc_size=None):
    nlen = len(name)
    name_off = 64
    run_off = name_off + 2 * nlen
    runb = enc_runs(runs)
    total = (run_off + len(runb) + 7) & ~7
    if alloc_size is None:
        alloc_size = sum(l for l, _ in runs) * CLUSTER
    a = bytearray(total)
    struct.pack_into("<I", a, 0, atype)
    struct.pack_into("<I", a, 4, total)
    a[8] = 1                       # non-resident
    a[9] = nlen
    struct.pack_into("<H", a, 10, name_off)
    struct.pack_into("<H", a, 12, flags)
    struct.pack_into("<H", a, 14, aid)
    struct.pack_into("<Q", a, 16, 0)              # start VCN
    struct.pack_into("<Q", a, 24, max(0, (size + CLUSTER - 1) // CLUSTER - 1))
    struct.pack_into("<H", a, 32, run_off)
    struct.pack_into("<H", a, 34, compusize)
    struct.pack_into("<Q", a, 40, alloc_size)
    struct.pack_into("<Q", a, 48, size)
    struct.pack_into("<Q", a, 56, size)           # initialized size
    a[name_off:name_off + 2 * nlen] = utf16(name)
    a[run_off:run_off + len(runb)] = runb
    return bytes(a)


def fname_value(parent, name, alloc, real, ns=1):
    v = bytearray(66 + 2 * len(name))
    struct.pack_into("<Q", v, 0, parent | (1 << 48))   # ref + seq 1
    struct.pack_into("<Q", v, 8, FTIME)
    struct.pack_into("<Q", v, 16, FTIME)
    struct.pack_into("<Q", v, 24, FTIME)
    struct.pack_into("<Q", v, 32, FTIME)
    struct.pack_into("<Q", v, 40, alloc)
    struct.pack_into("<Q", v, 48, real)
    struct.pack_into("<I", v, 56, 0)
    struct.pack_into("<I", v, 60, 0)
    v[64] = len(name)
    v[65] = ns
    v[66:] = utf16(name)
    return bytes(v)


def si_value():
    # crtime, mtime, mft-modified, accessed (48-byte v1.2 $STANDARD_INFORMATION)
    return struct.pack("<QQQQ", FTIME, FTIME, FTIME, FTIME) + b"\x00" * 16


def volinfo_value():
    return struct.pack("<QBBH", 0, 3, 1, 0) + b"\x00" * 4


def std_file_attrs(recno, parent, name, alloc, real):
    """SI + FNAME for a normal file."""
    return [res_attr(T_STD_INFO, si_value(), aid=0),
            res_attr(T_FNAME, fname_value(parent, name, alloc, real), aid=1)]


def idx_entry(ref, name, alloc, real, last=False):
    if last:
        e = bytearray(16)
        struct.pack_into("<Q", e, 0, 0)
        struct.pack_into("<H", e, 8, 16)
        struct.pack_into("<H", e, 10, 0)
        e[12] = 0x02                   # NTFS_IDX_LAST
        return bytes(e)
    key = fname_value(5, name, alloc, real)
    ln = 24 + len(key)
    ln = (ln + 7) & ~7
    e = bytearray(ln)
    struct.pack_into("<Q", e, 0, ref | (1 << 48))
    struct.pack_into("<H", e, 8, ln)
    struct.pack_into("<H", e, 10, len(key))
    e[12] = 0x00
    e[16:16 + len(key)] = key
    return bytes(e)


def idxroot_value(entries):
    ents = b"".join(entries)
    hdr = bytearray(16)
    struct.pack_into("<I", hdr, 0, T_FNAME)   # sorted by name
    struct.pack_into("<I", hdr, 4, 1)         # collation
    struct.pack_into("<I", hdr, 8, 4096)      # index block size
    hdr[12] = 8                               # clusters
    v = bytearray(16)                          # idxelist header
    struct.pack_into("<I", v, 0, 16)           # begin_off
    struct.pack_into("<I", v, 4, 16 + len(ents))
    struct.pack_into("<I", v, 8, 16 + len(ents))
    struct.pack_into("<I", v, 12, 0)
    return bytes(hdr) + bytes(v) + ents


class NtfsImage:
    def __init__(self):
        self.records = {}          # recno -> list of attr bytes
        self.rflags = {}           # recno -> flags
        self.clusters = {}         # cluster -> 512B content
        self.next_data_cluster = 128
        self.bitmap_cluster = 112

    def alloc(self, n):
        c = self.next_data_cluster
        self.next_data_cluster += n
        assert self.next_data_cluster <= NCLUSTERS, "image too small"
        return c

    def write_data(self, start, data):
        """Write data starting at cluster `start` (padded to clusters)."""
        data = bytes(data)
        pad = (-len(data)) % CLUSTER
        data += b"\x00" * pad
        for i in range(0, len(data), CLUSTER):
            self.clusters[start + i // CLUSTER] = data[i:i + CLUSTER]

    # ---- record helpers ----------------------------------------------
    def add_record(self, recno, attrs, flags=0x0001):
        self.records[recno] = attrs
        self.rflags[recno] = flags

    def add_file_rec(self, recno, name, data_attrs, size, alloc, parent=5):
        attrs = std_file_attrs(recno, parent, name, alloc, size)
        attrs += data_attrs
        self.add_record(recno, attrs)

    def add_dir_rec(self, recno, name, children, parent=5):
        ents = [idx_entry(ref, cname, calloc, creal)
                for (ref, cname, calloc, creal) in children]
        ents.append(idx_entry(0, "", 0, 0, last=True))
        attrs = std_file_attrs(recno, parent, name,
                               len(ents) * 64, len(ents) * 64)
        attrs.append(res_attr(T_IDXROOT, idxroot_value(ents), aid=2))
        self.add_record(recno, attrs, flags=0x0003)

    # ---- standard metadata records ------------------------------------
    def build_standard_records(self):
        mft_clusters = N_MFT_RECORDS * MFT_REC_SIZE // CLUSTER
        # 0 $MFT
        self.add_record(0, [nonres_attr(T_DATA, [(mft_clusters, MFT_START)],
                                       N_MFT_RECORDS * MFT_REC_SIZE)])
        # 1 $MFTMirr (4 clusters at 8)
        self.write_data(8, self._mftmirr_bytes())
        self.add_record(1, [nonres_attr(T_DATA, [(4, 8)], 2048)])
        # 2 $LogFile
        self.add_record(2, [res_attr(T_DATA, b"")])
        # 3 $Volume
        self.add_record(3, [
            res_attr(T_STD_INFO, si_value(), aid=0),
            res_attr(T_FNAME, fname_value(5, "$Volume", 0, 0, ns=0), aid=1),
            res_attr(T_VOLINFO, volinfo_value(), aid=2)])
        # 4 $AttrDef
        self.add_record(4, [res_attr(T_DATA, b"")])
        # 5 root dir - children filled by caller via set_root_children
        # 6 $Bitmap
        bmb = (NCLUSTERS + 7) // 8
        self.write_data(self.bitmap_cluster, b"\xff" * bmb)
        self.add_record(6, [nonres_attr(T_DATA, [(1, self.bitmap_cluster)], bmb)])
        # 7 $Boot
        # content set at build() (copy of boot sector)
        # 8 $BadClus
        self.add_record(8, [res_attr(T_DATA, b"")])
        # 9 $Secure (7 attributes; $SDS/$O empty, index attrs empty)
        self.add_record(9, [
            res_attr(T_STD_INFO, si_value(), aid=0),
            res_attr(T_FNAME, fname_value(5, "$Secure", 0, 0, ns=0), aid=1),
            nonres_attr(T_DATA, [], 0, name="$SDS", aid=2),
            res_attr(T_IDXROOT, idxroot_value([idx_entry(0, "", 0, 0, last=True)]),
                     name="$SDH", aid=3),
            nonres_attr(T_IDXALLOC, [], 0, name="$SII", aid=4),
            res_attr(T_BITMAP, b"\x00" * 8, name="$SDH", aid=5),
            nonres_attr(T_DATA, [], 0, name="$O", aid=6),
        ])
        # 10 $UpCase
        self.add_record(10, [res_attr(T_DATA, b"")])
        # 11 $Extend
        self.add_record(11, [res_attr(T_DATA, b"")], flags=0x0003)
        # 12..N unused (zeroed)

    def _mftmirr_bytes(self):
        buf = bytearray(2048)
        for r in (0, 1):
            if r in self.records:
                buf[r * MFT_REC_SIZE:(r + 1) * MFT_REC_SIZE] = \
                    self._record_bytes(r)
        return buf

    def set_root_children(self, children):
        ents = [idx_entry(ref, cname, calloc, creal)
                for (ref, cname, calloc, creal) in children]
        ents.append(idx_entry(0, "", 0, 0, last=True))
        attrs = std_file_attrs(5, 5, ".", len(ents) * 64, len(ents) * 64)
        attrs.append(res_attr(T_IDXROOT, idxroot_value(ents), aid=2))
        self.add_record(5, attrs, flags=0x0003)

    # ---- serialization -------------------------------------------------
    def _record_bytes(self, recno):
        rec = bytearray(MFT_REC_SIZE)
        rec[0:4] = b"FILE"
        struct.pack_into("<H", rec, 4, 48)          # upd_off
        struct.pack_into("<H", rec, 6, 3)           # upd_cnt
        struct.pack_into("<Q", rec, 8, 0)           # lsn
        struct.pack_into("<H", rec, 16, 1)          # seq
        struct.pack_into("<H", rec, 18, 1)          # link
        struct.pack_into("<H", rec, 20, 56)         # attr_off
        struct.pack_into("<H", rec, 22, self.rflags.get(recno, 0x0001))
        struct.pack_into("<I", rec, 28, MFT_REC_SIZE)  # alloc_size
        struct.pack_into("<H", rec, 40, 32)         # next_attrid
        struct.pack_into("<I", rec, 44, recno)      # entry number
        off = 56
        for a in self.records.get(recno, []):
            rec[off:off + len(a)] = a
            off += len(a)
        struct.pack_into("<I", rec, 24, off)        # used size
        # fixups: sectors 0-511, 512-1023
        rec[50] = rec[510]                          # fixup array entry 1
        rec[51] = rec[511]
        rec[52] = rec[1022]                         # fixup array entry 2
        rec[53] = rec[1023]
        rec[48:50] = b"\x01\x00"                    # update seq number
        rec[510:512] = b"\x01\x00"
        rec[1022:1024] = b"\x01\x00"
        return bytes(rec)

    def build(self):
        img = bytearray(NCLUSTERS * CLUSTER)
        # MFT records
        for r in range(N_MFT_RECORDS):
            if r in self.records:
                img[(MFT_START + r * 2) * CLUSTER:
                    (MFT_START + r * 2 + 2) * CLUSTER] = self._record_bytes(r)
        # other written clusters ($MFTMirr, $Bitmap, user data)
        for c, chunk in self.clusters.items():
            img[c * CLUSTER:(c + 1) * CLUSTER] = chunk
        # $Boot record 7 (copy of boot sector) - record 7 written below
        # boot sector
        boot = bytearray(512)
        boot[0:3] = b"\xEB\x52\x90"
        boot[3:11] = b"NTFS    "
        struct.pack_into("<H", boot, 11, 512)       # bytes/sector
        boot[13] = 1                                # sectors/cluster
        struct.pack_into("<Q", boot, 40, NCLUSTERS)
        struct.pack_into("<Q", boot, 48, MFT_START)
        struct.pack_into("<Q", boot, 56, 8)         # $MFTMirr cluster
        boot[64] = 2                                # mft rec = 2 clusters
        boot[68] = 8                                # index rec = 8 clusters
        boot[72:80] = b"OHOSNTFS"
        struct.pack_into("<H", boot, 510, 0xAA55)
        img[0:512] = boot
        img[510:512] = b"\x55\xAA"
        # $Boot record content = copy of the boot sector
        img[(MFT_START + 7 * 2) * CLUSTER:(MFT_START + 7 * 2) * CLUSTER + 512] = boot
        return bytes(img)


# ---- fixture builders --------------------------------------------------

def build_fe_ntfs_partition():
    """NTFS partition of fe_test_1.img (offset 32256).

    read_apis:test_ntfs_fe   -> testfile(31) non-resident, testfile(32) resident
    fs_fname_apis            -> dir_open_apis("/allocated", 30), walk(30)
    fs_attrlist_apis         -> get_apis(35, 3 attrs), get_apis(9, 7 attrs)
    """
    nt = NtfsImage()
    nt.build_standard_records()
    nt.set_root_children([(30, "allocated", 4096, 0)])
    # 31 non-resident file (3000 B = 6 clusters @512B)
    c31 = nt.alloc(6)
    nt.write_data(c31, b"N" * 3000)
    nt.add_file_rec(31, "nonres.dat",
                    [nonres_attr(T_DATA, [(6, c31)], 3000)], 3000, 4096,
                    parent=30)
    # 32 resident file
    nt.add_file_rec(32, "res.dat", [res_attr(T_DATA, b"R" * 100, aid=2)],
                    100, 100, parent=30)
    # 35 three-attribute file
    c35 = nt.alloc(4)
    nt.write_data(c35, b"T" * 2000)
    nt.add_file_rec(35, "three.dat",
                    [nonres_attr(T_DATA, [(4, c35)], 2000, aid=2)],
                    2000, 1536, parent=30)
    # 30 /allocated directory
    nt.add_dir_rec(30, "allocated",
                   [(31, "nonres.dat", 4096, 3000),
                    (32, "res.dat", 100, 100),
                    (35, "three.dat", 1536, 2000)])
    # re-apply children (add_dir_rec overwrote record 30's entry list order;
    # set_root_children must point at 30 which now exists)
    return nt.build()


def build_ntfs_comp():
    """ntfs-comp-1.img: read_apis:test_ntfs_comp.

    testfile(34) compressed, testfile(32) sparse.
    """
    nt = NtfsImage()
    nt.build_standard_records()
    nt.set_root_children([(34, "comp.dat", 5632, 5120),
                          (32, "sparse.dat", 8192, 8192)])
    # 32 sparse file: one hole run of 16 clusters
    nt.add_file_rec(32, "sparse.dat",
                    [nonres_attr(T_DATA, [(16, None)], 8192, aid=2)],
                    8192, 8192)
    # 34 compressed file: LZNT1 stored chunks
    # unit = 2^4 clusters = 8192 B; stored stream 5124 B -> 11 clusters,
    # padded to the 16-cluster unit boundary with a sparse run.
    chunk = lambda n: struct.pack("<H", n + 2 - 3) + b"C" * n
    stream = chunk(4096) + chunk(1024) + b"\x00\x00"
    c34 = nt.alloc(11)
    nt.write_data(c34, stream)
    nt.add_file_rec(34, "comp.dat",
                    [nonres_attr(T_DATA, [(11, c34), (5, None)], 5120,
                                 flags=0x0001, compusize=4,
                                 alloc_size=16 * CLUSTER)],
                    5120, 16 * CLUSTER)
    return nt.build()


def build_ntfs_kw():
    """ntfs-img-kw-1.dd: read_apis:test_ntfs_slack_ads.

    inode 36 file-n-4.dat: size 2000; read at 1536 w/o slack -> 464,
    with slack -> 512, "n-slack" at file offset 2021 (cluster byte 485).
    inode 37 file-n-5.dat: unnamed $DATA size 1300 with attribute id 3,
    $DATA:"here" size 2000 with attribute id 5.
    """
    nt = NtfsImage()
    nt.build_standard_records()
    nt.set_root_children([(36, "file-n-4.dat", 2048, 2000),
                          (37, "file-n-5.dat", 4096, 2000)])
    # 36: 4 clusters; last cluster = 464 valid bytes + slack marker
    last = bytearray(512)
    last[0:464] = b"B" * 464
    last[485:492] = b"n-slack"
    c36 = nt.alloc(4)
    nt.write_data(c36, b"A" * 1536 + bytes(last))
    nt.add_file_rec(36, "file-n-4.dat",
                    [nonres_attr(T_DATA, [(4, c36)], 2000, aid=2)],
                    2000, 2048)
    # 37: two $DATA attributes with explicit ids 3 and 5
    c37a = nt.alloc(3)
    nt.write_data(c37a, b"D" * 1300)
    c37b = nt.alloc(4)
    nt.write_data(c37b, b"H" * 2000)
    attrs = std_file_attrs(37, 5, "file-n-5.dat", 4096, 2000)
    attrs.append(nonres_attr(T_DATA, [(3, c37a)], 1300, aid=3))
    attrs.append(nonres_attr(T_DATA, [(4, c37b)], 2000, name="here", aid=5))
    nt.add_record(37, attrs)
    return nt.build()




# ---- entry point --------------------------------------------------------

if __name__ == "__main__":
    import os
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    images = {
        "fat12.dd": build_fat12_dd(),
        "fat-img-kw.dd": build_fat_img_kw(),
        "fat32.dd": build_fat32_dd(),
        "ntfs-comp-1.img": build_ntfs_comp(),
        "ntfs-img-kw-1.dd": build_ntfs_kw(),
    }
    # fe_test_1.img: composite with an NTFS partition at offset 32256 and a
    # FAT16 partition at 41126400 (the two offsets hardcoded upstream in
    # read_apis.cpp / fs_fname_apis.cpp / fs_attrlist_apis.cpp)
    fat_fe = build_fe_fat_partition()
    ntfs_fe = build_fe_ntfs_partition()
    fe = bytearray(41126400 + len(fat_fe))
    fe[32256:32256 + len(ntfs_fe)] = ntfs_fe
    fe[41126400:] = fat_fe
    images["fe_test_1.img"] = bytes(fe)
    for name, data in images.items():
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        print("generated", name, len(data), "bytes")
