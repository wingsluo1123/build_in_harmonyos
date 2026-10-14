#!/usr/bin/env python3
"""make_fixture.py — 生成一张最小合法 FFS2 固件卷，供 test.sh 做真实解析验证。

为什么需要它
------------
上游**没有任何测试语料**（无 tests/ 目录、无种子语料），而消费者用例如果只跑
`--version` / `--help`，证明不了"解析器真的能解析固件"。本脚本用纯标准库按
UEFI PI 规范拼出一张最小但**结构合法**的 FFS2 卷，让 uefiextract / uefifind
真的走一遍 flash-image → volume → file → section 的完整解析链路。

镜像是**无警告**的（这是刻意要求）
----------------------------------
上游在解析期对每处不合规都只发 msg() 警告、不改变退出码，所以一张"带警告的
合法卷"很容易被误当成通过。本脚本的目标是让
`uefiextract <img> report` 的日志里**一条 parse 警告都不出现**：

  * 文件头校验和用**上游自己的算法**（不是 PI 文档里的写法）：
        ffsparser.cpp:2187
        calculatedHeader =
            0x100 - (calculateSum8(header) - Checksum.Header
                                        - Checksum.File
                                        - State)
    即 **8 位**字节和取补，且把 Header / File / **State** 三个字节都当作 0
    （State 在偏移 0x17）。注意这是"排除三字节"而非"排除两字节"——按 PI
    文档只排除 IntegrityCheck 两个字节会算出别的值，实测会报
    `invalid header checksum ... should be XXh`。
  * 数据校验和：`Attributes & FFS_ATTRIB_CHECKSUM` 为 0 且 FFSv2 卷
    （volumeRevision == 2）时，上游要求 IntegrityCheck.Checksum.File 等于
    **FFS_FIXED_CHECKSUM2 = 0xAA**（ffs.h:301 / ffsparser.cpp:2205）。
  * 卷里必须有一个 **Volume Top File**，否则上游会报
    `parse: not a single Volume Top File is found, the image may be corrupted`，
    并且**整遍第二道解析被跳过**（ffsparser.cpp:103-109）：
        if (lastVtf.isValid()) { result = performSecondPass(root); }
        else { msg("... not a single Volume Top File ..."); }
    第二道解析做的是**地址侧分析**（reset vector / FIT / protected ranges /
    TE image base，见 ffsparser.cpp:3806），**不是**段解析 —— 段在第一遍
    parseFile→parseSections 里就已经解析完了。所以这个 VTF 的作用是"消掉告警
    + 让第二道解析真的跑起来"，而不是"让段能被解析"。
    VTF 由 GUID 判定（ffsparser.cpp:2244 比对 EFI_FFS_VOLUME_TOP_FILE_GUID），
    不依赖文件类型或段内容。

镜像布局（全部小端）
--------------------
offset 0x00  EFI_FIRMWARE_VOLUME_HEADER（56 字节）+ BlockMap（2 项 × 8 字节）
             = HeaderLength 0x48
  0x00  ZeroVector[16]                    全 0
  0x10  FileSystemGuid[16]                78E58C8C-3D8A-1C4F-9935-896185C32DD3
                                          （= EFI_FIRMWARE_FILE_SYSTEM2_GUID，
                                           见 common/ffs.cpp:49 的逐字节定义；
                                           在 FFSv2Volumes 表内 ⇒ 被识别为 FFSv2 卷）
  0x20  FvLength      u64 = 0x1000
  0x28  Signature[4]  "_FVH"              （EFI_FV_SIGNATURE = 0x4856465F）
  0x2C  Attributes    u32 = 0x00000800    （EFI_FVB_ERASE_POLARITY ⇒ 空白字节 = 0xFF）
  0x30  HeaderLength  u16 = 0x0048
  0x32  Checksum      u16                 16 位字和（Checksum 置 0 后求和，再取补）
  0x34  ExtHeaderOffset u16 = 0
  0x36  Reserved      u8  = 0
  0x37  Revision      u8  = 2             （FFSv2 ⇒ volumeRevision = 2）
  0x38  BlockMap[0]   NumBlocks=1, Length=0x1000
  0x40  BlockMap[1]   0, 0                （终止项，解析器据此结束遍历）

offset 0x48  FFS 文件 #1：探测文件（FREEFORM）
  0x48  Name[16]      A1B2C3D4-E5F6-4A5B-8C9D-0E1F2A3B4C5D
  0x58  IntegrityCheck u16                （Header=8 位补码，File=0xAA）
  0x5A  Type          u8 = 0x02           （EFI_FV_FILETYPE_FREEFORM）
  0x5B  Attributes    u8 = 0x00
  0x5C  Size[3]       u24 = 0x000040      （含 24 字节头；64 字节，8 字节对齐）
  0x5F  State         u8 = 0xF8           （标准"有效文件"状态）
  0x60  EFI_COMMON_SECTION_HEADER（4 字节）
  0x60    Size[3]     u24 = 0x000028      （含 4 字节段头；40 字节）
  0x63    Type        u8 = 0x19           （EFI_SECTION_RAW）
  0x64    Section body（36 字节）
          EF BE AD DE | "UEFITOOL-OHOS-CONSUMER-PROBE-001"
          ↑ 这两个探测串是 report / uefifind 断言的锚点

offset 0x88  FFS 文件 #2：Volume Top File（必须存在，见上）
  0x88  Name[16]      1BA0062E-C779-4582-8566-336AE8F78F09
                      （= EFI_FFS_VOLUME_TOP_FILE_GUID，ffs.cpp:74 的逐字节定义）
  0x98  IntegrityCheck u16                （同上算法）
  0x9A  Type          u8 = 0x02
  0x9B  Attributes    u8 = 0x00
  0x9C  Size[3]       u24 = 0x000040      （64 字节）
  0x9F  State         u8 = 0xF8
  0xA0  Section header u24=0x28, Type=0x19
  0xA4  Section body（36 字节）
        CA FE BA BE | "UEFITOOL-OHOS-VTF-ANCHOR-0001" | 00 ×3
        ↑ 刻意不含 EF BE AD DE，避免污染"魔数仅命中一次"的断言

其后到 0x1000 全部 0xFF（= erase polarity 决定的空白字节，解析器据此判定卷尾空白）

为什么两个文件都必须是 64 字节
------------------------------
除"8 字节对齐"外没有别的原因；把两个文件都做成 64 字节可以让布局与偏移一眼可算。

★ VTF 同时是 `uefiextract <img> guids` 子模式能产出内容的前提
----------------------------------------------------------------
上游 common/guiddatabase.cpp:124 的 guidDatabaseFromTreeRecursive() 是这样筛选的：

    if (model->type(index) == Types::File && !model->text(index).isEmpty())
        db[<header 前 16 字节>] = model->text(index);

它用的是 **text**，而 FFS 文件的**可读名**实际存在 **name** 字段里
（ffsparser.cpp:2222 `name = guidToUString(fileHeader->Name)`，
 ffsparser.cpp:2262 `model->addItem(..., name, text, info, ...)`）。
text 是另一个"短注记"字段，普通文件恒为空，只有 VTF / NVRAM store /
apriori / protected-range hash 这类特殊文件才会被赋值 —— 所以**没有 VTF 的镜像会让
GUID 库为空**，而 guids 分支一旦拿到空库就会落穿到 print_usage() 并返回 1
（uefiextract_main.cpp:102-107 缺终结 return，第 217-218 行兜底）。
本 fixture 放一个 VTF，既满足规范，也让 guids 子模式有确定性的可断言产物。

用法：python3 make_fixture.py <输出文件路径>
"""
from __future__ import annotations

import struct
import sys

# EFI_FIRMWARE_FILE_SYSTEM2_GUID = 8C8CE578-8A3D-4F1C-9935-896185C32DD3
# （EFI GUID 前三个字段按小端落盘，后两个字段原样落盘）
VOLUME_GUID = bytes.fromhex("78e58c8c3d8a1c4f9935896185c32dd3")

# 探测文件 GUID = A1B2C3D4-E5F6-4A5B-8C9D-0E1F2A3B4C5D
# 刻意选一个不在 UEFI PI 规范里、也不在上游 known-GUID 表里的值，
# 避免被解析器按特殊文件（FV top file / NVRAM / 微码等）走别的分支。
PROBE_FILE_GUID = bytes.fromhex("d4c3b2a1f6e55b4a8c9d0e1f2a3b4c5d")

# EFI_FFS_VOLUME_TOP_FILE_GUID = 1BA0062E-C779-4582-8566-336AE8F78F09
# 逐字节取自 common/ffs.cpp:74：
#   "\x2E\x06\xA0\x1B\x79\xC7\x82\x45\x85\x66\x33\x6A\xE8\xF7\x8F\x09"
VTF_FILE_GUID = bytes.fromhex("2e06a01b79c782458566336ae8f78f09")

# 消费者用例按 GUID 断言，字符串形态（去掉连字符、大写）与 guidToUString 一致
PROBE_FILE_GUID_STR = "A1B2C3D4E5F64A5B8C9D0E1F2A3B4C5D"
VTF_FILE_GUID_STR = "1BA0062EC77945828566336AE8F78F09"

# 探测文件段体：4 字节魔数 + 32 字节 ASCII 标记
# 长度刻意凑成 36 字节 ⇒ 段 40 字节 ⇒ 文件 64 字节（24+40），使 FFS 文件 8 字节对齐
PROBE_MAGIC = b"\xef\xbe\xad\xde"
PROBE_TEXT = b"UEFITOOL-OHOS-CONSUMER-PROBE-001"
PROBE_PAYLOAD = PROBE_MAGIC + PROBE_TEXT

# VTF 段体：4 字节魔数（**不用** EF BE AD DE）+ 标记 + 补零 = 36 字节
VTF_MAGIC = b"\xca\xfe\xba\xbe"
VTF_TEXT = b"UEFITOOL-OHOS-VTF-ANCHOR-0001"
assert len(VTF_MAGIC) + len(VTF_TEXT) <= 36, len(VTF_TEXT)
VTF_PAYLOAD = VTF_MAGIC + VTF_TEXT + b"\x00" * (36 - len(VTF_MAGIC) - len(VTF_TEXT))

VOLUME_SIZE = 0x1000
VOLUME_HEADER_LEN = 0x48          # 56（卷头）+ 2 * 8（BlockMap 一项 + 终止项）
FILE_HEADER_LEN = 24
SECTION_HEADER_LEN = 4
FILE_TYPE_FREEFORM = 0x02
FILE_STATE_VALID = 0xF8
SECTION_TYPE_RAW = 0x19
ATTR_ERASE_POLARITY = 0x00000800  # ⇒ 空白字节 0xFF
EMPTY_BYTE = 0xFF

# 上游常量（ffs.h:300-301）
FFS_FIXED_CHECKSUM = 0x5A         # volumeRevision == 1
FFS_FIXED_CHECKSUM2 = 0xAA        # volumeRevision != 1（本 fixture 走这条）

# FFS 文件头字段偏移
OFF_INTEGRITY_HEADER = 0x10
OFF_INTEGRITY_FILE = 0x11
OFF_STATE = 0x17
OFF_FILE_HEADER_SIZE = 0x14       # Size[3]（u24）

assert len(PROBE_PAYLOAD) == 36, len(PROBE_PAYLOAD)
assert len(VTF_PAYLOAD) == 36, len(VTF_PAYLOAD)
assert len(VTF_FILE_GUID) == 16, len(VTF_FILE_GUID)


def checksum16(data: bytes) -> int:
    """16 位字和取补 —— 卷头 Checksum 用，与上游 common/utility.cpp 的
    calculateChecksum16 同式：

        counter = sum(u16 words)
        return (UINT16)(0x10000 - counter)

    上游校验时先把 Checksum 字段清零再算，然后与落盘值比较。
    """
    total = 0
    for i in range(0, len(data) - 1, 2):
        total += data[i] | (data[i + 1] << 8)
    return (0x10000 - (total & 0xFFFF)) & 0xFFFF


def ffs_header_checksum8(header: bytes) -> int:
    """FFS 文件头的 **8 位**校验和，严格照上游 ffsparser.cpp:2187 的式子：

        calculated = 0x100 - (calculateSum8(header)
                              - Checksum.Header - Checksum.File - State)

    代入 h 自身后可以化简：设 S0 = 把头里 0x10 / 0x11 / 0x17 三字节当作 0 之后的
    字节和，则上游期望的 h 恒等于 (0x100 - S0) & 0xFF（与 h/f/s 的具体取值无关，
    因为 calculateSum8 的 UINT8 回绕在模 256 下被消掉）。所以这里一趟就能算准，
    不需要迭代逼近。
    """
    total = sum(
        b for i, b in enumerate(header)
        if i not in (OFF_INTEGRITY_HEADER, OFF_INTEGRITY_FILE, OFF_STATE)
    )
    return (0x100 - (total & 0xFF)) & 0xFF


def build_volume_header() -> bytearray:
    hdr = bytearray()
    hdr += b"\x00" * 16                                     # ZeroVector
    hdr += VOLUME_GUID                                      # FileSystemGuid
    hdr += struct.pack("<Q", VOLUME_SIZE)                   # FvLength
    hdr += b"_FVH"                                          # Signature
    hdr += struct.pack("<I", ATTR_ERASE_POLARITY)           # Attributes
    hdr += struct.pack("<H", VOLUME_HEADER_LEN)             # HeaderLength
    hdr += struct.pack("<H", 0)                             # Checksum（占位，下面回填）
    hdr += struct.pack("<H", 0)                             # ExtHeaderOffset
    hdr += bytes([0])                                       # Reserved
    hdr += bytes([2])                                       # Revision = 2（FFSv2）
    hdr += struct.pack("<II", 1, VOLUME_SIZE)               # BlockMap[0]
    hdr += struct.pack("<II", 0, 0)                         # BlockMap 终止项
    assert len(hdr) == VOLUME_HEADER_LEN, len(hdr)
    # 回填 16 位头校验和（此刻 Checksum 字段为 0，与上游算法口径一致）
    hdr[0x32:0x34] = struct.pack("<H", checksum16(bytes(hdr)))
    return hdr


def build_ffs_file(guid: bytes, payload: bytes) -> bytes:
    """拼一个 FREEFORM 文件：24 字节文件头 + 一个 RAW 段。"""
    assert len(guid) == 16, len(guid)

    section = struct.pack("<I", SECTION_HEADER_LEN + len(payload))[:3] \
        + bytes([SECTION_TYPE_RAW]) + payload
    assert len(section) == SECTION_HEADER_LEN + len(payload), len(section)

    file_size = FILE_HEADER_LEN + len(section)
    fhdr = bytearray()
    fhdr += guid                                            # Name
    fhdr += bytes([0x00, FFS_FIXED_CHECKSUM2])              # IntegrityCheck 占位
    fhdr += bytes([FILE_TYPE_FREEFORM])                     # Type
    fhdr += bytes([0x00])                                   # Attributes
    fhdr += struct.pack("<I", file_size)[:3]                # Size（u24）
    fhdr += bytes([FILE_STATE_VALID])                       # State
    assert len(fhdr) == FILE_HEADER_LEN, len(fhdr)

    # Header 校验和（8 位补码，排除 Header/File/State 三字节）
    fhdr[OFF_INTEGRITY_HEADER] = ffs_header_checksum8(bytes(fhdr))
    # File 校验和：Attributes 未置 FFS_ATTRIB_CHECKSUM 且 FFSv2 ⇒ 固定值 0xAA
    assert fhdr[OFF_INTEGRITY_FILE] == FFS_FIXED_CHECKSUM2

    # 自检：用上游的式子复核一遍（含 h/f/s 自身参与 sum8 的完整形态）
    total8 = sum(fhdr) & 0xFF
    recomputed = (0x100 - (total8
                           - fhdr[OFF_INTEGRITY_HEADER]
                           - fhdr[OFF_INTEGRITY_FILE]
                           - fhdr[OFF_STATE])) & 0xFF
    assert recomputed == fhdr[OFF_INTEGRITY_HEADER], (recomputed, fhdr[OFF_INTEGRITY_HEADER])

    return bytes(fhdr) + section


def build_image() -> bytes:
    # 顺序：探测文件在前，Volume Top File 在后（VTF 按规范必须是卷内最后一个文件）
    files = build_ffs_file(PROBE_FILE_GUID, PROBE_PAYLOAD) \
        + build_ffs_file(VTF_FILE_GUID, VTF_PAYLOAD)
    assert len(files) % 8 == 0, len(files)
    body = files + bytes([EMPTY_BYTE]) * (VOLUME_SIZE - VOLUME_HEADER_LEN - len(files))
    image = bytes(build_volume_header()) + body
    assert len(image) == VOLUME_SIZE, len(image)
    return image


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.split("用法：")[-1].strip(), file=sys.stderr)
        return 2
    with open(argv[1], "wb") as handle:
        handle.write(build_image())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
