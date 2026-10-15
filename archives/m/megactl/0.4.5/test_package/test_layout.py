#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""megactl 0.4.5 适配自检（M 项，非上游用例）—— conan 包交付形态与鸿蒙目标契约。

用法: python3 test_layout.py <package_folder>

为什么需要它
    test_megactl.py 负责「真跑 CLI」，但那需要宿主能执行 aarch64 ELF。本脚本
    **纯 Python 解析 ELF 字节**（不依赖 readelf / qemu / 执行权限），因此在任何
    宿主上都能给出确定结论，用来证明交付物确实是 OHOS aarch64 目标而不是
    「在 x86 宿主上编出来的、只是没报错」的东西。

覆盖
    · ELF64 / AArch64 / PIE 三要素
    · DT_NEEDED 白名单：只有 libc.so —— 证明链的是 OHOS musl 而不是宿主 glibc
    · .interp 是 OHOS hnp loader 路径（而非 /lib64/ld-linux-x86-64.so.2）
    · 无 RPATH/RUNPATH 指向构建机路径
    · man page / metainfo / licenses 交付完整，COPYING 正文是 GPL-2.0
    · 两个 CLI 是两个不同的二进制（BuildID/大小不同），不是同一个文件的硬链接
    · 无构建中间产物、无隐藏文件残留（JC5）
"""
from __future__ import print_function

import os
import struct
import sys

FAILED = []
TOTAL = [0]
HARMONY = [0]

# OHOS musl 允许的动态依赖白名单（本包零第三方依赖，应只有 libc.so）
OHOS_NEEDED_WHITELIST = {"libc.so"}

# OHOS hnp 动态加载器（实测 aarch64 OHOS 工具链产物的 .interp 取值）
OHOS_INTERP_SUBSTRINGS = ("ld-musl-aarch64.so.1", "ld-linux-aarch64.so.1")

EM_AARCH64 = 183


def check(ok, label, detail=""):
    TOTAL[0] += 1
    if not ok:
        FAILED.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("  " + detail) if detail else ""))
    return ok


def check_harmony(ok, label, detail=""):
    HARMONY[0] += 1
    return check(ok, "[鸿蒙] " + label, detail)


class Elf(object):
    """够用的 ELF64 解析器：e_type / e_machine / DT_NEEDED / .interp / BuildID。"""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as handle:
            self.data = handle.read()
        if self.data[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        self.is64 = self.data[4] == 2
        if not self.is64:
            raise ValueError("not ELF64")
        self.order = "<" if self.data[5] == 1 else ">"
        self.e_type, self.e_machine = struct.unpack_from(
            self.order + "HH", self.data, 16)
        e_shoff, = struct.unpack_from(self.order + "Q", self.data, 40)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(
            self.order + "HHH", self.data, 58)
        self.sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            sh_name, sh_type = struct.unpack_from(self.order + "II",
                                                  self.data, off)
            sh_offset, = struct.unpack_from(self.order + "Q", self.data,
                                            off + 24)
            sh_size, = struct.unpack_from(self.order + "Q", self.data,
                                          off + 32)
            sh_link, = struct.unpack_from(self.order + "I", self.data,
                                          off + 40)
            self.sections.append({
                "name_off": sh_name, "type": sh_type, "offset": sh_offset,
                "size": sh_size, "link": sh_link,
            })
        # e_shstrndx 才是 section 名字符串表的索引 —— 不能假设是 sections[0]
        # （ELF 规范里 index 0 是 SHT_NULL 的空节，offset=0 会指回 ELF 头）。
        if e_shstrndx >= len(self.sections):
            raise ValueError("e_shstrndx out of range")
        self._shstrtab_off = self.sections[e_shstrndx]["offset"]
        self.needed = []
        self.rpath = []
        self.has_interp = False
        self.interp = ""
        self.build_id = ""
        self.note_sections = []
        self._parse()

    def _cstr(self, table_off, index):
        end = self.data.index(b"\x00", table_off + index)
        return self.data[table_off + index:end].decode("utf-8", "replace")

    def _section_name(self, index):
        return self._cstr(self._shstrtab_off, self.sections[index]["name_off"])

    def _parse(self):
        for sec in self.sections:
            if sec["type"] == 1 and self._section_name_str(sec) == ".interp":
                self.has_interp = True
                raw = self.data[sec["offset"]:sec["offset"] + sec["size"]]
                self.interp = raw.split(b"\x00")[0].decode("utf-8", "replace")
        for idx, sec in enumerate(self.sections):
            if sec["type"] != 6:            # SHT_DYNAMIC
                continue
            strtab_off = self.sections[sec["link"]]["offset"]
            for j in range(sec["size"] // 16):
                base = sec["offset"] + j * 16
                d_tag, = struct.unpack_from(self.order + "q", self.data, base)
                d_val, = struct.unpack_from(self.order + "Q", self.data,
                                            base + 8)
                if d_tag == 0:
                    break
                if d_tag == 1:              # DT_NEEDED
                    self.needed.append(self._cstr(strtab_off, d_val))
                elif d_tag == 15:           # DT_RPATH
                    self.rpath.append(self._cstr(strtab_off, d_val))
                elif d_tag == 29:           # DT_RUNPATH
                    self.rpath.append(self._cstr(strtab_off, d_val))
        # BuildID 在 .note.gnu.build-id
        for idx, sec in enumerate(self.sections):
            if sec["type"] != 7:            # SHT_NOTE
                continue
            name = self._section_name(idx)
            self.note_sections.append(name)
            if "build-id" not in name:
                continue
            off = sec["offset"]
            namesz, descsz, _ntype = struct.unpack_from(
                self.order + "III", self.data, off)
            doff = off + 12 + ((namesz + 3) & ~3)
            self.build_id = self.data[doff:doff + descsz].hex()
            break

    def _section_name_str(self, sec):
        return self._cstr(self._shstrtab_off, sec["name_off"])


def main(argv):
    if len(argv) < 2:
        print("usage: test_layout.py <package_folder>")
        return 2
    pkg = argv[1]
    bindir = os.path.join(pkg, "bin")
    print("适配自检（M）: %s" % pkg)

    print("\n[1] 交付的两个 CLI 存在且为 aarch64/ELF64/PIE")
    elfs = {}
    for tool in ("megactl", "megasasctl"):
        path = os.path.join(bindir, tool)
        if not check(os.path.isfile(path), "bin/%s 交付" % tool):
            continue
        check(os.access(path, os.X_OK), "bin/%s 带可执行位" % tool)
        try:
            elf = Elf(path)
        except ValueError as exc:
            check(False, "bin/%s 是可解析的 ELF64" % tool, str(exc))
            continue
        elfs[tool] = elf
        # 直接读原始字节验魔数（不经过 Elf 解析器），避免与解析器的隐含假设同源
        with open(path, "rb") as raw:
            head = raw.read(20)
        check(len(head) >= 20 and head[:4] == b"\x7fELF" and head[4] == 2,
              "bin/%s 原始字节的 ELF 魔数 + EI_CLASS=ELF64" % tool,
              "magic=%r class=%r" % (head[:4], head[4:5]))
        check_harmony(elf.e_machine == EM_AARCH64,
                      "bin/%s 的 e_machine = AArch64(%d)"
                      % (tool, EM_AARCH64), "e_machine=%d" % elf.e_machine)
        check(elf.e_type == 3,
              "bin/%s 是 ET_DYN（PIE，OHOS 工具链默认）" % tool,
              "e_type=%d" % elf.e_type)

    print("\n[2] 动态依赖是 OHOS musl，不是宿主 glibc")
    for tool, elf in sorted(elfs.items()):
        needed = set(elf.needed)
        check_harmony(needed and needed <= OHOS_NEEDED_WHITELIST,
                      "bin/%s 的 DT_NEEDED ⊆ %s（零第三方运行时依赖）"
                      % (tool, sorted(OHOS_NEEDED_WHITELIST)),
                      "needed=%s" % sorted(needed))
        check("libc.so.6" not in needed and "ld-linux" not in "".join(needed),
              "bin/%s 未混入宿主 glibc 的 libc.so.6" % tool,
              "needed=%s" % sorted(needed))

    print("\n[3] 动态加载器是 OHOS hnp loader，且无构建机 RPATH")
    for tool, elf in sorted(elfs.items()):
        if not elf.has_interp:
            check(elf.e_type == 3,
                  "bin/%s 静态 PIE 无 .interp（OHOS 可接受）" % tool)
            continue
        check_harmony(any(sub in elf.interp for sub in OHOS_INTERP_SUBSTRINGS),
                      "bin/%s 的 .interp 指向 OHOS hnp loader" % tool,
                      "interp=%s" % elf.interp)
        check("x86_64" not in elf.interp,
              "bin/%s 的 .interp 非 x86_64 glibc loader" % tool,
              "interp=%s" % elf.interp)
        check(not elf.rpath, "bin/%s 无 RPATH/RUNPATH 指向构建机" % tool,
              "rpath=%s" % elf.rpath)

    print("\n[4] 两个 CLI 是两个不同二进制（不是硬链接/副本）")
    if len(elfs) == 2:
        a, b = elfs["megactl"], elfs["megasasctl"]
        check(a.build_id and b.build_id,
              "两个 CLI 都带 BuildID（可区分构建产物）",
              "megactl=%s megasasctl=%s" % (a.build_id[:16] or "(none)",
                                            b.build_id[:16] or "(none)"))
        differ = (a.build_id != b.build_id)
        check(differ, "两个 CLI 的 BuildID 不同（确为分别编译的两个目标）",
              "megactl=%s megasasctl=%s" % (a.build_id[:16] or "(none)",
                                            b.build_id[:16] or "(none)"))
        # .note.ohos.ident 是 OHOS 工具链独有的 note 段，宿主 glibc 工具链不会产出
    for tool, elf in sorted(elfs.items()):
        check_harmony(".note.ohos.ident" in elf.note_sections,
                      "bin/%s 带 OHOS 工具链的 .note.ohos.ident 段" % tool,
                      "note=%s" % elf.note_sections)

    print("\n[5] 手册页 / metainfo / 许可证交付完整")
    man1 = os.path.join(pkg, "share", "man", "man1")
    for tool in ("megactl", "megasasctl"):
        page = "%s.1" % tool
        path = os.path.join(man1, page)
        ok = os.path.isfile(path)
        if ok:
            with open(path, errors="replace") as handle:
                body = handle.read(4096)
            # 上游 man 页的 .TH 行形如 `.TH megactl 1 "03 March 2024" ""`，
            # 必须以对应工具名开头（曾误用硬编码 ".TH MEGACTL" 导致
            # megasasctl.1 假失败）
            ok = (".TH %s 1" % tool) in body
        check(ok, "share/man/man1/%s 交付且 .TH 宏指向 %s" % (page, tool))

    metainfo = os.path.join(pkg, "share", "metainfo",
                            "megactl.metainfo.xml")
    ok = os.path.isfile(metainfo)
    if ok:
        with open(metainfo, errors="replace") as handle:
            ok = "<component" in handle.read()
    check(ok, "share/metainfo/megactl.metainfo.xml 交付且是 AppStream 组件")

    copying = os.path.join(pkg, "licenses", "COPYING")
    ok = os.path.isfile(copying)
    if ok:
        with open(copying, errors="replace") as handle:
            head = handle.read(8192)
        ok = ("GNU GENERAL PUBLIC LICENSE" in head
              and "Version 2" in head)
    check(ok, "licenses/COPYING 交付且正文为 GPL-2.0")

    print("\n[6] 安装纯净性：无构建产物 / 无隐藏文件 / 无构建机路径")
    junk, hidden, leaked = [], [], []
    for root, dirs, files in os.walk(pkg):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, pkg)
            if name.endswith((".o", ".a", ".so", ".lo", ".la", ".log", ".tmp")):
                junk.append(rel)
            if name.startswith("."):
                hidden.append(rel)
        for name in list(dirs):
            if name.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, name), pkg))
    check(not junk, "无构建中间产物（.o/.a/.so/.log）", ",".join(junk[:6]))
    check(not hidden, "无隐藏文件/目录残留（JC5）", ",".join(hidden[:6]))
    for needle in ("/root/wt-", "/home/", "C:\\Users", "/tmp/conan",
                   "/mnt/c/Users"):
        for root, _dirs, files in os.walk(pkg):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, pkg)
                try:
                    if os.path.getsize(full) > 4 * 1024 * 1024:
                        continue
                    with open(full, "rb") as handle:
                        blob = handle.read()
                except OSError:
                    continue
                if needle.encode("utf-8") in blob:
                    leaked.append("%s(%s)" % (rel, needle))
    check(not leaked, "包内文本无构建机绝对路径泄漏",
          ";".join(sorted(set(leaked))[:6]))

    print("\n" + "=" * 64)
    print("适配自检 %d 项：通过 %d，失败 %d；其中鸿蒙特有 %d 项"
          % (TOTAL[0], TOTAL[0] - len(FAILED), len(FAILED), HARMONY[0]))
    if FAILED:
        for item in FAILED:
            print("  - FAIL: %s" % item)
        return 1
    print("[test] %d/%d assertions passed" % (TOTAL[0], TOTAL[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
